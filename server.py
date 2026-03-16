"""Tiny HTTP server for BM Exam Helper dashboard."""
import os
from flask import Flask, send_from_directory, jsonify

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


if __name__ == "__main__":
    os.makedirs(os.path.join(BASE_DIR, "saved_answers"), exist_ok=True)
    print("BM Exam Helper server running at http://localhost:5000")
    app.run(host="127.0.0.1", port=5000, debug=False)
