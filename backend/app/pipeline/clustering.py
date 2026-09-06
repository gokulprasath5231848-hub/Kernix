import numpy as np
from collections import Counter
import logging

logger = logging.getLogger(__name__)

def cluster_activities(labels: list[str], embeddings: np.ndarray, distance_threshold: float = 0.35) -> list[dict]:
    if not labels or len(labels) == 0:
        return []
        
    if len(labels) == 1:
        return [{"name": labels[0], "labels": [labels[0]], "count": 1}]
        
    embeddings = np.asarray(embeddings, dtype=np.float64)

    # Cosine distance is undefined for zero vectors and sklearn raises on them.
    # Replace any with a unique unit vector so degenerate input degrades to
    # "everything is dissimilar" instead of crashing the pipeline.
    norms = np.linalg.norm(embeddings, axis=1)
    for idx in np.where(norms == 0)[0]:
        embeddings[idx, idx % embeddings.shape[1]] = 1.0

    try:
        from sklearn.cluster import AgglomerativeClustering
        
        # 1 - cosine similarity = cosine distance
        clustering = AgglomerativeClustering(
            n_clusters=None, 
            metric='cosine', 
            linkage='average',
            distance_threshold=distance_threshold
        )
        
        cluster_labels = clustering.fit_predict(embeddings)
        
        clusters = {}
        for idx, cluster_id in enumerate(cluster_labels):
            if cluster_id not in clusters:
                clusters[cluster_id] = []
            clusters[cluster_id].append(labels[idx])
            
        result = []
        for cluster_id, items in clusters.items():
            counter = Counter(items)
            canonical_name = counter.most_common(1)[0][0]
            result.append({
                "name": canonical_name,
                "labels": items,
                "count": len(items)
            })
            
        return result
    except ImportError:
        logger.warning("scikit-learn not installed. Returning single cluster.")
        return [{"name": labels[0], "labels": labels, "count": len(labels)}]
