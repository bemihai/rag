"""ChromaDB utility functions."""
from datetime import datetime

import chromadb as cdb
from chromadb.errors import NotFoundError

from src.utils import logger


def initialize_chroma_client(host: str, port: int) -> cdb.ClientAPI:
    """
    Initialize the ChromaDB client.

    Args:
        host: The host address of the ChromaDB server.
        port: The port number of the ChromaDB server.

    Returns an instance of the ChromaDB client.
    """
    client = cdb.HttpClient(host=host, port=port)
    client.heartbeat()
    logger.info(f"Connected to ChromaDB at {host}:{port}")

    return client


def create_chroma_batches(
        ids: list,
        embeddings: list | None = None,
        metadata: list | None = None,
        documents: list | None = None,
        batch_size: int = 1000,
) -> list[tuple]:
    """Create batches for ChromaDB to avoid FastAPI errors with large collections."""
    batches = []
    if len(ids) > batch_size:
        for i in range(0, len(ids), batch_size):
            batches.append(
                (
                    ids[i : i + batch_size],
                    embeddings[i : i + batch_size] if embeddings else None,
                    metadata[i: i + batch_size] if metadata else None,
                    documents[i : i + batch_size] if documents else None,
                )
            )
    else:
        batches.append((ids, embeddings, metadata, documents))

    return batches


def get_or_create_collection(client: cdb.ClientAPI, name: str, metadata: dict | None = None) -> cdb.Collection:
    """
    Get or create a ChromaDB collection.

    Args:
        client: An instance of the ChromaDB client.
        name: The name of the collection.
        metadata: Optional metadata for the collection.

    Returns an instance of the ChromaDB collection.
    """
    try:
        collection = client.get_collection(name)
        logger.info(f"Using existing collection: {name}")
    except NotFoundError as _:
        metadata = metadata or {}
        metadata["created"] = str(datetime.now())
        collection = client.create_collection(name=name, metadata=dict(metadata))
        logger.info(f"Created new collection: {name}")

    return collection


def validate_chunks(chunks: list[dict]) -> list[dict]:
    """Validate and filter chunks for quality."""
    valid_chunks = []

    for chunk in chunks:
        text = chunk.get("text", "").strip()

        # Skip empty or very short chunks
        if len(text) < 10:
            continue

        # Skip chunks with too little actual content
        if len(text.split()) < 3:
            continue

        valid_chunks.append(chunk)

    logger.info(f"Validated {len(valid_chunks)} chunks from {len(chunks)} total")
    return valid_chunks

