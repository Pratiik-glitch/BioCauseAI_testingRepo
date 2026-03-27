import streamlit as st
import pandas as pd
import streamlit.components.v1 as components
import os
import spacy
import networkx as nx
from pyvis.network import Network
from Bio import Entrez
from google import genai
from dotenv import load_dotenv

# --- 1. Page Configuration & Environment ---
st.set_page_config(page_title="BioCause AI", page_icon="🧬", layout="wide")
load_dotenv(override=True)

# Load Credentials
ncbi_email = os.getenv("NCBI_EMAIL")
ncbi_api_key = os.getenv("NCBI_API_KEY")
gemini_key = os.getenv("GEMINI_API_KEY")

Entrez.email = ncbi_email
Entrez.api_key = ncbi_api_key

# --- 2. Cached AI Models (Loads once to save time) ---
@st.cache_resource
def load_spacy_model():
    return spacy.load("en_ner_bc5cdr_md")

nlp = load_spacy_model()

# --- 3. Core Engine Functions ---
def fetch_papers(query, max_results=20):
    """Fetches real papers from PubMed based on user input."""
    try:
        search_handle = Entrez.esearch(db="pubmed", term=query, retmax=max_results)
        search_results = Entrez.read(search_handle)
        search_handle.close()
        
        pmids = search_results["IdList"]
        if not pmids:
            return pd.DataFrame()

        fetch_handle = Entrez.efetch(db="pubmed", id=pmids, retmode="xml")
        papers = Entrez.read(fetch_handle)
        fetch_handle.close()

        extracted_data = []
        for paper in papers['PubmedArticle']:
            medline_citation = paper['MedlineCitation']
            article = medline_citation['Article']
            title = article.get('ArticleTitle', 'No Title')
            
            abstract = ""
            if 'Abstract' in article and 'AbstractText' in article['Abstract']:
                abstract = " ".join([str(text) for text in article['Abstract']['AbstractText']])
            
            pub_year = article.get('Journal', {}).get('JournalIssue', {}).get('PubDate', {}).get('Year', 'Unknown')

            extracted_data.append({"PMID": str(medline_citation['PMID']), "Title": title, "Abstract": abstract, "Year": pub_year})

        return pd.DataFrame(extracted_data)
    except Exception as e:
        st.error(f"PubMed Error: {e}")
        return pd.DataFrame()

def build_knowledge_graph(df):
    """Reads abstracts, extracts entities, and builds the 3D map."""
    G = nx.Graph()
    
    for _, row in df.iterrows():
        doc = nlp(str(row['Abstract']))
        diseases = {ent.text.lower() for ent in doc.ents if ent.label_ == "DISEASE"}
        chemicals = {ent.text.lower() for ent in doc.ents if ent.label_ == "CHEMICAL"}

        for d in diseases:
            G.add_node(d, group="disease", color="#ff4d4d", title="Disease")
        for c in chemicals:
            G.add_node(c, group="chemical", color="#4da6ff", title="Chemical/Drug")

        for d in diseases:
            for c in chemicals:
                if G.has_edge(d, c):
                    G[d][c]['weight'] += 1
                else:
                    G.add_edge(d, c, weight=1, title="Co-occurs with")

    net = Network(height="600px", width="100%", bgcolor="#222222", font_color="white")
    net.from_nx(G)
    net.repulsion(node_distance=150, central_gravity=0.2, spring_length=200)
    net.save_graph("live_graph.html")
    return G

def explain_network(edges_summary, papers_with_abstracts):
    """Uses Gemini to explain the network and extract strict evidence-based causal hypotheses."""
    client = genai.Client(api_key=gemini_key)
    prompt = f"""
You are a science writer who explains medical research to everyday people with no science background.
Write everything in plain, simple English — as if explaining to a curious 16-year-old.
Never use jargon without immediately explaining it in plain words right after.

===== PART 1: NETWORK EXPLANATION =====
Connections found across the literature:
{edges_summary}

Reference papers (Title, Year, PMID, Abstract):
{papers_with_abstracts}

Format Part 1 as:
1. SHORT SUMMARY: One simple paragraph. What is all this research about? What big health problems are scientists trying to solve? No technical terms.
2. CONNECTION MAP: Bullet points showing how the main ideas link together. After each bullet, add a plain-English explanation in parentheses of what this connection means in real life. Include PMID references.
3. PAPERS USED: List the reference papers with PMIDs.


===== PART 2: DISCOVERIES AND HYPOTHESES =====
Now carefully read each paper abstract above and extract ONLY relationships that are EXPLICITLY stated or directly supported by the text.

DO NOT invent, assume, or guess any relationships. If a paper does not clearly state a link, skip it.

For each relationship you find, pick the correct pattern and write it out simply:

PATTERN A — Something causes a problem:
🔬 [Chemical / Gene / Drug name] → causes or changes → [what happens inside the body] → which leads to → [Disease or condition]
Evidence: "direct quote from the paper"
Reference: [Paper Title] (PMID: XXXXX)
💬 In plain words: [Write 1-2 sentences for someone with zero science knowledge. What causes what? Why does this matter for a patient? Use everyday language, no technical words.]

PATTERN B — Something might be a treatment or cure:
💊 [Drug / Chemical / Natural compound] → may help treat or slow down → [Disease or condition]
Evidence: "direct quote from the paper"
Reference: [Paper Title] (PMID: XXXXX)
💬 In plain words: [Write 1-2 sentences for someone with zero science knowledge. What does this substance do? What disease might it help with? Why is this exciting? Use everyday language, no technical words.]

PATTERN C — A computer or AI tool improves detecting a disease:
🤖 [AI method / software / technology] → is better at spotting or diagnosing → [Condition or problem]
Evidence: "direct quote from the paper"
Reference: [Paper Title] (PMID: XXXXX)
💬 In plain words: [Write 1-2 sentences for someone with zero science knowledge. What does this computer tool do? How does it help doctors catch a disease sooner? Use everyday language, no technical words.]

If absolutely no relationships are found in any abstract, write:
⚠️ No clear findings were found in the provided abstracts. Researchers should examine the individual papers directly.

Do NOT invent relationships. Only report what the papers explicitly say.
"""
    try:
        response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
        return response.text
    except Exception as e:
        return f"❌ API Error: {e}"

