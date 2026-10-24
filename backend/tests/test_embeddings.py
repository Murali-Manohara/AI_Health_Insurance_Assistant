import pytest
from backend.app.services.embedding_service import LocalEmbeddingService

def test_embedding_dimensions_and_finite_values():
    embedder = LocalEmbeddingService()
    sample_texts = [
        "Health Shield Gold plan covers in-patient hospitalisation up to sum insured.",
        "Major surgery benefit payout percentage is 100% of sum insured.",
        "Waiting period of 30 days applies from policy inception."
    ]

    embeddings = embedder.generate_embeddings(sample_texts)
    assert len(embeddings) == 3

    for vec in embeddings:
        assert len(vec) == 384
        assert all(isinstance(x, float) for x in vec)
        # Check non-zero
        assert any(x != 0.0 for x in vec)

def test_embedding_empty_input():
    embedder = LocalEmbeddingService()
    res = embedder.generate_embeddings([])
    assert res == []
