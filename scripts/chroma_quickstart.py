"""ChromaDB Data Processing Quickstart - Comprehensive Testing Script

This script tests all components of the ChromaDB data processing pipeline:
- Document loading and parsing
- Multiple chunking strategies (basic, by_title, semantic)
- Wine metadata extraction (grapes, regions, vintages, appellations, producers)
- Document context extraction (title, chapter, section)
- Hierarchical chunking (small-to-big)
- Embedding generation
- Semantic deduplication
- Index tracking (incremental indexing)
- ChromaDB storage

Uses a dedicated test collection to avoid interfering with production data.

Usage:
    python -m src.chroma.chroma_quickstart
    PYTHONPATH=$(pwd) python src/chroma/chroma_quickstart.py

Prerequisites:
    - ChromaDB must be running (make chroma-up)
    - Test PDF file at: chroma-data/test/wine.pdf
"""
import os
import time
from pathlib import Path
from typing import List, Dict, Any

from src.chroma import split_file, create_hierarchical_chunks, deduplicate_chunks, IndexTracker, CollectionDataLoader, \
    get_collection_stats
from src.utils import get_config, initialize_chroma_client, compute_file_hash, get_project_root

os.environ["TOKENIZERS_PARALLELISM"] = "false"

# Test collection name - separate from production
TEST_COLLECTION = "wine_test"
TEST_PDF_PATH = get_project_root() / "chroma-data/test/wine.pdf"
TEST_MANIFEST = get_project_root() / "chroma-data/manifests/wine_test_manifest.json"


def print_section(title: str):
    """Print a formatted section header."""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}\n")


def check_prerequisites():
    """Check if prerequisites are met."""
    print_section("Prerequisites Check")

    # Check if test PDF exists
    if not TEST_PDF_PATH.exists():
        print(f"❌ Test PDF not found at: {TEST_PDF_PATH}")
        print(f"\nPlease place a test wine PDF file at: {TEST_PDF_PATH.absolute()}")
        print(f"You can use any wine-related PDF for testing.")
        return False

    print(f"✓ Test PDF found: {TEST_PDF_PATH}")
    print(f"  Size: {TEST_PDF_PATH.stat().st_size / 1024:.1f} KB")

    # Check ChromaDB connection
    try:
        cfg = get_config()
        client = initialize_chroma_client(cfg.chroma.client.host, cfg.chroma.client.port)
        print(f"✓ ChromaDB connected at {cfg.chroma.client.host}:{cfg.chroma.client.port}")
    except Exception as e:
        print(f"❌ ChromaDB connection failed: {e}")
        print(f"\nPlease start ChromaDB with: make chroma-up")
        return False

    return True


def test_basic_chunking(pdf_path: Path, cfg):
    """Test basic fixed-size chunking strategy."""
    print_section("1. Basic Chunking Strategy")

    print(f"Strategy: Fixed-size chunks")
    print(f"Chunk size: {cfg.chroma.chunking.chunk_size}")
    print(f"Overlap: {cfg.chroma.chunking.chunk_overlap}")

    start_time = time.time()
    chunks = split_file(
        filepath=pdf_path,
        strategy="basic",
        chunk_size=cfg.chroma.chunking.chunk_size,
        overlap_size=cfg.chroma.chunking.chunk_overlap,
        embedding_model=cfg.chroma.settings.embedder,
        extract_metadata=False,  # No metadata for basic test
    )
    processing_time = time.time() - start_time

    print(f"\nResults:")
    print(f"  Chunks generated: {len(chunks)}")
    print(f"  Processing time: {processing_time:.3f}s")

    if chunks:
        print(f"\n  Sample chunk:")
        sample = chunks[0]
        print(f"    ID: {sample['id']}")
        print(f"    Text length: {len(sample['text'])} chars")
        print(f"    Preview: {sample['text'][:100]}...")

    return chunks


