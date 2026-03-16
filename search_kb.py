"""Search the BM knowledge base across hot (vector) and cold (keyword) tiers.

Hot: ChromaDB semantic search over chunked markdown (class notes, readings, syllabus chapters)
Cold: Keyword grep over full Keller + Kotler textbook text with page numbers
"""
import os
import sys
import json
import re
import chromadb
from chromadb.utils import embedding_functions

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VECTOR_DB_DIR = os.path.join(BASE_DIR, "vector_db")
COLD_DIR = os.path.join(BASE_DIR, "knowledge_base", "cold")


def search_hot(query, n_results=10):
    """Semantic search in ChromaDB vector store."""
    ef = embedding_functions.DefaultEmbeddingFunction()
    client = chromadb.PersistentClient(path=VECTOR_DB_DIR)

    try:
        collection = client.get_collection("bm_knowledge", embedding_function=ef)
    except Exception:
        return []

    # Multi-query: search the original query + a rephrased version for better recall
    results = collection.query(query_texts=[query], n_results=n_results)

    chunks = []
    for i in range(len(results["documents"][0])):
        chunks.append({
            "text": results["documents"][0][i],
            "source": results["metadatas"][0][i]["source"],
            "heading": results["metadatas"][0][i]["heading"],
            "distance": results["distances"][0][i],
            "tier": "hot"
        })
    return chunks


def search_cold(query, max_results=5):
    """Keyword search in cold storage text files.

    Scores pages by keyword density. Lowered threshold to 1 keyword match
    but boosts pages with phrase matches (consecutive keywords).
    """
    results = []
    # Extract keywords: all words > 3 chars, plus important 2-3 char terms
    keywords = [w.lower() for w in query.split() if len(w) > 3]
    # Also extract 2-3 word phrases for phrase matching
    words = query.lower().split()
    phrases = [f"{words[i]} {words[i+1]}" for i in range(len(words)-1) if len(words[i]) > 2 and len(words[i+1]) > 2]

    for filename in ["keller_full_text.txt", "kotler_full_text.txt"]:
        filepath = os.path.join(COLD_DIR, filename)
        if not os.path.exists(filepath):
            continue

        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        pages = content.split("[PAGE ")
        scored_pages = []

        for page_block in pages[1:]:
            page_num_match = re.match(r"(\d+)\]", page_block)
            if not page_num_match:
                continue
            page_num = int(page_num_match.group(1))
            page_text = page_block[page_num_match.end():]
            page_lower = page_text.lower()

            # Score: keywords + bonus for phrase matches
            kw_score = sum(1 for kw in keywords if kw in page_lower)
            phrase_score = sum(2 for ph in phrases if ph in page_lower)
            total_score = kw_score + phrase_score

            if total_score >= 2:  # at least 2 keyword matches or 1 phrase match
                scored_pages.append((total_score, page_num, page_text[:1500], filename))

        scored_pages.sort(reverse=True)
        for score, page_num, text, fname in scored_pages[:max_results]:
            source_book = "Keller" if "keller" in fname else "Kotler"
            results.append({
                "text": text,
                "source": f"{source_book} textbook, Page {page_num}",
                "heading": "",
                "score": score,
                "page": page_num,
                "tier": "cold"
            })

    return results


def search(query, hot_results=10, cold_results=5):
    """Combined search across both tiers."""
    hot = search_hot(query, hot_results)
    cold = search_cold(query, cold_results)
    return {"query": query, "hot": hot, "cold": cold}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python search_kb.py 'your query here'")
        sys.exit(1)

    query = " ".join(sys.argv[1:])
    results = search(query)
    sys.stdout.buffer.write(json.dumps(results, indent=2, ensure_ascii=False).encode("utf-8"))
    sys.stdout.buffer.write(b"\n")
