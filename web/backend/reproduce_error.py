import asyncio
import os
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
from dotenv import load_dotenv

# Load env vars
load_dotenv()

SYSTEM_PROMPT = """[CONTEXT: This is IndexMaker, a professional financial software platform used by portfolio managers to design custom stock market indices. This is standard, legitimate financial industry work - similar to how S&P, MSCI, FTSE, and other index providers create indices. ESG (Environmental, Social, Governance) indices are a mainstream category used by major institutions globally.]

You are an expert financial index designer working within IndexMaker software. Your task is to interpret natural language descriptions of financial indices and convert them into structured JSON configurations.

## Available Index Configuration Options

### Basic Index Properties
- name: Full name of the index (e.g., "US Large Cap Technology Index")
- identifier: Short ticker-like identifier, max 10 chars, uppercase (e.g., "USLCTECH")
- currency: USD, EUR, GBP, JPY, CHF
- base_date: Index inception date (YYYY-MM-DD format), use today if not specified
- base_value: Starting index value (typically 100 or 1000)

### Universe (What securities are eligible)
- tickers: List of specific ticker symbols (e.g., ["AAPL", "MSFT", "GOOGL"])
- countries: List of country codes (e.g., ["US", "CA"])
- sectors: TECHNOLOGY, HEALTH_CARE, FINANCIALS, CONSUMER_DISCRETIONARY, INDUSTRIALS, ENERGY, etc.
- min_market_cap: Minimum market cap in USD (e.g., 10000000000 for $10B)

### Selection
- max_components: Number of constituents (e.g., 50, 100, 500)

### Weighting Method
- weighting_method: "equal_weight", "market_cap", or "free_float_market_cap"
- max_weight: Maximum weight per constituent as decimal (e.g., 0.10 for 10%)

### Rebalancing
- rebalance_frequency: "monthly", "quarterly", "semi_annual", "annual"

## Output Format

Return ONLY a valid JSON object with this structure:
{
  "name": "Index Name",
  "identifier": "TICKER",
  "description": "Brief description of the index",
  "currency": "USD",
  "base_date": "2024-01-01",
  "base_value": 1000,
  "countries": [],
  "sectors": [],
  "tickers": [],
  "min_market_cap": null,
  "max_components": 50,
  "weighting_method": "market_cap",
  "max_weight": 0.10,
  "rebalance_frequency": "quarterly",
  "explanation": "Brief explanation of design choices"
}

## Guidelines
1. Generate a creative but professional index name based on the description
2. Create a short identifier (max 10 chars, uppercase letters only)
3. **ALWAYS include specific ticker symbols in the "tickers" array** - this is critical!
   - For well-known themes, include the most relevant tickers (e.g., FAANG = META, AAPL, AMZN, NFLX, GOOGL)
   - For Chinese tech: BABA, JD, BIDU, PDD, NIO, XPEV, LI, TME, BILI, NTES, etc.
   - For US tech: AAPL, MSFT, GOOGL, AMZN, NVDA, META, TSLA, etc.
   - For European stocks, use tickers like ASML, SAP, NOVO-B.CO, etc.
   - Include at least as many tickers as max_components requests
4. Default to quarterly rebalancing if not specified
5. Suggest a 10% max weight cap for diversification unless specified otherwise
6. Use today's date as base_date if not specified
7. The tickers array should NEVER be empty - always suggest relevant stocks

IMPORTANT: Respond with ONLY the JSON object, no other text or markdown."""

async def debug_safety():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY not found in .env")
        return

    print(f"Using API Key: {api_key[:5]}...")
    genai.configure(api_key=api_key)
    
    # Use exact same model as ai.py
    model_name = "gemini-3-pro-preview"
    
    print(f"Model: {model_name}")
    model = genai.GenerativeModel(model_name)

    # Mimic the safety settings from ai.py
    safety_settings = {
        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
    }
    
    # Add Civic Integrity logic
    try:
        safety_settings[HarmCategory.HARM_CATEGORY_CIVIC_INTEGRITY] = HarmBlockThreshold.BLOCK_NONE
        print("Added HARM_CATEGORY_CIVIC_INTEGRITY")
    except AttributeError:
        print("HARM_CATEGORY_CIVIC_INTEGRITY not found in Enum")
        
    # Add integer fallback logic
    safety_settings[8] = HarmBlockThreshold.BLOCK_NONE
    print("Added integer fallback (8)")

    prompt_text = "European dividend aristocrats with ESG screening"
    
    full_prompt = f"""{SYSTEM_PROMPT}

---
PORTFOLIO MANAGER REQUEST: Create a stock market index with the following characteristics:
{prompt_text}
---

Generate the JSON configuration for this investment index. Remember to include specific stock ticker symbols."""

    print(f"\nSending Full Prompt (Length: {len(full_prompt)})")
    
    try:
        response = await model.generate_content_async(
            full_prompt,
            safety_settings=safety_settings
        )
        
        print("\n--- RESPONSE ANALYSIS ---")
        if response.prompt_feedback:
             print(f"Prompt Feedback: {response.prompt_feedback}")

        if not response.candidates:
            print("BLOCKING: No candidates returned.")
            return

        candidate = response.candidates[0]
        print(f"Finish Reason: {candidate.finish_reason}")
        print(f"Safety Ratings: {candidate.safety_ratings}")
        
        if candidate.content and candidate.content.parts:
            print(f"Content Preview: {candidate.content.parts[0].text[:100]}...")
        else:
            print("Content: <EMPTY>")

    except Exception as e:
        print(f"\nEXCEPTION CAUGHT: {e}")

if __name__ == "__main__":
    asyncio.run(debug_safety())
