"""Connect to Vertex AI and run a simple test."""
import os

from dotenv import load_dotenv
import vertexai
from vertexai.generative_models import GenerativeModel

load_dotenv()

# From your service account JSON
PROJECT_ID = "third-extension-474206-m2"
LOCATION = "us-central1"

# Credentials are auto-loaded from GOOGLE_APPLICATION_CREDENTIALS in .env
vertexai.init(project=PROJECT_ID, location=LOCATION)

# Simple test: generate a short response
# gemini-1.5-flash is retired; use gemini-2.0-flash or gemini-2.5-flash
model = GenerativeModel("gemini-2.0-flash-001")
response = model.generate_content("Say 'Hello from Vertex AI' in one short sentence.")

print(response.text)
print("\n✓ Connected to Vertex AI successfully!")