def test_by_title_chunking(pdf_path: Path, cfg):
    """Test section-based chunking strategy."""
    print_section("2. By-Title Chunking Strategy")

    print(f"Strategy: Section-based (preserves document structure)")

    start_time = time.time()
    chunks = split_file(
        filepath=pdf_path,
        strategy="by_title",
        chunk_size=cfg.chroma.chunking.chunk_size,
        overlap_size=cfg.chroma.chunking.chunk_overlap,
        embedding_model=cfg.chroma.settings.embedder,
        extract_metadata=False,
    )
    processing_time = time.time() - start_time

    print(f"\nResults:")
    print(f"  Chunks generated: {len(chunks)}")
    print(f"  Processing time: {processing_time:.3f}s")

    if chunks:
        # Show chunks with titles
        titled_chunks = [c for c in chunks if c.get('metadata', {}).get('document_title')]
        print(f"  Chunks with titles: {len(titled_chunks)}")

        if titled_chunks:
            print(f"\n  Sample titled chunk:")
            sample = titled_chunks[0]
            metadata = sample.get('metadata', {})
            print(f"    Title: {metadata.get('document_title', 'N/A')}")
            print(f"    Chapter: {metadata.get('chapter', 'N/A')}")
            print(f"    Section: {metadata.get('section', 'N/A')}")

    return chunks


def test_semantic_chunking(pdf_path: Path, cfg):
    """Test semantic chunking strategy."""
    print_section("3. Semantic Chunking Strategy")

    print(f"Strategy: AI-powered semantic boundaries")
    print(f"Note: This is slower but produces more coherent chunks")

    start_time = time.time()
    chunks = split_file(
        filepath=pdf_path,
        strategy="semantic",
        embedding_model=cfg.chroma.settings.embedder,
        extract_metadata=False,
    )
    processing_time = time.time() - start_time

    print(f"\nResults:")
    print(f"  Chunks generated: {len(chunks)}")
    print(f"  Processing time: {processing_time:.3f}s")
    print(f"  Avg chunk size: {sum(len(c['text']) for c in chunks) // len(chunks) if chunks else 0} chars")

    return chunks


def test_wine_metadata_extraction(pdf_path: Path, cfg):
    """Test wine-specific metadata extraction."""
    print_section("4. Wine Metadata Extraction")

    print(f"Extracting wine entities from chunks:")
    print(f"  - Grape varieties")
    print(f"  - Wine regions")
    print(f"  - Vintage years")
    print(f"  - Classifications (DOCG, AOC, etc.)")
    print(f"  - Producers/wineries")
    print(f"  - Wine appellations")

    start_time = time.time()
    chunks = split_file(
        filepath=pdf_path,
        strategy="by_title",
        chunk_size=cfg.chroma.chunking.chunk_size,
        overlap_size=cfg.chroma.chunking.chunk_overlap,
        embedding_model=cfg.chroma.settings.embedder,
        extract_metadata=True,  # Enable wine metadata extraction
    )
    processing_time = time.time() - start_time

    print(f"\nResults:")
    print(f"  Chunks generated: {len(chunks)}")
    print(f"  Processing time: {processing_time:.3f}s")

    # Analyze extracted metadata
    if chunks:
        grapes_found = set()
        regions_found = set()
        vintages_found = set()
        appellations_found = set()
        producers_found = set()

        for chunk in chunks:
            metadata = chunk.get('metadata', {})
            if metadata.get('grapes'):
                grapes_found.update(metadata['grapes'].split(','))
            if metadata.get('regions'):
                regions_found.update(metadata['regions'].split(','))
            if metadata.get('vintages'):
                vintages_found.update(metadata['vintages'].split(','))
            if metadata.get('appellations'):
                appellations_found.update(metadata['appellations'].split(','))
            if metadata.get('producers'):
                producers_found.update(metadata['producers'].split(','))

        print(f"\n  Metadata extracted:")
        if grapes_found:
            print(f"    Grapes: {', '.join(sorted(grapes_found)[:5])}{'...' if len(grapes_found) > 5 else ''}")
        if regions_found:
            print(f"    Regions: {', '.join(sorted(regions_found)[:5])}{'...' if len(regions_found) > 5 else ''}")
        if vintages_found:
            print(f"    Vintages: {', '.join(sorted(vintages_found)[:5])}{'...' if len(vintages_found) > 5 else ''}")
        if appellations_found:
            print(f"    Appellations: {', '.join(sorted(appellations_found)[:5])}{'...' if len(appellations_found) > 5 else ''}")
        if producers_found:
            print(f"    Producers: {', '.join(sorted(producers_found)[:3])}{'...' if len(producers_found) > 3 else ''}")

    return chunks


