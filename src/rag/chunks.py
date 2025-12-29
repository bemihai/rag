from pathlib import Path
from dataclasses import dataclass
from typing import List

from unstructured.chunking.basic import chunk_elements
from unstructured.chunking.title import chunk_by_title
from unstructured.partition.auto import partition

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_experimental.text_splitter import SemanticChunker

from src.utils import logger, generate_hash


# Module-level embedder cache for semantic chunking
_chunker_embedder_cache: dict = {}


def _get_chunker_embedder(model_name: str) -> HuggingFaceEmbeddings:
    """Get or create cached embedder for semantic chunking."""
    if model_name not in _chunker_embedder_cache:
        _chunker_embedder_cache[model_name] = HuggingFaceEmbeddings(model_name=model_name)
    return _chunker_embedder_cache[model_name]


@dataclass
class ChunkMetadata:
    """Dataclass for chunk metadata."""
    filename: str
    file_path: str
    file_type: str
    chunk_index: int
    chunk_id: str
    content_hash: str
    page_number: int = -1
    language: str = "unknown"
    category: str = "unknown"
    topic: str = "unknown"
    summary: str = "none"
    word_count: int = 0
    char_count: int = 0


def semantic_chunking(
    content: str,
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
    breakpoint_threshold_type: str = "percentile",
    breakpoint_threshold_amount: float = 95.0,
) -> List[str]:
    """
    Create semantic chunks using LangChain's SemanticChunker.

    Uses local embeddings to find semantic boundaries - no LLM calls required.

    Args:
        content: Text content to chunk.
        embedding_model: HuggingFace model name for embeddings.
        breakpoint_threshold_type: How to determine breakpoints. Options:
            - "percentile": Break at percentile threshold of distances
            - "standard_deviation": Break at standard deviation threshold
            - "interquartile": Break at interquartile range threshold
        breakpoint_threshold_amount: Threshold value for breakpoint detection.
            For percentile: 95.0 means break at 95th percentile of distances.

    Returns:
        List of chunk text strings.
    """
    try:
        embedder = _get_chunker_embedder(embedding_model)

        chunker = SemanticChunker(
            embeddings=embedder,
            breakpoint_threshold_type=breakpoint_threshold_type,
            breakpoint_threshold_amount=breakpoint_threshold_amount,
        )

        documents = chunker.create_documents([content])
        chunks = [doc.page_content for doc in documents]

        logger.debug(f"Semantic chunking created {len(chunks)} chunks")
        return chunks

    except Exception as e:
        logger.error(f"Error in semantic chunking, falling back to simple split: {e}")
        # Fallback to simple sentence-based splitting
        sentences = content.replace('\n', ' ').split('. ')
        chunks = []
        current_chunk = ""

        for sentence in sentences:
            if len(current_chunk) + len(sentence) > 1000:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence + ". "
            else:
                current_chunk += sentence + ". "

        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        return chunks if chunks else [content]


def split_file(
    file: str | Path,
    strategy: str = "basic",
    chunk_size: int = 512,
    overlap_size: int = 128,
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
    **kwargs,
) -> list[dict]:
    """
    Split a file into chunks using specified strategy and enrich with metadata.

    Args:
        file: Path to the file.
        strategy: Chunking strategy ("basic", "by_title", "semantic").
        chunk_size: Maximum chunk size (used for basic/by_title strategies).
        overlap_size: Overlap between chunks (used for basic/by_title strategies).
        embedding_model: HuggingFace model for semantic chunking (used for semantic strategy).
        **kwargs: Additional arguments for unstructured chunking.

    Returns:
        List of enhanced chunk dictionaries with metadata.
    """
    file_path = Path(file)
    chunks = []

    try:
        logger.info(f"Processing file: {file_path.name}")
        elements = partition(filename=str(file_path))

        if strategy == "semantic":
            full_text = "\n".join([str(elem) for elem in elements])
            semantic_chunks = semantic_chunking(
                content=full_text,
                embedding_model=embedding_model,
                breakpoint_threshold_type=kwargs.get("breakpoint_threshold_type", "percentile"),
                breakpoint_threshold_amount=kwargs.get("breakpoint_threshold_amount", 95.0),
            )

            for i, chunk_text in enumerate(semantic_chunks):
                chunk_id = f"{file_path.stem}_{i}_{generate_hash(chunk_text)[:8]}"

                metadata = ChunkMetadata(
                    filename=file_path.name,
                    file_path=str(file_path),
                    file_type=file_path.suffix.lower(),
                    chunk_index=i,
                    chunk_id=chunk_id,
                    content_hash=generate_hash(chunk_text),
                    word_count=len(chunk_text.split()),
                    char_count=len(chunk_text)
                )

                chunks.append({
                    "id": chunk_id,
                    "text": chunk_text,
                    "metadata": metadata.__dict__,
                    "importance_score": 1.0
                })
        else:
            if strategy == "basic":
                unstructured_chunks = chunk_elements(
                    elements, max_characters=chunk_size, overlap=overlap_size, **kwargs
                )
            elif strategy == "by_title":
                unstructured_chunks = chunk_by_title(
                    elements, max_characters=chunk_size, overlap=overlap_size, **kwargs
                )
            else:
                raise ValueError(f"Unknown chunking strategy: {strategy}")

            for i, chunk in enumerate(unstructured_chunks):
                chunk_text = str(chunk)
                chunk_id = f"{file_path.stem}_{i}_{generate_hash(chunk_text)[:8]}"

                # Extract metadata from unstructured chunk
                chunk_metadata = {}
                if hasattr(chunk, "metadata") and chunk.metadata:
                    if hasattr(chunk.metadata, "to_dict"):
                        chunk_metadata = chunk.metadata.to_dict()
                    else:
                        chunk_metadata = chunk.metadata.__dict__

                metadata = ChunkMetadata(
                    filename=file_path.name,
                    file_path=str(file_path),
                    file_type=file_path.suffix.lower(),
                    chunk_index=i,
                    chunk_id=chunk_id,
                    content_hash=generate_hash(chunk_text),
                    page_number=chunk_metadata.get("page_number", -1),
                    language=chunk_metadata.get("languages", ["unknown"])[0],
                    word_count=len(chunk_text.split()),
                    char_count=len(chunk_text)
                )

                chunks.append({
                    "id": chunk_id,
                    "text": chunk_text,
                    "metadata": metadata.__dict__,
                    "importance_score": 1.0  # Default importance
                })

        logger.info(f"Generated {len(chunks)} chunks from {file_path.name}")
        return chunks

    except Exception as e:
        logger.error(f"Error processing file {file_path}: {e}")
        return []
