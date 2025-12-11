from pathlib import Path
from dataclasses import dataclass

from unstructured.chunking.basic import chunk_elements
from unstructured.chunking.title import chunk_by_title
from unstructured.partition.auto import partition

import instructor
from pydantic import BaseModel

from src.utils import logger, generate_hash


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


class SemanticChunk(BaseModel):
    """Pydantic agents for instructor-based semantic chunking."""
    content: str
    topic: str
    category: str
    summary: str
    importance_score: float
    should_split: bool = False
    split_reason: str | None = None


def semantic_chunking(
    content: str,
    instructor_client: instructor.Instructor,
    max_chunk_size: int = 512
) -> list[SemanticChunk]:
    """Use instructor to create semantic chunks that respect content boundaries."""
    try:
        if len(content) <= max_chunk_size:
            response = instructor_client.chat.completions.create(
                response_model=SemanticChunk,
                messages=[
                    {"role": "system", "content": "Analyze this text chunk and provide semantic metadata."},
                    {"role": "user", "content": content}
                ],
            )
            return [response]

        chunks = []
        remaining_content = content

        while len(remaining_content) > max_chunk_size:
            # Take a portion and ask instructor to find the best split point
            portion = remaining_content[:max_chunk_size * 2]

            response = instructor_client.chat.completions.create(
                response_model=SemanticChunk,
                messages=[
                    {"role": "system", "content": f"Find the best semantic split point in this text around "
                                                  f"{max_chunk_size} characters. If the text should be split, "
                                                  f"set should_split=True and provide the split reason."},
                    {"role": "user", "content": portion}
                ],
            )

            if response.should_split and len(response.content) < len(portion):
                chunks.append(response)
                remaining_content = remaining_content[len(response.content):]
            else:
                # TODO: should increase portion if not split point?
                chunk_content = remaining_content[:max_chunk_size]
                chunk = SemanticChunk(
                    content=chunk_content,
                    topic="Unknown",
                    category="Unknown",
                    summary="Auto-generated chunk",
                    importance_score=0.5
                )
                chunks.append(chunk)
                remaining_content = remaining_content[max_chunk_size:]

        # Add remaining content as final chunk
        if remaining_content.strip():
            final_response = instructor_client.chat.completions.create(
                response_model=SemanticChunk,
                messages=[
                    {"role": "system", "content": "Analyze this final text chunk."},
                    {"role": "user", "content": remaining_content}
                ],
            )
            chunks.append(final_response)

        return chunks

    except Exception as e:
        logger.error(f"Error in semantic chunking with instructor, fallback to simple chunking: {e}")
        simple_chunks = []
        for i in range(0, len(content), max_chunk_size):
            chunk_content = content[i:i + max_chunk_size]
            chunk = SemanticChunk(
                content=chunk_content,
                topic="Unknown",
                category="Fallback",
                summary="Auto-generated fallback chunk",
                importance_score=0.5
            )
            simple_chunks.append(chunk)
        return simple_chunks


def split_file(
    file: str | Path,
    strategy: str = "basic",
    chunk_size: int = 512,
    overlap_size: int = 128,
    instructor_client: instructor.Instructor | None = None,
    **kwargs,
) -> list[dict]:
    """
    Split a file into chunks using specified strategy and enrich with metadata.

    Args:
        file: Path to the file.
        strategy: Chunking strategy ("basic", "by_title", "semantic").
        chunk_size: Maximum chunk size.
        overlap_size: Overlap between chunks.
        instructor_client: Instructor client for semantic analysis. Required for semantic chunking strategy.
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
            if not instructor_client:
                raise ValueError("Instructor client is required for semantic strategy.")

            full_text = "\n".join([str(elem) for elem in elements])
            semantic_chunks = semantic_chunking(full_text, instructor_client, chunk_size)

            for i, sem_chunk in enumerate(semantic_chunks):
                chunk_id = f"{file_path.stem}_{i}_{generate_hash(sem_chunk.content)[:8]}"

                metadata = ChunkMetadata(
                    filename=file_path.name,
                    file_path=str(file_path),
                    file_type=file_path.suffix.lower(),
                    chunk_index=i,
                    chunk_id=chunk_id,
                    content_hash=generate_hash(sem_chunk.content),
                    topic=sem_chunk.topic,
                    category=sem_chunk.category,
                    summary=sem_chunk.summary,
                    word_count=len(sem_chunk.content.split()),
                    char_count=len(sem_chunk.content)
                )

                chunks.append({
                    "id": chunk_id,
                    "text": sem_chunk.content,
                    "metadata": metadata.__dict__,
                    "importance_score": sem_chunk.importance_score
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
