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

