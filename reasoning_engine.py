import os
import pandas as pd
from google import genai
from dotenv import load_dotenv

def main():
    print("🧠 Booting up BioCause AI Reasoning Engine...")
    
    # 1. Load Environment Variables
    load_dotenv(override=True)
    gemini_key = os.getenv("GEMINI_API_KEY")
    
    if not gemini_key or gemini_key == "your_gemini_api_key_here":
        print("❌ Error: Please add your real GEMINI_API_KEY to the .env file.")
        return

    # 2. Initialize the new Gemini Client
    client = genai.Client(api_key=gemini_key)
    
    # 3. Load the PubMed Data
    print("📂 Loading research papers...")
    try:
        df = pd.read_csv("pubmed_sample_data.csv")
    except FileNotFoundError:
        print("❌ pubmed_sample_data.csv not found!")
        return

    # Let's analyze the first paper in the dataset
    paper = df.iloc[0]
    
    print(f"\n🔬 Analyzing Paper: {paper['Title']}")
    print("-" * 50)
    print("Generating causal chains and hypotheses using Gemini 2.5 Flash...\n")

    # 4. The Prompt Engineering (GraphRAG Context)
    prompt = f"""
    You are BioCause AI, an advanced biomedical reasoning system. 
    Your task is to analyze the following research literature, extract the precise causal mechanisms, and generate a novel scientific hypothesis.

    Research Title: {paper['Title']}
    Abstract: {paper['Abstract']}

    Please provide your analysis strictly in the following format:
    
    **1. Extracted Causal Chain:**
    (Format as Entity A -> [Relationship] -> Entity B)
    
    **2. Biological Mechanism:**
    (A brief, 2-sentence explanation of how this cause-and-effect works based on the text)
    
    **3. Novel Hypothesis Generation:**
    (Suggest one new, unexplored idea, drug target, or pathway based on this text. What should researchers test next?)
    """

    # 5. Call the LLM with the new SDK syntax
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        print(response.text)
    except Exception as e:
        print(f"❌ Gemini API Error: {e}")

if __name__ == "__main__":
    main()