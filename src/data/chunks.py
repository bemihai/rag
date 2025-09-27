from pathlib import Path
from typing import List, Dict, Any, Optional, Union
import hashlib
import logging
from dataclasses import dataclass

from pypdf import PdfReader
from unstructured.chunking.basic import chunk_elements
from unstructured.chunking.title import chunk_by_title
from unstructured.partition.auto import partition
import instructor
from pydantic import BaseModel

from src.utils import logger

@dataclass
class ChunkMetadata:
    """Enhanced metadata for document chunks."""
    filename: str
    file_path: str
    file_type: str
    chunk_index: int
    chunk_id: str
    content_hash: str
    page_number: Optional[int] = None
    language: Optional[str] = None
    category: Optional[str] = None
    topic: Optional[str] = None
    summary: Optional[str] = None
    word_count: int = 0
    char_count: int = 0

class SemanticChunk(BaseModel):
    """Pydantic model for instructor-based semantic chunking."""
    content: str
    topic: str
    category: str
    summary: str
    importance_score: float
    should_split: bool = False
    split_reason: Optional[str] = None

class DocumentStructure(BaseModel):
    """Model for analyzing document structure with instructor."""
    title: str
    sections: List[str]
    main_topics: List[str]
    document_type: str
    language: str
    complexity_level: str

def create_chroma_batches(
        ids: list,
        embeddings: list | None = None,
        metadata: list | None = None,
        documents: list | None = None,
        batch_size: int = 1000,
) -> list[tuple]:
    """Create batches for ChromaDB to avoid FastAPI errors with large collections."""
    _batches = []
    if len(ids) > batch_size:
        for i in range(0, len(ids), batch_size):
            _batches.append(
                (
                    ids[i : i + batch_size],
                    embeddings[i : i + batch_size] if embeddings else None,
                    metadata[i: i + batch_size] if metadata else None,
                    documents[i : i + batch_size] if documents else None,
                )
            )
    else:
        _batches.append((ids, embeddings, metadata, documents))
    return _batches

def generate_content_hash(content: str) -> str:
    """Generate a hash for content to detect duplicates."""
    return hashlib.md5(content.encode()).hexdigest()

def analyze_document_structure(file_path: Path, instructor_client: instructor.Instructor) -> DocumentStructure:
    """Analyze document structure using instructor for better chunking strategy."""
    try:
        # Read first few pages for structure analysis
        elements = partition(filename=str(file_path))
        sample_text = "\n".join([str(elem) for elem in elements[:10]])  # First 10 elements

        response = instructor_client.chat.completions.create(
            model="gemini-1.5-flash",  # Model name stays the same
            response_model=DocumentStructure,
            messages=[
                {"role": "system", "content": "Analyze the document structure and classify it for optimal chunking."},
                {"role": "user", "content": f"Analyze this document excerpt:\n\n{sample_text[:2000]}"}
            ],
        )
        return response
    except Exception as e:
        logger.warning(f"Failed to analyze document structure for {file_path}: {e}")
        return DocumentStructure(
            title="Unknown",
            sections=[],
            main_topics=[],
            document_type="unknown",
            language="unknown",
            complexity_level="medium"
        )

def semantic_chunk_with_instructor(
    content: str,
    instructor_client: instructor.Instructor,
    max_chunk_size: int = 512
) -> List[SemanticChunk]:
    """Use instructor to create semantic chunks that respect content boundaries."""
    try:
        # If content is short enough, return as single chunk
        if len(content) <= max_chunk_size:
            response = instructor_client.chat.completions.create(
                model="gemini-1.5-flash",  # Model name stays the same
                response_model=SemanticChunk,
                messages=[
                    {"role": "system", "content": "Analyze this text chunk and provide semantic metadata."},
                    {"role": "user", "content": content}
                ],
            )
            return [response]

        # For longer content, ask instructor to identify split points
        chunks = []
        remaining_content = content

        while len(remaining_content) > max_chunk_size:
            # Take a portion and ask instructor to find the best split point
            portion = remaining_content[:max_chunk_size * 2]  # Take double to find good split

            response = instructor_client.chat.completions.create(
                model="gemini-1.5-flash",  # Model name stays the same
                response_model=SemanticChunk,
                messages=[
                    {"role": "system", "content": f"Find the best semantic split point in this text around {max_chunk_size} characters. If the text should be split, set should_split=True and provide the split reason."},
                    {"role": "user", "content": portion}
                ],
            )

            if response.should_split and len(response.content) < len(portion):
                chunks.append(response)
                remaining_content = remaining_content[len(response.content):]
            else:
                # Fallback to character-based split
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
                model="gemini-1.5-flash",  # Model name stays the same
                response_model=SemanticChunk,
                messages=[
                    {"role": "system", "content": "Analyze this final text chunk."},
                    {"role": "user", "content": remaining_content}
                ],
            )
            chunks.append(final_response)

        return chunks

    except Exception as e:
        logger.error(f"Error in semantic chunking with instructor: {e}")
        # Fallback to simple chunking
        simple_chunks = []
        for i in range(0, len(content), max_chunk_size):
            chunk_content = content[i:i + max_chunk_size]
            chunk = SemanticChunk(
                content=chunk_content,
                topic="Unknown",
                category="Fallback",
                summary="Auto-generated fallback chunk",
                importance_score=0.3
            )
            simple_chunks.append(chunk)
        return simple_chunks

