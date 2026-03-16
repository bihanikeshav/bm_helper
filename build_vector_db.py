"""Build ChromaDB vector store from hot memory markdown files.

Chunking strategy: Section-aware splitting with overlap.
- Splits at markdown headings (##, ###) as primary boundaries
- Within long sections, splits at paragraph breaks (~500 tokens)
- Each chunk gets 2-sentence overlap from the previous chunk for context continuity
- Deduplication: combined_readings excluded (individual reading_materials are higher quality)
- Content-hash dedup catches remaining duplicates
"""
import os
import re
import hashlib
import chromadb
from chromadb.utils import embedding_functions

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HOT_DIR = os.path.join(BASE_DIR, "knowledge_base", "hot")
KB_DIR = os.path.join(BASE_DIR, "knowledge_base")
VECTOR_DB_DIR = os.path.join(BASE_DIR, "vector_db")

# Files to SKIP — combined readings overlap heavily with individual reading_materials
SKIP_PATTERNS = ["combined_readings_part"]


def chunk_markdown(text, source_file, max_tokens=500, overlap_sentences=2):
    """Split markdown into ~500-token chunks at section boundaries with overlap.

    Strategy:
    1. Split text into sections at heading boundaries (## or ###)
    2. If a section is <= max_tokens, keep it as one chunk
    3. If a section is > max_tokens, split at paragraph breaks (\n\n)
    4. Add last N sentences from previous chunk as overlap prefix
    """
    chunks = []

    # Split into sections at headings
    sections = re.split(r'(?=^#{1,4}\s)', text, flags=re.MULTILINE)

    prev_tail = ""  # Last few sentences of previous chunk for overlap

    for section in sections:
        section = section.strip()
        if not section:
            continue

        # Extract heading from this section
        heading = ""
        heading_match = re.match(r'^(#{1,4})\s+(.+)', section)
        if heading_match:
            heading = heading_match.group(2).strip()

        # Estimate tokens (1 token ~ 4 chars)
        section_tokens = len(section) // 4

        if section_tokens <= max_tokens:
            # Section fits in one chunk — prepend overlap from previous
            chunk_text = (prev_tail + "\n\n" + section).strip() if prev_tail else section
            chunks.append({
                "text": chunk_text,
                "source": source_file,
                "heading": heading,
            })
            # Update overlap tail
            sentences = re.split(r'[.!?]\s+', section)
            prev_tail = ". ".join(sentences[-overlap_sentences:]) if len(sentences) >= overlap_sentences else ""
        else:
            # Section too long — split at paragraph breaks
            paragraphs = section.split("\n\n")
            current_chunk_parts = []
            current_size = 0

            # First sub-chunk gets overlap from previous section
            if prev_tail:
                current_chunk_parts.append(prev_tail)
                current_size += len(prev_tail) // 4

            for para in paragraphs:
                para = para.strip()
                if not para:
                    continue
                para_tokens = len(para) // 4

                if current_size + para_tokens > max_tokens and current_chunk_parts:
                    # Flush current chunk
                    chunk_text = "\n\n".join(current_chunk_parts)
                    chunks.append({
                        "text": chunk_text,
                        "source": source_file,
                        "heading": heading,
                    })
                    # Overlap: last few sentences from this chunk
                    sentences = re.split(r'[.!?]\s+', chunk_text)
                    prev_tail = ". ".join(sentences[-overlap_sentences:]) if len(sentences) >= overlap_sentences else ""
                    # Start new chunk with overlap
                    current_chunk_parts = [prev_tail] if prev_tail else []
                    current_size = len(prev_tail) // 4 if prev_tail else 0

                current_chunk_parts.append(para)
                current_size += para_tokens

            # Flush remaining
            if current_chunk_parts:
                chunk_text = "\n\n".join(current_chunk_parts)
                chunks.append({
                    "text": chunk_text,
                    "source": source_file,
                    "heading": heading,
                })
                sentences = re.split(r'[.!?]\s+', chunk_text)
                prev_tail = ". ".join(sentences[-overlap_sentences:]) if len(sentences) >= overlap_sentences else ""

    return chunks


def collect_markdown_files():
    """Collect all .md files, skipping combined_readings (overlap with reading_materials)."""
    files = []

    # Hot memory directory (class notes, slides, textbook chapters)
    # SKIP combined_readings_part*.md — overlaps with individual reading_materials
    if os.path.exists(HOT_DIR):
        for root, dirs, filenames in os.walk(HOT_DIR):
            for f in filenames:
                if f.endswith(".md"):
                    if any(skip in f for skip in SKIP_PATTERNS):
                        continue
                    files.append(os.path.join(root, f))

    # Reading materials (individual articles — preferred over combined readings)
    rm_dir = os.path.join(KB_DIR, "reading_materials")
    if os.path.exists(rm_dir):
        for f in os.listdir(rm_dir):
            if f.endswith(".md"):
                files.append(os.path.join(rm_dir, f))

    return files


def build():
    """Main build function."""
    print("Building vector database...")
    print("Chunking: section-aware with 2-sentence overlap")
    print("Dedup: skipping combined_readings (overlaps with reading_materials) + content hash\n")

    ef = embedding_functions.DefaultEmbeddingFunction()
    client = chromadb.PersistentClient(path=VECTOR_DB_DIR)

    try:
        client.delete_collection("bm_knowledge")
    except Exception:
        pass

    collection = client.create_collection(
        name="bm_knowledge",
        embedding_function=ef,
        metadata={"description": "Brand Management course knowledge base"}
    )

    files = collect_markdown_files()
    print(f"Found {len(files)} markdown files (combined_readings excluded)")

    all_chunks = []
    seen_hashes = set()
    skipped_dupes = 0

    for filepath in files:
        with open(filepath, "r", encoding="utf-8") as f:
            text = f.read()

        rel_path = os.path.relpath(filepath, BASE_DIR)
        chunks = chunk_markdown(text, rel_path)

        for chunk in chunks:
            # Deduplicate by normalized content hash
            # Normalize: lowercase, strip whitespace, remove page markers
            normalized = re.sub(r'\[page \d+\]', '', chunk["text"].lower())
            normalized = re.sub(r'\s+', ' ', normalized).strip()
            content_hash = hashlib.md5(normalized[:300].encode()).hexdigest()

            if content_hash not in seen_hashes:
                seen_hashes.add(content_hash)
                all_chunks.append(chunk)
            else:
                skipped_dupes += 1

    print(f"Total chunks: {len(all_chunks)} (skipped {skipped_dupes} duplicates)")

    # Add to ChromaDB in batches of 100
    batch_size = 100
    for i in range(0, len(all_chunks), batch_size):
        batch = all_chunks[i:i + batch_size]
        collection.add(
            ids=[f"chunk_{i + j}" for j in range(len(batch))],
            documents=[c["text"] for c in batch],
            metadatas=[{"source": c["source"], "heading": c["heading"]} for c in batch],
        )
        print(f"  Indexed {min(i + batch_size, len(all_chunks))}/{len(all_chunks)} chunks")

    print(f"\nDone! Vector DB saved to {VECTOR_DB_DIR}")
    print(f"  {len(all_chunks)} chunks from {len(files)} files")
    print(f"  {skipped_dupes} duplicate chunks removed")


if __name__ == "__main__":
    build()
