"""Scrape ChatGPT free tier response for a given question.
Outputs JSON to stdout with the response text and brand examples found.
"""
import sys
import json
import re
import time
from playwright.sync_api import sync_playwright


def extract_brand_names(text):
    """Extract likely brand names from ChatGPT response (capitalized words/phrases)."""
    # Find capitalized multi-word phrases that look like brand names
    brands = set()
    # Match capitalized words that aren't common English words
    common_words = {"The", "This", "That", "These", "Their", "There", "They",
                    "What", "When", "Where", "Which", "While", "With",
                    "From", "Have", "Has", "Had", "For", "Are", "Was",
                    "Were", "Been", "Being", "Into", "Over", "Such",
                    "Through", "Under", "About", "After", "Before",
                    "Between", "Each", "Every", "Both", "India", "Indian",
                    "Brand", "Market", "Example", "Company", "Product"}

    # Find capitalized phrases (2+ words) or single capitalized words followed by TM-like context
    for match in re.finditer(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b', text):
        word = match.group(1)
        if word not in common_words and len(word) > 2:
            brands.add(word)

    # Also find ALL-CAPS words (likely brand names)
    for match in re.finditer(r'\b([A-Z]{2,})\b', text):
        word = match.group(1)
        if word not in {"CEO", "CMO", "CFO", "GDP", "AND", "THE", "FOR", "NOT"}:
            brands.add(word)

    return sorted(brands)


def scrape_chatgpt(question, timeout_seconds=90):
    """Send question to ChatGPT and capture response."""
    result = {"response": "", "brands": [], "error": None}

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            page.goto("https://chatgpt.com", wait_until="networkidle", timeout=30000)
            time.sleep(3)

            # Find the prompt textarea and type the question
            textarea = page.locator("textarea, #prompt-textarea, [contenteditable='true']").first
            textarea.click()
            textarea.fill(question)
            time.sleep(1)

            # Submit (press Enter or click send button)
            page.keyboard.press("Enter")

            # Wait for response to appear and finish streaming
            time.sleep(5)  # Initial wait for response to start

            # Poll until response stops growing
            prev_text = ""
            stable_count = 0
            for _ in range(timeout_seconds // 3):
                time.sleep(3)
                # Get all assistant message elements
                messages = page.locator("[data-message-author-role='assistant']").all()
                if messages:
                    current_text = messages[-1].inner_text()
                    if current_text == prev_text and len(current_text) > 50:
                        stable_count += 1
                        if stable_count >= 2:
                            break
                    else:
                        stable_count = 0
                    prev_text = current_text

            result["response"] = prev_text
            result["brands"] = extract_brand_names(prev_text)
            browser.close()

    except Exception as e:
        result["error"] = str(e)

    return result


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"response": "", "brands": [], "error": "No question provided"}))
        sys.exit(1)

    question = " ".join(sys.argv[1:])
    result = scrape_chatgpt(question)
    print(json.dumps(result, ensure_ascii=False))
