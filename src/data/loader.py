from pathlib import Path
from tqdm import tqdm
import time

from langchain_huggingface import HuggingFaceEmbeddings
import instructor

from src.data.chunks import split_file
from src.utils import logger, initialize_chroma_client, get_or_create_collection, create_chroma_batches, validate_chunks


class CollectionDataLoader:
    """
    Data loader class for processing and loading documents into a ChromaDB collection.
    If the provided collection does not exist, a new one will be created.

    Args:
        collection_name: Name of the ChromaDB collection.
        collection_metadata: Optional metadata for the collection.
        chroma_host: Host for ChromaDB.
        chroma_port: Port for ChromaDB.
        embedding_model: HuggingFace model name for embeddings.
        batch_size: Number of documents to process in each batch.
        use_instructor: Whether to use semantic chunking with Instructor.
        gemini_model: Optional, model name for Google Gemini if using Instructor. Should be
            a string like 'google/gemini-2.5-flash'.
        gemini_api_key: Optional, the API key for Google Gemini if using Instructor.
    """
    def __init__(
        self,
        collection_name: str,
        collection_metadata: dict,
        chroma_host: str,
        chroma_port: int,
        embedding_model: str,
        batch_size: int = 2500,
        use_instructor: bool = False,
        gemini_model: str | None = None,
        gemini_api_key: str | None = None,
    ):
        self.collection_name = collection_name
        self.batch_size = batch_size
        self.use_instructor = use_instructor
        self.gemini_model = gemini_model
        self.embedder = HuggingFaceEmbeddings(model_name=embedding_model)
        self.instructor_client = None

        # Initialize instructor client with Gemini if required
        if use_instructor and gemini_api_key:
            # Use the new from_provider approach to avoid deprecation warning
            self.instructor_client = instructor.from_provider(gemini_model, api_key=gemini_api_key)
            logger.info("Instructor client with Gemini initialized for semantic chunking.")

        # Initialize or get ChromaDB collection
        self.client = initialize_chroma_client(chroma_host, chroma_port)
        self.collection = get_or_create_collection(self.client, collection_name, collection_metadata)


    def _check_duplicate(self, content_hash: str) -> bool:
        """Check if content already exists in the collection."""
        try:
            results = self.collection.get(where={"content_hash": content_hash}, limit=1)
            return len(results["ids"]) > 0
        except Exception as e:
            logger.warning(f"Error checking for duplicates: {e}")
            return False


    def process_file(
        self,
        file_path: str | Path,
        strategy: str = "basic",
        chunk_size: int = 512,
        overlap_size: int = 128,
        skip_duplicates: bool = True,
    ) -> dict:
        """
        Process a single file and return a dict with stats.

        Args:
            file_path: Path to the file to process.
            strategy: Chunking strategy ("basic", "by_title", "semantic").
            chunk_size: Size of each chunk.
            overlap_size: Overlap size between chunks.
            skip_duplicates: Whether to skip duplicate chunks based on content hash.
        """
        file_path = Path(file_path)
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
                instructor_client=self.instructor_client,
            )

            if not chunks:
                stats["errors"].append("No chunks generated")
                return stats

            stats["chunks_generated"] = len(chunks)

            # Validate chunks
            valid_chunks = validate_chunks(chunks)

            # Prepare the chunked data for ChromaDB
            docs = []
            metadata_list = []
            ids = []

            for chunk in valid_chunks:
                if skip_duplicates and self._check_duplicate(chunk["metadata"]["content_hash"]):
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
        data_path: str | Path,
        file_extensions: list[str] = [".epub", ".pdf"],
        strategy: str = "basic",
        chunk_size: int = 512,
        overlap_size: int = 128,
        skip_duplicates: bool = True,
    ) -> dict:
        """
        Load all files from directory with progress tracking. Returns a summary dict.

        Args:
            data_path: Path to the directory containing files.
            file_extensions: List of file extensions to process, ex: [".epub", ".pdf"].
            strategy: Chunking strategy ("basic", "by_title", "semantic").
            chunk_size: Size of each chunk.
            overlap_size: Overlap size between chunks.
            skip_duplicates: Whether to skip duplicate chunks based on content hash.
        """

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



