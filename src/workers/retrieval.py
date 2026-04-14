"""
workers/retrieval.py — Retrieval Worker
Sprint 2: Implement retrieval từ ChromaDB, trả về chunks + sources.

Input (từ AgentState):
    - task: câu hỏi cần retrieve
    - (optional) retrieved_chunks nếu đã có từ trước

Output (vào AgentState):
    - retrieved_chunks: list of {"text", "source", "score", "metadata"}
    - retrieved_sources: list of source filenames
    - worker_io_log: log input/output của worker này

Gọi độc lập để test:
    python workers/retrieval.py
"""

import os
import sys
from pathlib import Path

# Load .env if available
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

from dotenv import load_dotenv
load_dotenv()

from openai import OpenAI
import chromadb

import random

# ─────────────────────────────────────────────
# Worker Contract (xem contracts/worker_contracts.yaml)
# Input:  {"task": str, "top_k": int = 3}
# Output: {"retrieved_chunks": list, "retrieved_sources": list, "error": dict | None}
# ─────────────────────────────────────────────

WORKER_NAME = "retrieval_worker"
DEFAULT_TOP_K = 3


def _get_embedding_fn():
    """
    Trả về embedding function sử dụng OpenAI.
    """
    try:
        # Lấy config từ environment
        api_key = os.getenv("OPENAI_API_KEY", "")
        base_url = os.getenv("OPENAI_BASE_URL")
        embedding_model = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")

        # Khởi tạo client với base URL nếu có (cho LM Studio/local LLM)
        client_kwargs = {"api_key": api_key}
        if base_url:
            client_kwargs["base_url"] = base_url

        client = OpenAI(**client_kwargs)

        def embed(text: str) -> list:
            # text-embedding-3 models support dimension truncating
            # We add dimensions=1024 to match rag_lab dimension (1024) if using text-embedding-3
            kwargs = {"input": text, "model": embedding_model}
            if "text-embedding-3" in embedding_model:
                kwargs["dimensions"] = 1024
                
            resp = client.embeddings.create(**kwargs)
            return resp.data[0].embedding

        return embed
    except ImportError:
        print("⚠️ Lỗi: Không thể import openai. Cần cài đặt gói `openai`.")
        pass

    def embed(text: str) -> list:
        return [random.random() for _ in range(1536)]

    print("⚠️ WARNING: Using random embeddings (test only). Install openai & dotenv.")
    return embed


def _get_collection():
    """
    Kết nối ChromaDB collection từ project root.
    """

    # Xác định project root (3 levels up từ workers/retrieval.py)
    project_root = Path(__file__).parent.parent.parent
    chroma_path = project_root / "chroma_db"

    client = chromadb.PersistentClient(path=str(chroma_path))
    try:
        # User defined data is in 'rag_lab', not 'day09_docs'
        collection = client.get_collection("rag_lab")
    except Exception:
        collection = client.get_or_create_collection(
            "rag_lab", metadata={"hnsw:space": "cosine"}
        )
        print("⚠️  Collection 'rag_lab' chưa có data.")
    return collection


def retrieve_dense(query: str, top_k: int = DEFAULT_TOP_K) -> list:
    """
    Dense retrieval: embed query → query ChromaDB → trả về top_k chunks.

    Returns:
        list of {"text": str, "source": str, "score": float, "metadata": dict}
    """
    embed = _get_embedding_fn()
    query_embedding = embed(query)

    try:
        collection = _get_collection()
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "distances", "metadatas"],
        )

        chunks = []
        for i, (doc, dist, meta) in enumerate(
            zip(
                results["documents"][0],
                results["distances"][0],
                results["metadatas"][0],
            )
        ):
            chunks.append(
                {
                    "text": doc,
                    "source": meta.get("source", "unknown"),
                    "score": round(1 - dist, 4),  # cosine similarity
                    "metadata": meta,
                }
            )
        return chunks

    except Exception as e:
        print(f"⚠️  ChromaDB query failed: {e}")
        # Fallback: return empty (abstain)
        return []


def run(state: dict) -> dict:
    """
    Worker entry point — gọi từ graph.py.

    Args:
        state: AgentState dict

    Returns:
        Updated AgentState với retrieved_chunks và retrieved_sources
    """
    task = state.get("task", "")
    top_k = state.get("retrieval_top_k", DEFAULT_TOP_K)

    state.setdefault("workers_called", [])
    state.setdefault("history", [])

    state["workers_called"].append(WORKER_NAME)

    # Log worker IO (theo contract)
    worker_io = {
        "worker": WORKER_NAME,
        "input": {"task": task, "top_k": top_k},
        "output": None,
        "error": None,
    }

    try:
        chunks = retrieve_dense(task, top_k=top_k)

        sources = list({c["source"] for c in chunks})

        state["retrieved_chunks"] = chunks
        state["retrieved_sources"] = sources

        worker_io["output"] = {
            "chunks_count": len(chunks),
            "sources": sources,
        }
        state["history"].append(
            f"[{WORKER_NAME}] retrieved {len(chunks)} chunks from {sources}"
        )

    except Exception as e:
        worker_io["error"] = {"code": "RETRIEVAL_FAILED", "reason": str(e)}
        state["retrieved_chunks"] = []
        state["retrieved_sources"] = []
        state["history"].append(f"[{WORKER_NAME}] ERROR: {e}")

    # Ghi worker IO vào state để trace
    state.setdefault("worker_io_logs", []).append(worker_io)

    return state


# ─────────────────────────────────────────────
# Test độc lập
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 50)
    print("Retrieval Worker — Standalone Test")
    print("=" * 50)

    test_queries = [
        "SLA ticket P1 là bao lâu?",
        "Điều kiện được hoàn tiền là gì?",
        "Ai phê duyệt cấp quyền Level 3?",
    ]

    for query in test_queries:
        print(f"\n▶ Query: {query}")
        result = run({"task": query})
        chunks = result.get("retrieved_chunks", [])
        print(f"  Retrieved: {len(chunks)} chunks")
        for c in chunks[:2]:
            print(f"    [{c['score']:.3f}] {c['source']}: {c['text'][:80]}...")
        print(f"  Sources: {result.get('retrieved_sources', [])}")

    print("\n✅ retrieval_worker test done.")