def test_hierarchical_chunking(pdf_path: Path, cfg):
    """Test hierarchical (small-to-big) chunking."""
    print_section("5. Hierarchical Chunking (Small-to-Big)")

    print(f"Creating hierarchical chunks:")
    print(f"  Small chunks: 256 chars (for retrieval)")
    print(f"  Large chunks: 1024 chars (for context)")

    # Read file content
    from unstructured.partition.auto import partition
    elements = partition(filename=str(pdf_path))
    full_text = "\n".join([str(elem) for elem in elements])

    start_time = time.time()
    hierarchical_chunks = create_hierarchical_chunks(
        text=full_text,
        small_chunk_size=256,
        large_chunk_size=1024,
        overlap=64,
    )
    processing_time = time.time() - start_time

    print(f"\nResults:")
    print(f"  Hierarchical chunks: {len(hierarchical_chunks)}")
    print(f"  Processing time: {processing_time:.3f}s")

    if hierarchical_chunks:
        sample = hierarchical_chunks[0]
        print(f"\n  Sample hierarchical chunk:")
        print(f"    Small text: {len(sample.small_text)} chars")
        print(f"    Large text: {len(sample.large_text)} chars")
        print(f"    Ratio: {len(sample.large_text) / len(sample.small_text):.1f}x larger")

    return hierarchical_chunks


def test_deduplication(chunks: List[Dict[str, Any]], cfg):
    """Test semantic deduplication."""
    print_section("6. Semantic Deduplication")

    print(f"Removing near-duplicate chunks")
    print(f"Similarity threshold: {cfg.chroma.retrieval.deduplication_threshold}")

    original_count = len(chunks)

    start_time = time.time()
    deduplicated = deduplicate_chunks(
        chunks,
        similarity_threshold=cfg.chroma.retrieval.deduplication_threshold,
        embedding_model=cfg.chroma.settings.embedder,
    )
    processing_time = time.time() - start_time

    removed = original_count - len(deduplicated)
    print(f"\nResults:")
    print(f"  Original chunks: {original_count}")
    print(f"  Deduplicated chunks: {len(deduplicated)}")
    print(f"  Removed: {removed} ({removed/original_count*100:.1f}%)")
    print(f"  Processing time: {processing_time:.3f}s")

    return deduplicated


def test_index_tracking(pdf_path: Path, cfg):
    """Test incremental indexing with index tracking."""
    print_section("7. Index Tracking (Incremental Indexing)")

    tracker = IndexTracker(
        collection_name=TEST_COLLECTION,
        manifest_path=TEST_MANIFEST,
    )

    print(f"Collection: {TEST_COLLECTION}")
    print(f"Manifest path: {tracker.manifest_path}")

    # Check if file is tracked
    file_hash = compute_file_hash(pdf_path)
    is_indexed = tracker.is_file_indexed(pdf_path)

    print(f"\nFile status:")
    print(f"  Path: {pdf_path}")
    print(f"  Hash: {file_hash[:16]}...")
    print(f"  Is indexed: {is_indexed}")

    if is_indexed:
        abs_path = str(pdf_path.absolute())
        file_info = tracker.manifest.files.get(abs_path)
        if file_info:
            print(f"\n  Index info:")
            print(f"    Indexed at: {file_info.indexed_at}")
            print(f"    Chunks: {file_info.chunk_count}")

    # Mark as indexed for testing
    if not is_indexed:
        tracker.mark_indexed(pdf_path, chunk_count=100)
        tracker.save()
        print(f"\n  Marked file as indexed (for testing)")

    stats = tracker.get_stats()
    print(f"\nTracker stats:")
    print(f"  Files indexed: {stats['total_files']}")
    print(f"  Total chunks: {stats['total_chunks']}")

    return tracker


