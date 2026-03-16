"""Merge ChatGPT responses into saved_answers/q*.json files."""
import json, os, glob

CHATGPT_DIR = os.path.join(os.environ.get("TEMP", "/tmp"))
SAVED_DIR = "saved_answers"

for qnum in [3, 4, 5, 6]:
    chatgpt_file = os.path.join(CHATGPT_DIR, f"chatgpt_q{qnum}.json")
    saved_file = os.path.join(SAVED_DIR, f"q{qnum}.json")

    if not os.path.exists(chatgpt_file):
        print(f"Q{qnum}: No ChatGPT file found, skipping")
        continue
    if not os.path.exists(saved_file):
        print(f"Q{qnum}: No saved_answers file found, skipping")
        continue

    with open(chatgpt_file, "r", encoding="utf-8") as f:
        chatgpt = json.load(f)

    with open(saved_file, "r", encoding="utf-8") as f:
        saved = json.load(f)

    # Update chatgpt field
    saved["chatgpt"] = {
        "response": chatgpt.get("response", ""),
        "brands_mentioned": chatgpt.get("brands_mentioned", []),
        "banned_brands_in_response": chatgpt.get("banned_brands_in_response", []),
        "error": chatgpt.get("error"),
    }

    # Check overlap: which brands in our answers also appear in ChatGPT's response
    chatgpt_brands_lower = set(b.lower() for b in chatgpt.get("brands_mentioned", []))
    chatgpt_text_lower = chatgpt.get("response", "").lower()

    for ans in saved.get("answers", []):
        our_brands = []
        # Extract brand names from our answer's brand field
        brand_field = ans.get("brand", "")
        # Check each word in the brand field against chatgpt response
        overlaps = []
        for word in brand_field.replace("+", ",").replace("|", ",").split(","):
            word = word.strip()
            if len(word) > 2 and word.lower() in chatgpt_text_lower:
                overlaps.append(word)
        ans["chatgpt_overlap"] = overlaps if overlaps else []

    # Atomic write
    tmp = saved_file + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(saved, f, indent=2, ensure_ascii=False)
    os.replace(tmp, saved_file)
    print(f"Q{qnum}: ChatGPT merged — {len(chatgpt.get('brands_mentioned', []))} brands detected, "
          f"banned in response: {chatgpt.get('banned_brands_in_response', [])}")

# Also update results.json (currently Q3)
if os.path.exists("results.json"):
    with open("results.json", "r", encoding="utf-8") as f:
        results = json.load(f)
    qnum = results.get("question_number", 3)
    chatgpt_file = os.path.join(CHATGPT_DIR, f"chatgpt_q{qnum}.json")
    if os.path.exists(chatgpt_file):
        with open(chatgpt_file, "r", encoding="utf-8") as f:
            chatgpt = json.load(f)
        results["chatgpt"] = {
            "response": chatgpt.get("response", ""),
            "brands_mentioned": chatgpt.get("brands_mentioned", []),
            "banned_brands_in_response": chatgpt.get("banned_brands_in_response", []),
            "error": chatgpt.get("error"),
        }
        tmp = "results.json.tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        os.replace(tmp, "results.json")
        print(f"results.json updated with Q{qnum} ChatGPT response")