def generate_hypothesis(title, abstract):
    """Uses Gemini 2.5 Flash to reason over the selected paper."""
    client = genai.Client(api_key=gemini_key)
    prompt = f"""
    You are BioCause AI. Analyze this literature, extract causal mechanisms, and generate a novel scientific hypothesis.
    Title: {title}
    Abstract: {abstract}

    Format strictly as:
    **1. Extracted Causal Chain:**
    **2. Biological Mechanism:**
    **3. Novel Hypothesis Generation:**
    """
    try:
        response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
        return response.text
    except Exception as e:
        return f"❌ API Error: {e}"

# --- 4. User Interface ---
st.title("🧬 BioCause AI: Causal Discovery Engine")
st.markdown("Search a disease or biological concept to automatically extract relationships and generate novel hypotheses.")

# Search Bar
col1, col2 = st.columns([3, 1])
with col1:
    user_query = st.text_input("Enter a Disease or Topic (e.g., Pancreatic Cancer):", placeholder="Type here...")
with col2:
    num_papers = st.number_input("Papers to analyze:", min_value=5, max_value=100, value=20, step=5)

# Session state keeps the data saved when the user switches tabs
if 'paper_data' not in st.session_state:
    st.session_state.paper_data = pd.DataFrame()

if st.button("🚀 Run AI Analysis", type="primary", use_container_width=True):
    if user_query:
        with st.status("Running BioCause AI Pipeline...", expanded=True) as status:
            st.write("📚 Fetching papers from PubMed...")
            df = fetch_papers(user_query, max_results=num_papers)
            
            if not df.empty:
                st.session_state.paper_data = df
                st.write("🧠 Extracting entities via SciSpacy...")
                G = build_knowledge_graph(df)
                st.session_state.network_graph = G
                status.update(label="Analysis Complete!", state="complete", expanded=False)
            else:
                status.update(label="No papers found.", state="error")
                st.stop()
    else:
        st.warning("Please enter a topic to search.")

st.divider()

# Only show the dashboard if we have data in memory
if not st.session_state.paper_data.empty:
    df = st.session_state.paper_data
    
    tab1, tab2, tab3 = st.tabs(["🕸️ Knowledge Graph", "🧠 AI Reasoning Engine", "📊 Raw Literature Data"])

    with tab1:
        st.subheader(f"Extracted Relationships for: '{user_query}'")
        try:
            HtmlFile = open("live_graph.html", 'r', encoding='utf-8')
            components.html(HtmlFile.read(), height=650, scrolling=True)
            
            if 'network_graph' in st.session_state:
                with st.expander("🤖 Explain this Network in Simple Terms (Text Flowchart)"):
                    if st.button("Generate Easy Explanation"):
                        with st.spinner("Translating network and extracting causal hypotheses from papers..."):
                            G = st.session_state.network_graph
                            df_papers = st.session_state.paper_data
                            
                            edges = sorted(G.edges(data=True), key=lambda x: x[2].get('weight', 0), reverse=True)[:30]
                            edges_str = "\n".join([f"- {u} is linked to {v} ({d.get('weight',1)} times)" for u, v, d in edges])
                            
                            # Pass full abstracts so the LLM can extract real causal chains
                            papers_with_abstracts = "\n\n".join([
                                f"Title: {row['Title']}\nYear: {row['Year']}\nPMID: {row['PMID']}\nAbstract: {row['Abstract'][:800]}"
                                for _, row in df_papers.head(15).iterrows()
                                if row['Abstract'].strip()
                            ])
                            
                            explanation = explain_network(edges_str, papers_with_abstracts)
                            st.markdown(explanation)
        except FileNotFoundError:
            st.warning("Graph not generated yet.")

    with tab2:
        st.subheader("Automated Hypothesis Generation")
        selected_title = st.selectbox("Select an extracted paper to analyze:", df['Title'].tolist())
        selected_paper = df[df['Title'] == selected_title].iloc[0]
        
        st.info(f"**Abstract:** {selected_paper['Abstract'][:400]}...")
        
        if st.button("Generate Causal Insights ✨"):
            with st.spinner("Gemini 2.5 is reasoning over the evidence..."):
                result = generate_hypothesis(selected_paper['Title'], selected_paper['Abstract'])
                st.success("Reasoning Complete!")
                st.markdown(result)

    with tab3:
        st.subheader(f"Dataset ({len(df)} papers fetched)")
        st.dataframe(df[['PMID', 'Title', 'Year']], use_container_width=True)