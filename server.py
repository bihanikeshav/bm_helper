"""Tiny HTTP server for BM Exam Helper dashboard."""
import os
import requests
from flask import Flask, send_from_directory, jsonify, request

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, static_folder=BASE_DIR)


@app.route("/")
def index():
    return send_from_directory(BASE_DIR, "index.html")


@app.route("/results.json")
def results():
    results_path = os.path.join(BASE_DIR, "results.json")
    if os.path.exists(results_path):
        return send_from_directory(BASE_DIR, "results.json")
    return jsonify({"status": "waiting", "answers": [], "chatgpt": None, "recommender": None})


@app.route("/saved_answers/<path:filename>")
def saved_answer(filename):
    return send_from_directory(os.path.join(BASE_DIR, "saved_answers"), filename)


@app.route("/saved_answers/")
def list_saved():
    saved_dir = os.path.join(BASE_DIR, "saved_answers")
    if os.path.exists(saved_dir):
        files = sorted(os.listdir(saved_dir), reverse=True)
        return jsonify(files)
    return jsonify([])


@app.route("/check-url")
def check_url():
    """Proxy endpoint to verify citation URLs (avoids CORS issues)."""
    url = request.args.get("url", "")
    if not url:
        return jsonify({"ok": False, "status": 0, "error": "no url"})
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        # Try HEAD first (fast, no body download)
        r = requests.head(url, timeout=5, allow_redirects=True, headers=headers)
        if r.status_code < 400:
            return jsonify({"ok": True, "status": r.status_code})
        # HEAD blocked (403/405)? Try GET with stream (only reads headers, not body)
        r = requests.get(url, timeout=5, allow_redirects=True, headers=headers, stream=True)
        r.close()
        return jsonify({"ok": r.status_code < 400, "status": r.status_code})
    except requests.exceptions.Timeout:
        return jsonify({"ok": False, "status": 0, "error": "timeout"})
    except Exception as e:
        return jsonify({"ok": False, "status": 0, "error": str(e)[:100]})


if __name__ == "__main__":
    os.makedirs(os.path.join(BASE_DIR, "saved_answers"), exist_ok=True)
    print("BM Exam Helper server running at http://localhost:5000")
    app.run(host="127.0.0.1", port=5000, debug=False)
