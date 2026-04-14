"""
index_docs.py — Build ChromaDB index with OpenAI-compatible embeddings (LM Studio)

Usage:
    python src/index_docs.py              # Index all docs in data/docs/
    python src/index_docs.py --reset      # Reset collection and re-index

Requirements:
    - LM Studio running with embedding model loaded
    - .env file with OPENAI_BASE_URL, OPENAI_EMBEDDING_MODEL
"""

import os
import sys
import argparse
from pathlib import Path

# Load .env
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

# Ensure src is in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import chromadb
from openai import OpenAI


def get_embedding_client():
    """Khởi tạo OpenAI client cho embeddings."""
    api_key = os.getenv("OPENAI_API_KEY", "")
    base_url = os.getenv("OPENAI_BASE_URL")
    embedding_model = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")

    client_kwargs = {"api_key": api_key}
    if base_url:
        client_kwargs["base_url"] = base_url

    client = OpenAI(**client_kwargs)
    return client, embedding_model


def embed_texts(client, model, texts):
    """Embed nhiều texts dùng OpenAI-compatible API."""
    response = client.embeddings.create(model=model, input=texts)
    return [item.embedding for item in response.data]


def chunk_text(text, chunk_size=500, overlap=100):
    """Chia text thành chunks với overlap."""
    words = text.split()
    chunks = []
    start = 0

    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        start += chunk_size - overlap

    return chunks if chunks else [text]


def index_documents(
    docs_dir="./data/docs",
    db_path="./chroma_db",
    collection_name="day09_docs",
    reset=False,
):
    """Index tài liệu vào ChromaDB."""

    print("=" * 60)
    print("Building ChromaDB Index")
    print("=" * 60)

    # Setup embedding client
    client, embedding_model = get_embedding_client()
    print(f"Embedding model: {embedding_model}")
    print(f"Base URL: {os.getenv('OPENAI_BASE_URL', 'default')}")
    print()

    # Setup ChromaDB
    chroma_client = chromadb.PersistentClient(path=db_path)

    if reset:
        try:
            chroma_client.delete_collection(collection_name)
            print(f"Deleted existing collection: {collection_name}")
        except Exception:
            pass

    collection = chroma_client.get_or_create_collection(
        collection_name, metadata={"hnsw:space": "cosine"}
    )
    print(f"Collection: {collection_name}")
    print(f"DB path: {db_path}")
    print()

    # Read and index documents
    docs_path = Path(docs_dir)
    if not docs_path.exists():
        print(f"❌ Error: {docs_dir} does not exist")
        return

    files = list(docs_path.glob("*.txt"))
    print(f"Found {len(files)} .txt files")
    print("-" * 60)

    total_chunks = 0

    for file_path in files:
        print(f"\n📄 {file_path.name}")

        # Read file
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Chunk content
        chunks = chunk_text(content, chunk_size=500, overlap=100)
        print(f"   Chunks: {len(chunks)}")

        # Embed chunks
        embeddings = embed_texts(client, embedding_model, chunks)
        print(f"   Embeddings: {len(embeddings)} x {len(embeddings[0])}d")

        # Add to collection
        ids = [f"{file_path.name}_{i}" for i in range(len(chunks))]
        metadatas = [
            {"source": file_path.name, "chunk_index": i} for i in range(len(chunks))
        ]

        collection.add(
            ids=ids, documents=chunks, metadatas=metadatas, embeddings=embeddings
        )

        total_chunks += len(chunks)
        print(f"   ✅ Indexed: {len(chunks)} chunks")

    print()
    print("=" * 60)
    print(f"✅ Index complete: {len(files)} files, {total_chunks} chunks")
    print(f"Collection count: {collection.count()}")
    print("=" * 60)


def verify_index(collection_name="day09_docs", db_path="./chroma_db"):
    """Kiểm tra index đã tạo."""
    chroma_client = chromadb.PersistentClient(path=db_path)

    try:
        collection = chroma_client.get_collection(collection_name)
        print(f"\n📊 Collection stats:")
        print(f"   Total documents: {collection.count()}")

        # Sample query
        client, embedding_model = get_embedding_client()
        query_embedding = embed_texts(client, embedding_model, ["test query"])[0]

        results = collection.query(query_embeddings=[query_embedding], n_results=3)

        print(f"   Sample query returned {len(results['documents'][0])} results")
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build ChromaDB index")
    parser.add_argument(
        "--reset", action="store_true", help="Reset collection and re-index"
    )
    parser.add_argument(
        "--docs-dir", default="./data/docs", help="Directory containing .txt files"
    )
    parser.add_argument(
        "--db-path", default="./chroma_db", help="ChromaDB persistence path"
    )
    parser.add_argument("--collection", default="day09_docs", help="Collection name")
    parser.add_argument(
        "--verify", action="store_true", help="Verify index after building"
    )
    args = parser.parse_args()

    # Build index
    index_documents(
        docs_dir=args.docs_dir,
        db_path=args.db_path,
        collection_name=args.collection,
        reset=args.reset,
    )

    # Verify if requested
    if args.verify:
        verify_index(args.collection, args.db_path)
