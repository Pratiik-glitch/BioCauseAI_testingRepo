from Bio import Entrez
import pandas as pd
import os
from dotenv import load_dotenv

# Force Python to read the .env file and override any old cached variables
load_dotenv(override=True)

# --- Configuration ---
# Fetch credentials securely from the environment
Entrez.email = os.getenv("NCBI_EMAIL")
Entrez.api_key = os.getenv("NCBI_API_KEY")

# --- Quick Debug Check ---
print("-" * 30)
print(f"🛠️  DEBUG - Email loaded: {Entrez.email}")
print(f"🛠️  DEBUG - API Key loaded: {Entrez.api_key}")
print("-" * 30)

# Safety check
if not Entrez.email or not Entrez.api_key or Entrez.email == "your_student_email@srmist.edu.in":
    raise ValueError("❌ Still loading old credentials! Make sure both files are saved.")

def fetch_pubmed_abstracts(search_query, max_results=5):
    print(f"🔍 Searching PubMed for: '{search_query}'...")
    
    try:
        search_handle = Entrez.esearch(db="pubmed", term=search_query, retmax=max_results)
        search_results = Entrez.read(search_handle)
        search_handle.close()
        
        pmids = search_results["IdList"]
        print(f"✅ Found {len(pmids)} papers. Fetching details...")

        if not pmids:
            return pd.DataFrame()

        fetch_handle = Entrez.efetch(db="pubmed", id=pmids, retmode="xml")
        papers = Entrez.read(fetch_handle)
        fetch_handle.close()

        extracted_data = []
        for paper in papers['PubmedArticle']:
            medline_citation = paper['MedlineCitation']
            article = medline_citation['Article']
            
            pmid = str(medline_citation['PMID'])
            title = article.get('ArticleTitle', 'No Title Available')
            
            abstract = ""
            if 'Abstract' in article and 'AbstractText' in article['Abstract']:
                abstract = " ".join([str(text) for text in article['Abstract']['AbstractText']])
            
            pub_year = "Unknown"
            if 'Journal' in article and 'JournalIssue' in article['Journal']:
                pub_date = article['Journal']['JournalIssue'].get('PubDate', {})
                pub_year = pub_date.get('Year', 'Unknown')

            extracted_data.append({
                "PMID": pmid,
                "Title": title,
                "Abstract": abstract,
                "Year": pub_year
            })

        return pd.DataFrame(extracted_data)

    except Exception as e:
        print(f"❌ An error occurred: {e}")
        return None

if __name__ == "__main__":
    query = "Alzheimer disease AND Amyloid beta"
    papers_df = fetch_pubmed_abstracts(query, max_results=5)
    
    if papers_df is not None and not papers_df.empty:
        print("\n🎉 Success! Here is a preview of your data:")
        pd.set_option('display.max_colwidth', 50) 
        print(papers_df.head())
        papers_df.to_csv("pubmed_sample_data.csv", index=False)
        print("\n💾 Data saved to 'pubmed_sample_data.csv'")