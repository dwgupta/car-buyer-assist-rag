# scripts/setup/langsmith_project_test.py
import os
from dotenv import load_dotenv
from langchain_core.runnables import RunnableLambda

# Load environment variables from .env file
load_dotenv()

# Ensure environment variables are set
print("Environment Check:")
print(f"LANGSMITH_API_KEY: {'✅ Set' if os.getenv('LANGSMITH_API_KEY') else '❌ Not Set'}")
print(f"LANGSMITH_PROJECT: {os.getenv('LANGSMITH_PROJECT', '❌ Not Set')}")
print(f"LANGSMITH_TRACING: {os.getenv('LANGSMITH_TRACING', '❌ Not Set')}")
print()

# Simple function that will be traced
def simple_processor(input_data):
    """A simple function that processes input - no external APIs needed"""
    return f"Processed: {input_data}"

# Create a runnable (LangChain component)
processor = RunnableLambda(simple_processor)

# Run it - this will send traces to LangSmith
print("Sending test trace to LangSmith...")
try:
    result = processor.invoke("Test query for LangSmith validation")
    print(f"✅ Result: {result}")
    print(f"✅ Trace sent to LangSmith project: {os.getenv('LANGSMITH_PROJECT')}")
    print()
    print("👉 Now check your LangSmith dashboard at https://smith.langchain.com")
    print(f"👉 You should see the project '{os.getenv('LANGSMITH_PROJECT')}' with a new trace!")
except Exception as e:
    print(f"❌ Error: {e}")