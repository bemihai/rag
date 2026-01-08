from langchain_huggingface import HuggingFaceEmbeddings

from src.utils import get_config


# Module-level cache for embedder
embedder_cache: dict[str, HuggingFaceEmbeddings] = {}


def get_embedder(model_name: str | None = None) -> HuggingFaceEmbeddings:
    """Get or create cached embedder instance."""
    if model_name is None:
        cfg = get_config()
        model_name = cfg.chroma.settings.embedder

    if model_name not in embedder_cache:
        embedder_cache[model_name] = HuggingFaceEmbeddings(model_name=model_name)

    return embedder_cache[model_name]
