import pandas as pd
import spacy
import networkx as nx
from pyvis.network import Network

def main():
    print("🧠 Loading SciSpacy Model...")
    try:
        nlp = spacy.load("en_ner_bc5cdr_md")
    except OSError:
        print("❌ Model not found! Please ensure it is installed.")
        return

    print("📂 Loading PubMed data...")
    try:
        df = pd.read_csv("pubmed_sample_data.csv")
    except FileNotFoundError:
        print("❌ pubmed_sample_data.csv not found!")
        return

    # Initialize a NetworkX Graph
    G = nx.Graph()

    print("🕸️ Building the Knowledge Graph (Extracting Co-occurrences)...")
    
    # Process all papers in your dataset
    for index, row in df.iterrows():
        abstract = str(row['Abstract'])
        doc = nlp(abstract)
        
        diseases = set()
        chemicals = set()

        # Categorize the entities
        for ent in doc.ents:
            if ent.label_ == "DISEASE":
                diseases.add(ent.text.lower())
            elif ent.label_ == "CHEMICAL":
                chemicals.add(ent.text.lower())

        # Add Nodes (Entities) to the graph
        for d in diseases:
            G.add_node(d, group="disease", color="#ff4d4d", title="Disease")
        for c in chemicals:
            G.add_node(c, group="chemical", color="#4da6ff", title="Chemical/Drug")

        # Add Edges (Relationships): If they are in the same abstract, connect them!
        for d in diseases:
            for c in chemicals:
                # If the edge already exists, increase its weight (stronger evidence)
                if G.has_edge(d, c):
                    G[d][c]['weight'] += 1
                else:
                    G.add_edge(d, c, weight=1, title="Co-occurs with")

    print(f"✅ Graph built with {G.number_of_nodes()} entities and {G.number_of_edges()} connections.")

    # Convert the NetworkX graph to a PyVis interactive network
    print("🎨 Generating Interactive HTML map...")
    net = Network(height="750px", width="100%", bgcolor="#222222", font_color="white")
    net.from_nx(G)
    
    # Add physics to make it look cool and organize itself naturally
    net.repulsion(node_distance=150, central_gravity=0.2, spring_length=200)
    
    # Save the file
    output_file = "biocause_knowledge_graph.html"
    net.save_graph(output_file)
    print(f"\n🎉 Success! Open '{output_file}' in your web browser to view your AI Knowledge Graph!")

if __name__ == "__main__":
    main()