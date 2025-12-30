"""Index tracking for incremental document ingestion.

This module tracks which files have been indexed into ChromaDB to enable
incremental updates. Only new or modified files are processed, avoiding
redundant re-indexing.
"""
import json
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field, asdict
from datetime import datetime

from src.utils import logger


@dataclass
class IndexedFileInfo:
    """
    Information about an indexed file.

    Attributes:
        file_path: Absolute path to the file.
        file_hash: MD5 hash of file contents for change detection.
        file_size: File size in bytes.
        modified_time: Last modification timestamp.
        indexed_at: When the file was indexed.
        chunk_count: Number of chunks created from this file.
        collection_name: ChromaDB collection the file was indexed into.
    """
    file_path: str
    file_hash: str
    file_size: int
    modified_time: float
    indexed_at: str
    chunk_count: int
    collection_name: str


@dataclass
class IndexManifest:
    """
    Manifest tracking all indexed files for a collection.

    Attributes:
        collection_name: Name of the ChromaDB collection.
        created_at: When the manifest was created.
        updated_at: Last update timestamp.
        files: Dictionary mapping file paths to their index info.
    """
    collection_name: str
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    files: Dict[str, IndexedFileInfo] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert manifest to dictionary for JSON serialization."""
        return {
            "collection_name": self.collection_name,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "files": {k: asdict(v) for k, v in self.files.items()},
        }

    @classmethod
    def from_dict(cls, data: dict) -> "IndexManifest":
        """Create manifest from dictionary."""
        manifest = cls(
            collection_name=data["collection_name"],
            created_at=data.get("created_at", datetime.now().isoformat()),
            updated_at=data.get("updated_at", datetime.now().isoformat()),
        )
        for path, info in data.get("files", {}).items():
            manifest.files[path] = IndexedFileInfo(**info)
        return manifest


def compute_file_hash(file_path: Path) -> str:
    """
    Compute MD5 hash of a file's contents.

    Args:
        file_path: Path to the file.

    Returns:
        Hexadecimal MD5 hash string.
    """
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


class IndexTracker:
    """
    Tracks indexed files to enable incremental updates.

    Maintains a manifest file that records which files have been indexed,
    along with their hashes and modification times. This allows the loader
    to skip files that haven't changed since last indexing.

    Args:
        manifest_path: Path to the manifest JSON file.
        collection_name: Name of the ChromaDB collection being tracked.
    """

    DEFAULT_MANIFEST_DIR = Path("chroma-data/manifests")

    def __init__(self, manifest_path: str | Path | None = None, collection_name: str = "default"):
        self.collection_name = collection_name

        if manifest_path is None:
            self.DEFAULT_MANIFEST_DIR.mkdir(parents=True, exist_ok=True)
            manifest_path = self.DEFAULT_MANIFEST_DIR / f"{collection_name}_manifest.json"

        self.manifest_path = Path(manifest_path)
        self.manifest = self._load_manifest()

    def _load_manifest(self) -> IndexManifest:
        """Load manifest from disk or create new one."""
        if self.manifest_path.exists():
            try:
                with open(self.manifest_path, "r") as f:
                    data = json.load(f)
                logger.info(f"Loaded index manifest with {len(data.get('files', {}))} tracked files")
                return IndexManifest.from_dict(data)
            except Exception as e:
                logger.warning(f"Failed to load manifest, creating new: {e}")

        return IndexManifest(collection_name=self.collection_name)

    def save(self) -> None:
        """Save manifest to disk."""
        self.manifest.updated_at = datetime.now().isoformat()
        self.manifest_path.parent.mkdir(parents=True, exist_ok=True)

        with open(self.manifest_path, "w") as f:
            json.dump(self.manifest.to_dict(), f, indent=2)

        logger.debug(f"Saved index manifest to {self.manifest_path}")

    def is_file_indexed(self, file_path: Path) -> bool:
        """
        Check if a file is already indexed and unchanged.

        Args:
            file_path: Path to check.

        Returns:
            True if file is indexed and unchanged, False otherwise.
        """
        abs_path = str(file_path.absolute())

        if abs_path not in self.manifest.files:
            return False

        info = self.manifest.files[abs_path]

        # Check if file still exists
        if not file_path.exists():
            return False

        # Check if file has been modified (by hash)
        current_hash = compute_file_hash(file_path)
        if current_hash != info.file_hash:
            logger.debug(f"File changed (hash mismatch): {file_path.name}")
            return False

        return True

    def get_files_to_index(self, file_paths: List[Path]) -> List[Path]:
        """
        Filter list to only files that need indexing.

        Args:
            file_paths: List of file paths to check.

        Returns:
            List of files that are new or modified.
        """
        to_index = []
        skipped = 0

        for file_path in file_paths:
            if self.is_file_indexed(file_path):
                skipped += 1
            else:
                to_index.append(file_path)

        if skipped > 0:
            logger.info(f"Skipping {skipped} already indexed files, {len(to_index)} new/modified files to process")

        return to_index

    def mark_indexed(
        self,
        file_path: Path,
        chunk_count: int,
    ) -> None:
        """
        Mark a file as successfully indexed.

        Args:
            file_path: Path to the indexed file.
            chunk_count: Number of chunks created.
        """
        abs_path = str(file_path.absolute())
        stat = file_path.stat()

        self.manifest.files[abs_path] = IndexedFileInfo(
            file_path=abs_path,
            file_hash=compute_file_hash(file_path),
            file_size=stat.st_size,
            modified_time=stat.st_mtime,
            indexed_at=datetime.now().isoformat(),
            chunk_count=chunk_count,
            collection_name=self.collection_name,
        )

    def remove_file(self, file_path: Path) -> bool:
        """
        Remove a file from the manifest.

        Args:
            file_path: Path to remove.

        Returns:
            True if file was in manifest and removed.
        """
        abs_path = str(file_path.absolute())
        if abs_path in self.manifest.files:
            del self.manifest.files[abs_path]
            return True
        return False

    def get_indexed_files(self) -> Set[str]:
        """Get set of all indexed file paths."""
        return set(self.manifest.files.keys())

    def get_stats(self) -> Dict:
        """Get statistics about indexed files."""
        total_chunks = sum(f.chunk_count for f in self.manifest.files.values())
        return {
            "total_files": len(self.manifest.files),
            "total_chunks": total_chunks,
            "collection_name": self.collection_name,
            "last_updated": self.manifest.updated_at,
        }

    def clear(self) -> None:
        """Clear all tracking data."""
        self.manifest = IndexManifest(collection_name=self.collection_name)
        if self.manifest_path.exists():
            self.manifest_path.unlink()
        logger.info("Cleared index manifest")

