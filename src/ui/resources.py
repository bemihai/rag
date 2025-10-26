"""Cached resources for the Streamlit app."""
import streamlit as st

from src.model.llm import load_base_model
from src.data import ChromaRetriever
from src.utils import get_config, logger
from src.utils.chroma import initialize_chroma_client


@st.cache_resource
def load_llm():
    """Load model wrapper to allow caching."""
    cfg = get_config()
    return load_base_model(cfg.model.provider, cfg.model.name)


@st.cache_resource
def load_chroma_client():
    """Initialize ChromaDB client with caching to avoid reconnection."""
    cfg = get_config()
    chroma_cfg = cfg.chroma

    try:
        client = initialize_chroma_client(
            host=chroma_cfg.client.host,
            port=chroma_cfg.client.port
        )
        return client
    except Exception as e:
        logger.error(f"Failed to initialize ChromaDB client: {e}")
        st.error(
            f"⚠️ Unable to connect to ChromaDB at {chroma_cfg.client.host}:{chroma_cfg.client.port}. "
            "RAG features will be disabled. Using LLM general knowledge only."
        )
        return None


@st.cache_resource
def load_retriever():
    """Initialize ChromaRetriever with caching."""
    try:
        cfg = get_config()
        chroma_cfg = cfg.chroma
        client = load_chroma_client()

        if client is None:
            logger.warning("ChromaDB client is unavailable. Retriever not initialized.")
            return None

        collection_name = chroma_cfg.collections[0].name

        return ChromaRetriever(
            client=client,
            collection_name=collection_name,
            embedding_model=chroma_cfg.settings.embedder,
            n_results=chroma_cfg.retrieval.n_results,
            similarity_threshold=chroma_cfg.retrieval.similarity_threshold,
        )
    except Exception as e:
        logger.error(f"Failed to initialize retriever: {e}")
        st.warning(
            "⚠️ Could not initialize the retrieval system. "
            "RAG features are unavailable. Answers will be based on general knowledge only."
        )
        return None

