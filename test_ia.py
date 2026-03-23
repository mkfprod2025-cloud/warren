import os
import json
from dotenv import load_dotenv
from google import genai

load_dotenv()
GENAI_API_KEY = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=GENAI_API_KEY)

MODELS_PRIORITY = ["gemini-3.1-pro-preview", "gemini-2.5-pro", "gemini-2.5-flash", "gemini-1.5-pro", "gemini-1.5-flash"]

def test_ia():
    print("Listing models...")
    try:
        models = client.models.list()
        for m in models:
            print(f"- {m.name}")
    except Exception as e:
        print(f"Error listing models: {e}")

    prompt = "Dis-moi 'OK' en JSON: {\"reponse\": \"OK\"}"
    for model_id in MODELS_PRIORITY:
        print(f"Testing {model_id}...")
        try:
            response = client.models.generate_content(model=model_id, contents=prompt, config={"response_mime_type": "application/json"})
            print(f"Success with {model_id}: {response.text}")
            break
        except Exception as e:
            print(f"Failed {model_id}: {e}")

if __name__ == "__main__":
    test_ia()
