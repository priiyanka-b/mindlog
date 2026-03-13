import json
import os
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

def analyze_emotions(text):
    try:
        model = genai.GenerativeModel('models/gemini-2.5-flash')

        prompt = f"""Analyze the emotions in this journal entry and return ONLY a JSON object with these exact keys: joy, sadness, anxiety, fear.
Each value must be a float between 0 and 1 representing intensity.
Do not include any explanation, just the raw JSON.

Journal entry: "{text}"

Example output format:
{{"joy": 0.1, "sadness": 0.7, "anxiety": 0.4, "fear": 0.2}}"""

        response = model.generate_content(prompt)
        text_response = response.text.strip()
        text_response = text_response.replace('```json', '').replace('```', '').strip()

        emotions = json.loads(text_response)
        return {
            "joy":     float(emotions.get("joy", 0)),
            "sadness": float(emotions.get("sadness", 0)),
            "anxiety": float(emotions.get("anxiety", 0)),
            "fear":    float(emotions.get("fear", 0))
        }

    except Exception as e:
        print(f"Emotion analysis error: {e}")
        return {"joy": 0.0, "sadness": 0.0, "anxiety": 0.0, "fear": 0.0}