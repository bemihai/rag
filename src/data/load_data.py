"""Runnable script for processing external data and loading to ChromaDB."""
from src.data import CollectionDataLoader
from src.utils import get_config, logger
from src.utils.env import GOOGLE_API_KEY


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
            use_instructor=False,
            gemini_model=f"{cfg.model.provider}/{cfg.model.name}",
            gemini_api_key=GOOGLE_API_KEY,
        )

        stats =loader.load_directory(
            file_extensions=[".epub", ".pdf"],
            data_path=collection.local_data_path,
            strategy=chroma_cfg.chunking.strategy,
            chunk_size=chroma_cfg.chunking.chunk_size,
            overlap_size=chroma_cfg.chunking.chunk_overlap,
        )

        # # Basic loading
        # # results = load_wine_books(data_path=cfg.data.local_path)
        # # print("Processing results:", results)
        #
        # # With instructor using Gemini (requires Google API key)
        # res = load_wine_books(
        #     data_path=cfg.data.local_path,
        #     use_instructor=True,
        #     gemini_api_key=st.secrets["GOOGLE_API_KEY"],  # Changed from OPENAI_API_KEY
        #     strategy="semantic"
        # )