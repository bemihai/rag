

def create_chroma_batches(
        ids: list,
        embeddings: list | None = None,
        metadata: list | None = None,
        documents: list | None = None,
        batch_size: int = 1000,
) -> list[tuple]:
    """Create batches for ChromaDB to avoid FastAPI errors with large collections."""
    _batches = []
    if len(ids) > batch_size:
        for i in range(0, len(ids), batch_size):
            _batches.append(
                (
                    ids[i : i + batch_size],
                    embeddings[i : i + batch_size] if embeddings else None,
                    metadata[i: i + batch_size] if metadata else None,
                    documents[i : i + batch_size] if documents else None,
                )
            )
    else:
        _batches.append((ids, embeddings, metadata, documents))
    return _batches