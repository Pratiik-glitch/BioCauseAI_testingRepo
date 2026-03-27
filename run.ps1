if (-Not (Test-Path ".env")) {
    Copy-Item ".env.example" -Destination ".env"
    Write-Host "Created .env from .env.example. Please update it with your API keys if you encounter errors fetching data."
}

if (-Not (Test-Path "venv")) {
    Write-Host "Creating virtual environment..."
    python -m venv venv
}

.\venv\Scripts\activate
Write-Host "Installing requirements..."
pip install -r requirements.txt
Write-Host "Installing scispacy model..."
pip install "https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.5.4/en_ner_bc5cdr_md-0.5.4.tar.gz"

Write-Host "Starting Streamlit app..."
streamlit run app.py
