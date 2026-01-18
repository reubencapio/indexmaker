import os

import google.generativeai as genai

api_key = os.environ.get("GEMINI_API_KEY")
genai.configure(api_key=api_key)

model = genai.GenerativeModel("gemini-3-pro-preview")

# Use list of dicts with string keys to avoid Enum dependency
safety_settings = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_CIVIC_INTEGRITY", "threshold": "BLOCK_NONE"},
]

prompt = "Global clean energy index with 50 constituents"

print("Sending prompt with string safety settings...")
try:
    response = model.generate_content(prompt, safety_settings=safety_settings)
    print("Success!")
    print(response.text[:100])
except Exception as e:
    print(f"Failed with: {e}")
