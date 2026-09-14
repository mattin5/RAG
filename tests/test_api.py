import os
import time
from dotenv import load_dotenv
from google import genai

# Carga las variables del archivo .env
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

client = genai.Client(api_key=GEMINI_API_KEY)

MAX_TRIES = 5

for attempt in range(MAX_TRIES):
    try:
        for m in client.models.list():
            if "generateContent" in m.supported_actions:
                print(m.name)    
        break
    except Exception as e:
        if '503' in str(e):
            print('The selected model is actually unavailable.')
            time.sleep(2**attempt)

        else:
            raise


print(response.text)