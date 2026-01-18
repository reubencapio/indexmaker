import google.generativeai as genai
from google.generativeai.types import HarmCategory

print("Testing HarmCategory attributes:")
try:
    print(f"HARM_CATEGORY_CIVIC_INTEGRITY: {HarmCategory.HARM_CATEGORY_CIVIC_INTEGRITY}")
except AttributeError:
    print("AttributeError: HARM_CATEGORY_CIVIC_INTEGRITY not found in HarmCategory")

print("\nAll HarmCategory members:")
for member in HarmCategory:
    print(member)