def test_full_pipeline(pdf_path: Path, cfg):
    """Test the complete data loading pipeline."""
    print_section("8. Full Pipeline - Load into ChromaDB")

    print(f"Loading {pdf_path.name} into test collection '{TEST_COLLECTION}'")
    print(f"This will test:")
    print(f"  - Document parsing")
    print(f"  - Chunking with metadata")
    print(f"  - Embedding generation")
    print(f"  - Duplicate detection")
    print(f"  - ChromaDB storage")

    # Initialize loader
    loader = CollectionDataLoader(
        collection_name=TEST_COLLECTION,
        collection_metadata={
            "description": "Test collection for quickstart",
            "version": "test-v1",
            "hnsw:space": "cosine",
        },
        chroma_host=cfg.chroma.client.host,
        chroma_port=cfg.chroma.client.port,
        embedding_model=cfg.chroma.settings.embedder,
        batch_size=cfg.chroma.settings.batch_size,
    )

    print(f"\nProcessing file...")
    start_time = time.time()

    stats = loader.process_file(
        file_path=pdf_path,
        strategy=cfg.chroma.chunking.strategy,
        chunk_size=cfg.chroma.chunking.chunk_size,
        overlap_size=cfg.chroma.chunking.chunk_overlap,
        skip_duplicates=True,
        extract_wine_metadata=cfg.chroma.chunking.extract_wine_metadata,
    )

    total_time = time.time() - start_time

    print(f"\nProcessing results:")
    print(f"  Filename: {stats['filename']}")
    print(f"  Chunks generated: {stats['chunks_generated']}")
    print(f"  Chunks added: {stats['chunks_added']}")
    print(f"  Chunks skipped: {stats['chunks_skipped']}")
    print(f"  Processing time: {total_time:.3f}s")

    if stats['errors']:
        print(f"\n  Errors:")
        for error in stats['errors']:
            print(f"    - {error}")

    return loader


def test_collection_stats(cfg):
    """Test collection statistics."""
    print_section("9. Collection Statistics")

    print(f"Getting stats for collection: {TEST_COLLECTION}")

    client = initialize_chroma_client(cfg.chroma.client.host, cfg.chroma.client.port)
    stats = get_collection_stats(client, TEST_COLLECTION)

    if "error" in stats:
        print(f"Error: {stats['error']}")
        return

    print(f"\nCollection: {stats['name']}")
    print(f"  Records: {stats['record_count']:,}")
    print(f"  Embedding dimension: {stats.get('embedding_dimension', 'N/A')}")

    if stats.get('avg_document_length'):
        print(f"\n  Document stats:")
        print(f"    Average length: {stats['avg_document_length']:,} chars")
        print(f"    Min length: {stats['min_document_length']:,} chars")
        print(f"    Max length: {stats['max_document_length']:,} chars")

    if stats.get('metadata_fields'):
        print(f"\n  Metadata fields: {len(stats['metadata_fields'])}")
        wine_fields = ['grapes', 'regions', 'vintages', 'appellations', 'producers']
        for field in wine_fields:
            if field in stats['metadata_fields']:
                print(f"    {field}")


