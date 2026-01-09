import hashlib
import json
import os
from pathlib import Path

import numpy as np
from omegaconf import DictConfig, OmegaConf
import chromadb as cdb

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


def find_project_root(marker="pyproject.toml"):
    """
    Walks up from the current file to find the project root.
    The marker can be a file or folder like '.git' or 'pyproject.toml'
    """
    current_path = os.path.abspath(os.getcwd())
    while current_path != os.path.dirname(current_path):
        if marker in os.listdir(current_path):
            return current_path
        current_path = os.path.dirname(current_path)
    raise FileNotFoundError(f"Project root with {marker} not found.")


def get_project_root() -> Path:
    """Returns the project root path."""
    return Path(find_project_root())


def get_default_db_path():
    """Returns the default wine cellar database path."""
    cfg = get_config()
    return get_project_root() / cfg.cellar.db_path


def get_config() -> DictConfig:
    """Returns the app config object."""
    return OmegaConf.load(Path(find_project_root()) / "app_config.yml")


def get_initial_message():
    """Returns the initial message from config."""
    cfg = get_config()
    msg = cfg.initial_message
    return [
        {
            "role": msg["role"] if "role" in msg else "ai",
            "answer": msg["answer"] if "answer" in msg else "Welcome! Ask me anything about wine."
        }
    ]


def generate_hash(content: str) -> str:
    """Generate a hash for content to detect duplicates."""
    return hashlib.md5(content.encode()).hexdigest()


def compute_file_hash(file_path: Path) -> str:
    """Compute MD5 hash of a file's contents."""
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
    """
    Compute cosine similarity between two vectors.

    Args:
        vec1: First vector.
        vec2: Second vector.

    Returns:
        Cosine similarity score between -1 and 1.
    """
    dot_product = np.dot(vec1, vec2)
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)

    if norm1 == 0 or norm2 == 0:
        return 0.0

    return float(dot_product / (norm1 * norm2))


def load_json(filepath: str | Path) -> dict | list:
    """Load JSON file from path."""
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)



