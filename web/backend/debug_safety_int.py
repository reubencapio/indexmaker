import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import os

api_key = os.environ.get("GEMINI_API_KEY")
genai.configure(api_key=api_key)

model = genai.GenerativeModel("gemini-3-pro-preview")

# civic_integrity = 8 (usually)
# Let's try to use the integer key
safety_settings = {
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
    8: HarmBlockThreshold.BLOCK_NONE,
}

prompt = "Global clean energy index with 50 constituents"

print("Sending prompt with integer safety key 8...")
try:
    response = model.generate_content(prompt, safety_settings=safety_settings)
    print("Success!")
    print(response.text[:100])
except Exception as e:
    print(f"Failed with: {e}")
