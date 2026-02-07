# scripts/setup/langsmith_validate.py
import os
from dotenv import load_dotenv
from langsmith import Client

# Load environment variables from .env file
load_dotenv()

# Verify environment variables are set
print("Environment Check:")
print(f"LANGSMITH_API_KEY: {'✅ Set' if os.getenv('LANGSMITH_API_KEY') else '❌ Not Set'}")
print(f"LANGSMITH_PROJECT: {os.getenv('LANGSMITH_PROJECT', '❌ Not Set')}")
print(f"LANGSMITH_TRACING: {os.getenv('LANGSMITH_TRACING', '❌ Not Set')}")
print()

# Test connection
client = Client()

try:
    projects = client.list_projects()
    print("✅ LangSmith API key is valid!")
    print(f"Connected to LangSmith successfully")
    print(f"Available projects: {[p.name for p in projects]}")
except Exception as e:
    print(f"❌ Error connecting to LangSmith: {e}")