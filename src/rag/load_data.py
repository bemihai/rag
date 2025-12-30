"""Runnable script for processing external data and loading to ChromaDB."""
import os

from src.rag import CollectionDataLoader
from src.utils import get_config, logger

os.environ["TOKENIZERS_PARALLELISM"] = "false"


if __name__ == "__main__":

    cfg = get_config()
    chroma_cfg = cfg.chroma

    logger.info(f"Loading {len(chroma_cfg.collections)} collection(s) to ChromaDB")
    for collection in chroma_cfg.collections:

        loader = CollectionDataLoader(
            collection_name=collection.name,
            collection_metadata=collection.metadata,
            chroma_host=chroma_cfg.client.host,
            chroma_port=chroma_cfg.client.port,
            embedding_model=chroma_cfg.settings.embedder,
            batch_size=chroma_cfg.settings.batch_size,
        )

        # Get extract_wine_metadata from config, default to True
        extract_wine_metadata = getattr(chroma_cfg.chunking, 'extract_wine_metadata', True)

        stats = loader.load_directory(
            file_extensions=[".epub", ".pdf"],
            data_path=collection.local_data_path,
            strategy=chroma_cfg.chunking.strategy,
            chunk_size=chroma_cfg.chunking.chunk_size,
            overlap_size=chroma_cfg.chunking.chunk_overlap,
            extract_wine_metadata=extract_wine_metadata,
        )