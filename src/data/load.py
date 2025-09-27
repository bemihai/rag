from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from tqdm import tqdm
import time
import streamlit as st

import chromadb
from langchain_huggingface import HuggingFaceEmbeddings
import instructor

from src.data.chunks import split_file, create_chroma_batches, validate_chunks, generate_content_hash
from src.utils import get_config, logger


class DataLoader:
    """Enhanced data loader with better error handling and progress tracking."""

    def __init__(
        self,
        collection_name: str = "wine_books",
        chroma_host: str = "localhost",
        chroma_port: str = "8000",
        embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
        batch_size: int = 2500,
        use_instructor: bool = False,
        gemini_api_key: Optional[str] = None,  # Changed from openai_api_key
    ):
        self.collection_name = collection_name
        self.batch_size = batch_size
        self.use_instructor = use_instructor

        # Initialize ChromaDB client with retry logic
        self.client = self._initialize_chroma_client(chroma_host, chroma_port)

        # Initialize embedder
        self.embedder = HuggingFaceEmbeddings(model_name=embedding_model)

        # Initialize instructor client with Gemini if needed
        self.instructor_client = None
        if use_instructor and gemini_api_key:
            # Use the new from_provider approach to avoid deprecation warning
            self.instructor_client = instructor.from_provider(
                'google/gemini-2.5-flash-preview-05-20',
                api_key=gemini_api_key
            )
            logger.info("Instructor client initialized for semantic chunking with Gemini")

        # Initialize or get collection
        self.collection = self._get_or_create_collection()

    def _initialize_chroma_client(
        self, host: str, port: int, max_retries: int = 3
    ) -> chromadb.Client:
        """Initialize ChromaDB client with retry logic."""
        for attempt in range(max_retries):
            try:
                client = chromadb.HttpClient(host=host, port=port)
                # Test connection
                client.heartbeat()
                logger.info(f"Connected to ChromaDB at {host}:{port}")
                return client
            except Exception as e:
                logger.warning(f"Failed to connect to ChromaDB (attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    raise ConnectionError(
                        f"Could not connect to ChromaDB after {max_retries} attempts"
                    )

    def _get_or_create_collection(self):
        """Get or create ChromaDB collection with optimized settings."""
        try:
            collection = self.client.get_collection(self.collection_name)
            logger.info(f"Using existing collection: {self.collection_name}")
        except Exception:
            collection = self.client.create_collection(
                name=self.collection_name,
                metadata={
                    "description": "Enhanced wine books collection with semantic chunking",
                    "created": str(datetime.now()),
                    "hnsw:space": "cosine",  # similarity measure
                    "hnsw:search_ef": 100,  # num candidates for searching
                    "hnsw:construction_ef": 200,  # increased for better indexing
                    "hnsw:num_threads": 8,  # num of threads for indexing
                    "version": "v1.1",
                },
            )
            logger.info(f"Created new collection: {self.collection_name}")

        return collection

    def check_duplicate(self, content_hash: str) -> bool:
        """Check if content already exists in the collection."""
        try:
            results = self.collection.get(
                where={"content_hash": content_hash}, limit=1
            )
            return len(results["ids"]) > 0
        except Exception as e:
            logger.warning(f"Error checking for duplicates: {e}")
            return False

    def process_file(
        self,
        file_path: Path,
        strategy: str = "basic",
        chunk_size: int = 512,
        overlap_size: int = 128,
        skip_duplicates: bool = True,
    ) -> Dict[str, Any]:
        """Process a single file and return statistics."""
        start_time = time.time()
        stats = {
            "filename": file_path.name,
            "chunks_generated": 0,
            "chunks_added": 0,
            "chunks_skipped": 0,
            "processing_time": 0,
            "errors": [],
        }

        try:
            logger.info(f"Processing file: {file_path.name}")

            # Generate chunks
            chunks = split_file(
                file=file_path,
                strategy=strategy,
                chunk_size=chunk_size,
                overlap_size=overlap_size,
                use_instructor=self.use_instructor,
                instructor_client=self.instructor_client,
            )

            if not chunks:
                stats["errors"].append("No chunks generated")
                return stats

            stats["chunks_generated"] = len(chunks)

            # Validate chunks
            valid_chunks = validate_chunks(chunks)

            # Prepare data for ChromaDB
            docs = []
            embeddings = []
            metadata_list = []
            ids = []

            for chunk in valid_chunks:
                # Skip duplicates if requested
                if skip_duplicates and self.check_duplicate(chunk["metadata"]["content_hash"]):
                    stats["chunks_skipped"] += 1
                    continue

                docs.append(chunk["text"])
                ids.append(chunk["id"])
                metadata_list.append(chunk["metadata"])

            if not docs:
                logger.info(f"No new chunks to add from {file_path.name}")
                stats["processing_time"] = time.time() - start_time
                return stats

            # Generate embeddings
            logger.info(f"Generating embeddings for {len(docs)} chunks...")
            embeddings = self.embedder.embed_documents(docs)

            # Add to ChromaDB in batches
            batches = create_chroma_batches(
                batch_size=self.batch_size,
                documents=docs,
                embeddings=embeddings,
                metadata=metadata_list,
                ids=ids,
            )

            for i, batch in enumerate(batches):
                try:
                    self.collection.add(
                        ids=batch[0],
                        embeddings=batch[1],
                        metadatas=batch[2],
                        documents=batch[3],
                    )
                    logger.debug(f"Added batch {i+1}/{len(batches)} for {file_path.name}")
                except Exception as e:
                    error_msg = f"Error adding batch {i+1}: {e}"
                    stats["errors"].append(error_msg)
                    logger.error(error_msg)

            stats["chunks_added"] = len(docs)
            logger.info(f"Successfully added {len(docs)} chunks from {file_path.name}")

        except Exception as e:
            error_msg = f"Error processing file {file_path.name}: {e}"
            stats["errors"].append(error_msg)
            logger.error(error_msg)

        stats["processing_time"] = time.time() - start_time
        return stats

    def load_directory(
        self,
        data_path: str,
        file_extensions: List[str] = [".epub", ".pdf", ".txt", ".md"],
        strategy: str = "basic",
        chunk_size: int = 512,
        overlap_size: int = 128,
        skip_duplicates: bool = True,
    ) -> Dict[str, Any]:
        """Load all files from directory with progress tracking."""

        data_dir = Path(data_path)
        if not data_dir.exists():
            raise ValueError(f"Data directory {data_path} does not exist")

        # Find all files
        files_to_process = []
        for ext in file_extensions:
            files_to_process.extend(data_dir.glob(f"**/*{ext}"))

        if not files_to_process:
            logger.warning(f"No files found with extensions {file_extensions} in {data_path}")
            return {"total_files": 0, "files_processed": 0, "total_chunks": 0}

        logger.info(f"Found {len(files_to_process)} files to process")

        # Process files with progress bar
        total_stats = {
            "total_files": len(files_to_process),
            "files_processed": 0,
            "successful_files": 0,
            "failed_files": 0,
            "total_chunks_generated": 0,
            "total_chunks_added": 0,
            "total_chunks_skipped": 0,
            "total_processing_time": 0,
            "file_results": [],
            "errors": [],
        }

        with tqdm(files_to_process, desc="Processing files") as pbar:
            for file_path in pbar:
                pbar.set_description(f"Processing {file_path.name}")

                file_stats = self.process_file(
                    file_path=file_path,
                    strategy=strategy,
                    chunk_size=chunk_size,
                    overlap_size=overlap_size,
                    skip_duplicates=skip_duplicates,
                )

                # Update total stats
                total_stats["files_processed"] += 1
                total_stats["total_chunks_generated"] += file_stats["chunks_generated"]
                total_stats["total_chunks_added"] += file_stats["chunks_added"]
                total_stats["total_chunks_skipped"] += file_stats["chunks_skipped"]
                total_stats["total_processing_time"] += file_stats["processing_time"]
                total_stats["file_results"].append(file_stats)

                if file_stats["errors"]:
                    total_stats["failed_files"] += 1
                    total_stats["errors"].extend(file_stats["errors"])
                else:
                    total_stats["successful_files"] += 1

                # Update progress bar
                pbar.set_postfix(
                    {
                        "chunks": total_stats["total_chunks_added"],
                        "errors": len(total_stats["errors"]),
                    }
                )

        # Log final summary
        logger.info(
            f"""
        Processing Complete:
        - Files processed: {total_stats['files_processed']}/{total_stats['total_files']}
        - Successful: {total_stats['successful_files']}
        - Failed: {total_stats['failed_files']}
        - Total chunks added: {total_stats['total_chunks_added']}
        - Total chunks skipped: {total_stats['total_chunks_skipped']}
        - Total processing time: {total_stats['total_processing_time']:.2f}s
        """
        )

        return total_stats

    def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the current collection."""
        try:
            count = self.collection.count()
            return {
                "collection_name": self.collection_name,
                "total_documents": count,
                "last_updated": str(datetime.now()),
            }
        except Exception as e:
            logger.error(f"Error getting collection stats: {e}")
            return {"error": str(e)}


# Convenience function for backward compatibility
def load_wine_books(
    data_path: str,
    use_instructor: bool = False,
    gemini_api_key: Optional[str] = None,
    strategy: str = "basic",
    chunk_size: int = 512,
) -> Dict[str, Any]:
    """Load wine books with enhanced processing."""

    loader = DataLoader(
        use_instructor=use_instructor, gemini_api_key=gemini_api_key  # Changed parameter name
    )

    return loader.load_directory(
        data_path=data_path, strategy=strategy, chunk_size=chunk_size
    )


# Example usage
if __name__ == "__main__":

    cfg = get_config()

    # Basic loading
    # results = load_wine_books(data_path=cfg.data.local_path)
    # print("Processing results:", results)

    # With instructor using Gemini (requires Google API key)
    results = load_wine_books(
        data_path=cfg.data.local_path,
        use_instructor=True,
        gemini_api_key=st.secrets["GOOGLE_API_KEY"],  # Changed from OPENAI_API_KEY
        strategy="semantic"
    )
