"""
OhRight — Embeddings layer
Priority: OpenAI text-embedding-3-small (cloud, fast) → Ollama all-minilm (local, fallback)

Both produce affordable embeddings. OpenAI is ~$0.02 per 1000 embeddings.
"""

import requests
import numpy as np
import time
import os
from typing import Optional

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
EMBEDDING_MODEL = os.environ.get("OHRIGHT_EMBED_MODEL", "all-minilm:33m")
EMBEDDING_DIM = 384


def _get_openai_key() -> str:
    """Get OpenAI key from environment or key file."""
    key = os.environ.get("OPENAI_API_KEY", "")
    if not key:
        key_file = os.path.expanduser("~/.ohright/.openai_key")
        if os.path.exists(key_file):
            with open(key_file) as f:
                key = f.read().strip()
    return key


def embed_openai(texts: list[str]) -> list[list[float]]:
    """Generate embeddings using OpenAI text-embedding-3-small."""
    from openai import OpenAI
    key = _get_openai_key()
    if not key:
        raise RuntimeError("OPENAI_API_KEY not set")
    client = OpenAI(api_key=key)
    resp = client.embeddings.create(
        model="text-embedding-3-small",
        input=texts
    )
    return [d.embedding for d in resp.data]


def embed_local(texts: list[str]) -> list[list[float]]:
    """Generate embeddings using local Ollama model."""
    embeddings = []
    for text in texts:
        resp = requests.post(
            f"{OLLAMA_URL}/api/embeddings",
            json={"model": EMBEDDING_MODEL, "prompt": text},
            timeout=5
        )
        resp.raise_for_status()
        embeddings.append(resp.json()["embedding"])
    return embeddings


def embed(texts: list[str]) -> list[list[float]]:
    """
    Generate embeddings. Tries OpenAI first (fast, cheap), falls back to local Ollama.
    Handles both single string and list of strings.
    """
    if isinstance(texts, str):
        texts = [texts]

    # Try OpenAI first (fast, reliable)
    if _get_openai_key():
        try:
            return embed_openai(texts)
        except Exception as e:
            print(f"[ohright] OpenAI embeddings failed ({e}), trying local...")

    # Fallback to local Ollama
    try:
        return embed_local(texts)
    except Exception as e:
        raise RuntimeError(f"All embedding backends failed: {e}")


def embed_single(text: str) -> list[float]:
    """Convenience: embed a single text string."""
    return embed([text])[0]


def embedding_to_blob(vec: list[float]) -> bytes:
    """Convert embedding list to binary blob for SQLite storage."""
    return np.array(vec, dtype=np.float32).tobytes()


def blob_to_embedding(blob: bytes) -> list[float]:
    """Convert SQLite blob back to embedding list."""
    return np.frombuffer(blob, dtype=np.float32).tolist()


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two embeddings."""
    a_np = np.array(a)
    b_np = np.array(b)
    return float(np.dot(a_np, b_np) / (np.linalg.norm(a_np) * np.linalg.norm(b_np)))


def check_ollama_available() -> bool:
    """Check if Ollama is running and model is available."""
    try:
        resp = requests.get(f"{OLLAMA_URL}/api/tags", timeout=3)
        resp.raise_for_status()
        models = [m["name"] for m in resp.json().get("models", [])]
        return any(EMBEDDING_MODEL in m for m in models)
    except Exception:
        return False


if __name__ == "__main__":
    key = _get_openai_key()
    print(f"OpenAI key available: {bool(key)}")
    ollama = check_ollama_available()
    print(f"Ollama available: {ollama}")

    if key or ollama:
        t0 = time.time()
        vec = embed_single("product research: ultrawide monitors")
        elapsed = (time.time() - t0) * 1000
        print(f"Embedding: {len(vec)} dims, {elapsed:.1f}ms")
        print(f"First 5: {[round(v, 4) for v in vec[:5]]}")
    else:
        print("No embedding backend available")