def split_file(
    file: Union[str, Path],
    strategy: str = "basic",
    chunk_size: int = 512,
    overlap_size: int = 128,
    use_instructor: bool = False,
    instructor_client: Optional[instructor.Instructor] = None,
    **kwargs,
) -> List[Dict[str, Any]]:
    """
    Enhanced file splitting with instructor integration and better metadata.

    Args:
        file: Path to the file
        strategy: Chunking strategy ("basic", "by_title", "semantic")
        chunk_size: Maximum chunk size
        overlap_size: Overlap between chunks
        use_instructor: Whether to use instructor for semantic chunking
        instructor_client: Instructor client for semantic analysis
        **kwargs: Additional arguments

    Returns:
        List of enhanced chunk dictionaries with metadata
    """
    file_path = Path(file)
    chunks = []

    try:
        logger.info(f"Processing file: {file_path.name}")

        # Analyze document structure if using instructor
        doc_structure = None
        if use_instructor and instructor_client:
            doc_structure = analyze_document_structure(file_path, instructor_client)
            logger.info(f"Document analysis: {doc_structure.document_type}, topics: {doc_structure.main_topics}")

        # Get unstructured elements
        elements = partition(filename=str(file_path))

        if strategy == "semantic" and use_instructor and instructor_client:
            # Use instructor for semantic chunking
            full_text = "\n".join([str(elem) for elem in elements])
            semantic_chunks = semantic_chunk_with_instructor(
                full_text, instructor_client, chunk_size
            )

            for i, sem_chunk in enumerate(semantic_chunks):
                chunk_id = f"{file_path.stem}_{i}_{generate_content_hash(sem_chunk.content)[:8]}"

                metadata = ChunkMetadata(
                    filename=file_path.name,
                    file_path=str(file_path),
                    file_type=file_path.suffix.lower(),
                    chunk_index=i,
                    chunk_id=chunk_id,
                    content_hash=generate_content_hash(sem_chunk.content),
                    topic=sem_chunk.topic,
                    category=sem_chunk.category,
                    summary=sem_chunk.summary,
                    word_count=len(sem_chunk.content.split()),
                    char_count=len(sem_chunk.content)
                )

                chunks.append({
                    'id': chunk_id,
                    'text': sem_chunk.content,
                    'metadata': metadata.__dict__,
                    'importance_score': sem_chunk.importance_score
                })

        else:
            # Use traditional unstructured chunking
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
                chunk_id = f"{file_path.stem}_{i}_{generate_content_hash(chunk_text)[:8]}"

                # Extract metadata from unstructured chunk
                chunk_metadata = {}
                if hasattr(chunk, 'metadata') and chunk.metadata:
                    if hasattr(chunk.metadata, 'to_dict'):
                        chunk_metadata = chunk.metadata.to_dict()
                    else:
                        chunk_metadata = chunk.metadata.__dict__

                metadata = ChunkMetadata(
                    filename=file_path.name,
                    file_path=str(file_path),
                    file_type=file_path.suffix.lower(),
                    chunk_index=i,
                    chunk_id=chunk_id,
                    content_hash=generate_content_hash(chunk_text),
                    page_number=chunk_metadata.get('page_number'),
                    language=chunk_metadata.get('languages', [None])[0] if chunk_metadata.get('languages') else None,
                    category=chunk_metadata.get('category'),
                    word_count=len(chunk_text.split()),
                    char_count=len(chunk_text)
                )

                chunks.append({
                    'id': chunk_id,
                    'text': chunk_text,
                    'metadata': metadata.__dict__,
                    'importance_score': 1.0  # Default importance
                })

        logger.info(f"Generated {len(chunks)} chunks from {file_path.name}")
        return chunks

    except Exception as e:
        logger.error(f"Error processing file {file_path}: {e}")
        return []

def validate_chunks(chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Validate and filter chunks for quality."""
    valid_chunks = []

    for chunk in chunks:
        text = chunk.get('text', '').strip()

        # Skip empty or very short chunks
        if len(text) < 10:
            continue

        # Skip chunks with too little actual content
        if len(text.split()) < 3:
            continue

        # Add quality score
        chunk['quality_score'] = min(len(text.split()) / 50, 1.0)  # Normalize by word count

        valid_chunks.append(chunk)

    logger.info(f"Validated {len(valid_chunks)} chunks from {len(chunks)} total")
    return valid_chunks