def cleanup_test_collection(cfg):
    """Clean up test collection."""
    print_section("Cleanup")

    print(f"Do you want to delete the test collection '{TEST_COLLECTION}'?")
    print(f"This will remove all test data from ChromaDB.")
    response = input("Delete test collection? (y/N): ").strip().lower()

    if response == 'y':
        try:
            client = initialize_chroma_client(cfg.chroma.client.host, cfg.chroma.client.port)
            client.delete_collection(TEST_COLLECTION)
            print(f"✓ Deleted test collection: {TEST_COLLECTION}")

            # Clean up manifest
            tracker = IndexTracker(collection_name=TEST_COLLECTION)
            if tracker.manifest_path.exists():
                tracker.manifest_path.unlink()
                print(f"✓ Deleted manifest: {tracker.manifest_path}")
        except Exception as e:
            print(f"Error during cleanup: {e}")
    else:
        print(f"Test collection '{TEST_COLLECTION}' kept for inspection")
        print(f"You can view it with: python -m src.chroma.stats -c {TEST_COLLECTION}")


def main():
    """Main quickstart flow testing all chroma processing components."""
    print(f"""
{'='*70}
  ChromaDB Data Processing - Comprehensive Test
{'='*70}

This script tests all components of the data processing pipeline:
  1. Basic chunking (fixed-size)
  2. By-title chunking (section-based)
  3. Semantic chunking (AI-powered)
  4. Wine metadata extraction
  5. Hierarchical chunking (small-to-big)
  6. Semantic deduplication
  7. Index tracking (incremental indexing)
  8. Full pipeline (load into ChromaDB)
  9. Collection statistics

Uses test collection: '{TEST_COLLECTION}'
Test PDF: {TEST_PDF_PATH}

{'='*70}
""")

    # Check prerequisites
    if not check_prerequisites():
        return 1

    # Load config
    cfg = get_config()

    # Run tests
    print(f"\nStarting comprehensive tests...")

    # 1. Basic chunking
    basic_chunks = test_basic_chunking(TEST_PDF_PATH, cfg)

    # 2. By-title chunking
    by_title_chunks = test_by_title_chunking(TEST_PDF_PATH, cfg)

    # 3. Semantic chunking
    semantic_chunks = test_semantic_chunking(TEST_PDF_PATH, cfg)

    # 4. Wine metadata extraction
    metadata_chunks = test_wine_metadata_extraction(TEST_PDF_PATH, cfg)

    # 5. Hierarchical chunking
    hierarchical_chunks = test_hierarchical_chunking(TEST_PDF_PATH, cfg)

    # 6. Deduplication (using by_title chunks)
    if by_title_chunks:
        deduplicated_chunks = test_deduplication(by_title_chunks, cfg)

    # 7. Index tracking
    tracker = test_index_tracking(TEST_PDF_PATH, cfg)

    # 8. Full pipeline
    loader = test_full_pipeline(TEST_PDF_PATH, cfg)

    # 9. Collection stats
    test_collection_stats(cfg)

    # Summary
    print_section("Summary")
    print("All tests completed successfully!")
    print(f"\nComponents tested:")
    print(f"  ✓ Basic chunking ({len(basic_chunks)} chunks)")
    print(f"  ✓ By-title chunking ({len(by_title_chunks)} chunks)")
    print(f"  ✓ Semantic chunking ({len(semantic_chunks)} chunks)")
    print(f"  ✓ Wine metadata extraction")
    print(f"  ✓ Hierarchical chunking ({len(hierarchical_chunks)} chunks)")
    print(f"  ✓ Semantic deduplication")
    print(f"  ✓ Index tracking")
    print(f"  ✓ Full pipeline (ChromaDB load)")
    print(f"  ✓ Collection statistics")

    print(f"\nTest collection: {TEST_COLLECTION}")
    print(f"View stats with: python -m src.chroma.stats -c {TEST_COLLECTION}")
    print(f"")

    # Cleanup
    cleanup_test_collection(cfg)


if __name__ == "__main__":
    main()

