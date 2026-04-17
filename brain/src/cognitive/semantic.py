"""Layer 8: Semantic Memory -- vector search using ChromaDB embeddings."""

from __future__ import annotations

from typing import Any

from brain.src.logger import get_logger

log = get_logger("semantic")


class SemanticMemory:
    """Meaning-based memory via vector embeddings. ChromaDB backend.

    ChromaDB and sentence-transformers are optional dependencies.
    If not installed, semantic search is disabled gracefully.
    """

    def __init__(self, persist_dir: str | None = None) -> None:
        self._client: Any = None
        self._collection: Any = None
        self._enabled = False

        try:
            import chromadb
            if persist_dir:
                self._client = chromadb.PersistentClient(path=persist_dir)
            else:
                self._client = chromadb.Client()
            self._collection = self._client.get_or_create_collection(
                name="brain_memories",
                metadata={"hnsw:space": "cosine"},
            )
            self._enabled = True
            log.info("semantic_initialized", persist=persist_dir or "in_memory")
        except ImportError:
            log.warning("semantic_disabled", reason="chromadb not installed")
        except Exception as e:
            log.warning("semantic_init_failed", error=str(e))

    @property
    def enabled(self) -> bool:
        return self._enabled

    def add(self, doc_id: str, text: str, metadata: dict | None = None) -> None:
        if not self._enabled:
            return
        try:
            self._collection.upsert(
                ids=[doc_id],
                documents=[text],
                metadatas=[metadata or {}],
            )
        except Exception as e:
            log.error("semantic_add_failed", id=doc_id, error=str(e))

    def search(self, query: str, limit: int = 5, min_score: float = 0.3) -> list[dict]:
        if not self._enabled:
            return []
        try:
            results = self._collection.query(
                query_texts=[query],
                n_results=limit,
            )
            entries = []
            ids = results.get("ids", [[]])[0]
            docs = results.get("documents", [[]])[0]
            distances = results.get("distances", [[]])[0]
            metadatas = results.get("metadatas", [[]])[0]

            for i, doc_id in enumerate(ids):
                score = 1.0 - distances[i]  # cosine distance to similarity
                if score < min_score:
                    continue
                entries.append({
                    "id": doc_id,
                    "text": docs[i],
                    "score": round(score, 3),
                    "metadata": metadatas[i] if i < len(metadatas) else {},
                })
            return entries
        except Exception as e:
            log.error("semantic_search_failed", error=str(e))
            return []

    def delete(self, doc_id: str) -> None:
        if not self._enabled:
            return
        try:
            self._collection.delete(ids=[doc_id])
        except Exception as e:
            log.error("semantic_delete_failed", id=doc_id, error=str(e))

    def count(self) -> int:
        if not self._enabled:
            return 0
        return self._collection.count()

    def check_duplicate(self, text: str, threshold: float = 0.92) -> str | None:
        """Returns existing doc ID if a near-duplicate exists, else None."""
        results = self.search(text, limit=1, min_score=threshold)
        if results:
            return results[0]["id"]
        return None
