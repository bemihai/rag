import hashlib
import os
from pathlib import Path

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



