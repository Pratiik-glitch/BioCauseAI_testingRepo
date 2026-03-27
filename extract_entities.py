import pandas as pd
import spacy

def main():
    print("🧠 Loading the SciSpacy Biomedical Model (this might take a few seconds)...")
    try:
        # Load the model specifically trained for Diseases and Chemicals
        nlp = spacy.load("en_ner_bc5cdr_md")
    except OSError:
        print("❌ Model not found! Please make sure you ran the pip install command for the model url.")
        return

    print("📂 Loading the downloaded PubMed data...")
    try:
        df = pd.read_csv("pubmed_sample_data.csv")
    except FileNotFoundError:
        print("❌ CSV file not found! Make sure pubmed_sample_data.csv is in this folder.")
        return

    # Let's just process the very first abstract to test our AI
    sample_abstract = df['Abstract'].iloc[0]
    sample_title = df['Title'].iloc[0]

    print(f"\n📄 Analyzing Paper: {sample_title}")
    print("-" * 50)
    
    # 🪄 This is where the magic happens. We pass the text into the AI model.
    doc = nlp(sample_abstract)

    print("\n🧬 --- Extracted Entities ---")
    
    # We use a set to avoid printing the exact same word multiple times
    extracted_data = set()
    for ent in doc.ents:
        extracted_data.add((ent.label_, ent.text))
        
    # Sort and print the results clearly
    for label, text in sorted(extracted_data):
        if label == "DISEASE":
            print(f"🔴 [{label}] : {text}")
        elif label == "CHEMICAL":
            print(f"💊 [{label}] : {text}")

if __name__ == "__main__":
    main()