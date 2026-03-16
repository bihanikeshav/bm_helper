"""Get ChatGPT-equivalent response via Azure OpenAI GPT-5.3 with web search.
Mimics what a student would get from ChatGPT so we can detect overlap.
Outputs JSON to stdout: {response, brands_mentioned, error}
"""
import sys
import json
import re
import os
from openai import AzureOpenAI
from dotenv import load_dotenv

load_dotenv()

ENDPOINT = "https://imagegenerators.cognitiveservices.azure.com/"
DEPLOYMENT = "gpt-5.3-chat"
API_VERSION = "2025-03-01-preview"  # supports web search preview

BANNED_BRANDS = [
    "ACC", "Abercrombie and Fitch", "Accenture", "Adani", "Adidas",
    "Aditya Birla Fashion", "Air India", "Aiwa", "Amazon", "Amul", "Apple",
    "Ariel", "Asian Paints", "Audi", "Barbie", "Bata", "Benz", "Big Bazaar",
    "Coca-Cola", "Coke", "Colgate", "Decathlon", "Dettol", "Disney",
    "Dominos", "Duracell", "Fab India", "Fevicol", "Flipkart", "Fogg",
    "Ford", "Forest Essentials", "GE", "Gillette", "Google", "Gucci",
    "Harley-Davidson", "HUL", "Hindustan Unilever", "IBM", "IKEA", "ITC",
    "Intel", "Jaguar", "KFC", "Kit Kat", "L&T", "LG", "Lenskart",
    "Maggi", "Maruti", "McDonalds", "Microsoft", "Nestle", "Nike", "Nokia",
    "Old Monk", "Onida", "Oreo", "P&G", "Patanjali", "Pepsi", "PhonePe",
    "Prada", "Raymond", "Reebok", "Reliance", "Rolex", "Royal Enfield",
    "Samsung", "Santoor", "Snapdeal", "Sony", "Starbucks", "Tata",
    "Tanishq", "Titan", "Toyota", "Tesla", "TVS", "Unilever", "Vivo",
    "Volkswagen", "Voltas", "Walmart", "Whirlpool", "Wipro", "Zomato",
    "Paper Boat", "Paperboat", "Udaan"
]


def extract_brand_names(text):
    """Extract likely brand names from response."""
    brands = set()
    common_words = {
        "The", "This", "That", "These", "Their", "There", "They",
        "What", "When", "Where", "Which", "While", "With",
        "From", "Have", "Has", "Had", "For", "Are", "Was",
        "Were", "Been", "Being", "Into", "Over", "Such",
        "Through", "Under", "About", "After", "Before",
        "Between", "Each", "Every", "Both", "India", "Indian",
        "Brand", "Market", "Example", "Company", "Product",
        "However", "Therefore", "Moreover", "Furthermore",
        "According", "Additionally", "Conclusion", "Introduction",
    }

    # Capitalized phrases (2+ words)
    for match in re.finditer(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b', text):
        word = match.group(1)
        if word not in common_words and len(word) > 2:
            brands.add(word)

    # ALL-CAPS words (brand acronyms)
    for match in re.finditer(r'\b([A-Z]{2,})\b', text):
        word = match.group(1)
        if word not in {"CEO", "CMO", "CFO", "GDP", "AND", "THE", "FOR",
                        "NOT", "USA", "IPL", "RSS", "HTML", "URL", "PDF"}:
            brands.add(word)

    return sorted(brands)


def get_chatgpt_response(question, timeout=120):
    """Call Azure OpenAI GPT-5.3 with web search to mimic ChatGPT response."""
    result = {"response": "", "brands_mentioned": [], "error": None}

    api_key = os.getenv("key") or os.getenv("AZURE_OPENAI_API_KEY") or ""
    if not api_key:
        result["error"] = "No API key found in .env (expected 'key' or 'AZURE_OPENAI_API_KEY')"
        return result

    try:
        client = AzureOpenAI(
            azure_endpoint=ENDPOINT,
            api_key=api_key,
            api_version=API_VERSION,
        )

        system_prompt = (
            "You are ChatGPT, a helpful AI assistant. The user is a business school student "
            "asking a Brand Management exam question. Answer it thoroughly with real brand "
            "examples, preferably from the Indian market. Use web search to find current, "
            "real examples with citations. Be detailed and provide 2-3 examples per sub-part."
        )

        response = client.chat.completions.create(
            model=DEPLOYMENT,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": question},
            ],
            max_completion_tokens=4000,
        )

        text = response.choices[0].message.content or ""
        result["response"] = text
        result["brands_mentioned"] = extract_brand_names(text)

        # Flag which brands overlap with banned list
        response_lower = text.lower()
        banned_found = []
        for brand in BANNED_BRANDS:
            if brand.lower() in response_lower:
                banned_found.append(brand)
        result["banned_brands_in_response"] = banned_found

    except Exception as e:
        result["error"] = str(e)

    return result


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"response": "", "brands_mentioned": [], "error": "No question provided"}))
        sys.exit(1)

    question = " ".join(sys.argv[1:])
    result = get_chatgpt_response(question)
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
