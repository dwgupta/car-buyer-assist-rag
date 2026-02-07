from google import genai
from dotenv import load_dotenv
import os

load_dotenv()
client = genai.Client()

response = client.models.generate_content(
    #model="gemini-3-flash-preview",
    model="gemini-2.5-pro",
    contents="Explain how AI works in a few words",
)

print(response.text)