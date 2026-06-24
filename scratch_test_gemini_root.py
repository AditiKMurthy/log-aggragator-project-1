import os
from dotenv import load_dotenv

# Load root env
load_dotenv(".env")

gemini_key = os.getenv("GEMINI_API_KEY")
print("Loaded GEMINI_API_KEY:", gemini_key[:10] + "..." if gemini_key else "None")

try:
    from google import genai
    print("Successfully imported google-genai")
    
    client = genai.Client(api_key=gemini_key)
    print("Created genai.Client")
    
    print("Testing generate_content...")
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents="Hello, reply with 'Hello World'"
    )
    print("Response text:", response.text)
except Exception as e:
    print("Error occurred:")
    import traceback
    traceback.print_exc()
