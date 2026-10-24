import re
import time
from typing import Optional
from rank_bm25 import BM25Okapi
from backend.app.services.chroma_service import ChromaStorageService
from backend.app.core.logging_config import logger

def simple_tokenize(text: str) -> list[str]:
    """Tokenize text into lowercase alphanumeric tokens for BM25 matching."""
    return re.findall(r"\b[a-zA-Z0-9_\-\.\%]+\b", text.lower())

class BM25SearchService:
    """
    In-memory BM25 lexical search engine over persisted ChromaDB chunks.
    Filters candidate matches strictly by authorized plan IDs before ranking.
    """

    def __init__(self, chroma_service: Optional[ChromaStorageService] = None):
        self.chroma_service = chroma_service or ChromaStorageService()
        self.bm25: Optional[BM25Okapi] = None
        self.chunk_ids: list[str] = []
        self.documents: list[str] = []
        self.metadatas: list[dict] = []
        self.plan_ids: list[str] = []
        self.last_built_timestamp: Optional[str] = None
        self.build_index()

    def build_index(self) -> int:
        """Fetch all chunks from ChromaDB and build the BM25 index."""
        logger.info("Building BM25 index from ChromaDB storage...")
        try:
            results = self.chroma_service.collection.get(include=["documents", "metadatas"])
            self.chunk_ids = results.get("ids", [])
            self.documents = results.get("documents", [])
            self.metadatas = results.get("metadatas", [])
            self.plan_ids = [m.get("plan_id", "") for m in self.metadatas]
            
            tokenized_corpus = [simple_tokenize(doc) for doc in self.documents]
            if tokenized_corpus:
                self.bm25 = BM25Okapi(tokenized_corpus)
                self.last_built_timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                logger.info(f"BM25 index built successfully with {len(self.chunk_ids)} documents.")
            else:
                self.bm25 = None
                logger.warning("BM25 index is empty; 0 documents retrieved from ChromaDB.")
            return len(self.chunk_ids)
        except Exception as e:
            logger.error(f"Failed to build BM25 index: {e}")
            self.bm25 = None
            return 0

    def search(
        self,
        query: str,
        authorized_plan_ids: list[str],
        top_k: int = 10
    ) -> list[dict]:
        """
        Execute BM25 lexical search against authorized plan scope.
        Returns ranked list of candidate chunks with scores and ranks.
        """
        if not self.bm25 or not self.chunk_ids:
            # Attempt lazy rebuild if empty
            if self.build_index() == 0:
                return []

        tokens = simple_tokenize(query)
        if not tokens:
            return []

        # Compute raw scores for all documents
        raw_scores = self.bm25.get_scores(tokens)
        authorized_set = set(authorized_plan_ids)

        scored_candidates = []
        for idx, score in enumerate(raw_scores):
            if score <= 0.0:
                continue
            plan_id = self.plan_ids[idx]
            # Strict pre-filter: plan must be in authorized scope
            if plan_id not in authorized_set:
                continue

            scored_candidates.append({
                "chunk_id": self.chunk_ids[idx],
                "content": self.documents[idx],
                "metadata": self.metadatas[idx],
                "plan_id": plan_id,
                "score": float(score)
            })

        # Sort descending by score
        scored_candidates.sort(key=lambda x: x["score"], reverse=True)
        top_results = scored_candidates[:top_k]

        # Assign 1-indexed ranks
        for rank, item in enumerate(top_results, start=1):
            item["bm25_rank"] = rank

        return top_results

    def get_status(self) -> dict:
        return {
            "total_indexed_chunks": len(self.chunk_ids),
            "is_indexed": self.bm25 is not None,
            "last_built": self.last_built_timestamp
        }
