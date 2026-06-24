import os
from dotenv import load_dotenv

# Load backend env
load_dotenv("backend/.env")

gemini_key = os.getenv("GEMINI_API_KEY")

try:
    from google import genai
    client = genai.Client(api_key=gemini_key)
    print("Available models:")
    for model in client.models.list():
        print(f"Name: {model.name}")
except Exception as e:
    import traceback
    traceback.print_exc()
