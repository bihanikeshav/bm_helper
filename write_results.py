import json, os, time, sys

def load_existing():
    if os.path.exists("results.json"):
        with open("results.json", "r", encoding="utf-8") as f:
            return json.load(f)
    return {"status": "generating", "timestamp": "", "questions": {}}

def save(data):
    data["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")
    tmp = "results.json.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, "results.json")

if __name__ == "__main__":
    qnum = sys.argv[1]  # e.g. "Q4"
    json_file = sys.argv[2]  # path to JSON with answers

    with open(json_file, "r", encoding="utf-8") as f:
        q_data = json.load(f)

    results = load_existing()
    if "questions" not in results:
        # Migrate old single-question format
        results = {"status": "generating", "timestamp": "", "questions": {}}
    results["questions"][qnum] = q_data

    # Check if all questions done
    all_done = all(
        results["questions"].get(q, {}).get("status") == "complete"
        for q in ["Q3", "Q4", "Q5", "Q6"]
    )
    results["status"] = "complete" if all_done else "generating"

    save(results)
    print(f"{qnum} written to results.json")
