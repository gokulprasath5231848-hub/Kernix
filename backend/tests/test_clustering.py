"""Clustering tests.

These deliberately test *stability and bounds* rather than semantic
"correctness" — an embedding model's exact groupings are not a fixed contract,
but determinism and obvious separations are.
"""
import numpy as np
import pytest

from app.pipeline.clustering import cluster_activities
from app.pipeline.discovery import get_embedding_service

sklearn = pytest.importorskip("sklearn", reason="scikit-learn not installed")


def _fake_embeddings(groups: list[list[str]]) -> tuple[list[str], np.ndarray]:
    """Build deterministic embeddings where members of a group are near-identical
    and different groups are orthogonal. Lets us test clustering mechanics
    without downloading an 80MB model."""
    labels: list[str] = []
    vectors: list[np.ndarray] = []
    dim = max(len(groups), 2)
    for gi, group in enumerate(groups):
        base = np.zeros(dim)
        base[gi] = 1.0
        for offset, label in enumerate(group):
            v = base.copy()
            v[(gi + 1) % dim] += 0.01 * offset  # tiny jitter within the group
            v = v / np.linalg.norm(v)
            labels.append(label)
            vectors.append(v)
    return labels, np.vstack(vectors)


def test_known_similar_labels_group_together():
    labels, embeddings = _fake_embeddings([
        ["exp letter req", "experience certificate", "EXP LTR"],
    ])
    clusters = cluster_activities(labels, embeddings)
    assert len(clusters) == 1
    assert clusters[0]["count"] == 3


def test_dissimilar_labels_separate():
    labels, embeddings = _fake_embeddings([
        ["expense report", "expense reimbursement"],
        ["server reboot", "restart server"],
    ])
    clusters = cluster_activities(labels, embeddings)
    assert len(clusters) == 2
    assert {c["count"] for c in clusters} == {2}


def test_clustering_is_deterministic():
    labels, embeddings = _fake_embeddings([["a1", "a2"], ["b1", "b2"]])
    first = cluster_activities(labels, embeddings)
    second = cluster_activities(labels, embeddings)
    assert [c["count"] for c in first] == [c["count"] for c in second]


def test_empty_input_returns_empty():
    assert cluster_activities([], np.zeros((0, 3))) == []


def test_single_label_returns_single_cluster():
    result = cluster_activities(["only one"], np.ones((1, 3)))
    assert len(result) == 1
    assert result[0]["name"] == "only one"


def test_canonical_name_is_the_most_common_label():
    labels = ["exp ltr", "exp ltr", "experience certificate"]
    embeddings = np.array([[1.0, 0.0], [1.0, 0.0], [0.999, 0.001]])
    clusters = cluster_activities(labels, embeddings)
    assert clusters[0]["name"] == "exp ltr"


def test_embedding_service_degrades_without_model():
    """If sentence-transformers is unavailable the service must not crash the
    pipeline — it returns zero vectors and logs a warning."""
    service = get_embedding_service()
    vectors = service.embed(["one", "two"])
    assert vectors.shape[0] == 2
