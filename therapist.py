import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
print("KEY:", os.getenv("GEMINI_API_KEY"))

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

model = genai.GenerativeModel('models/gemini-2.5-flash')


def therapist_response(entry, history):

    context = "\n".join([h["text"] for h in history])

    prompt = f"""
You are a supportive therapist.

User journal entry:
{entry}

Recent journal entries:
{context}

Respond with empathy and offer one small helpful suggestion.
"""

    response = model.generate_content(prompt)

    return response.text