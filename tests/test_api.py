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
        response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents="Quiero usar la API de genai para hacerle unos prompts con una extructura base, y le quiero añadir un output de una funcion que he usado yo. Cómo mandarías ese prompt"    
        )
        break
    except Exception as e:
        if '503' in str(e):
            print('The selected model is actually unavailable.')
            time.sleep(2**attempt)

        else:
            raise


print(response.text)