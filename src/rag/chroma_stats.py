"""ChromaDB statistics and diagnostics script.

Displays detailed statistics about ChromaDB collections including:
- Number of records per collection
- Embedding dimensions
- Metadata field distribution
- Storage information
"""
import argparse
from collections import Counter
from typing import Dict, Any, List

from src.utils import get_config, logger, initialize_chroma_client


def get_collection_stats(client, collection_name: str) -> Dict[str, Any]:
    """
    Get detailed statistics for a ChromaDB collection.

    Args:
        client: ChromaDB client instance.
        collection_name: Name of the collection to analyze.

    Returns:
        Dictionary with collection statistics.
    """
    try:
        collection = client.get_collection(collection_name)
    except Exception as e:
        return {"error": str(e), "name": collection_name}

    # Get collection count
    count = collection.count()

    stats = {
        "name": collection_name,
        "record_count": count,
        "metadata": dict(collection.metadata) if collection.metadata else {},
    }

    if count == 0:
        stats["embedding_dimension"] = "N/A (empty collection)"
        return stats

    # Sample records to get embedding dimension and metadata stats
    sample_size = min(100, count)
    sample = collection.get(
        limit=sample_size,
        include=["embeddings", "metadatas", "documents"]
    )

    # Embedding dimension
    if sample["embeddings"] is not None and len(sample["embeddings"]) > 0:
        stats["embedding_dimension"] = len(sample["embeddings"][0])
    else:
        stats["embedding_dimension"] = "N/A"

    # Document length stats
    if sample["documents"]:
        doc_lengths = [len(doc) for doc in sample["documents"] if doc]
        if doc_lengths:
            stats["avg_document_length"] = sum(doc_lengths) // len(doc_lengths)
            stats["min_document_length"] = min(doc_lengths)
            stats["max_document_length"] = max(doc_lengths)

    # Metadata field analysis
    if sample["metadatas"]:
        metadata_fields = Counter()
        field_values = {}

        for meta in sample["metadatas"]:
            if meta:
                for key, value in meta.items():
                    metadata_fields[key] += 1
                    if key not in field_values:
                        field_values[key] = Counter()
                    # Only count non-empty values
                    if value and str(value).strip():
                        field_values[key][str(value)[:50]] += 1

        stats["metadata_fields"] = dict(metadata_fields)

        # Get top values for categorical fields
        categorical_summary = {}
        for field, values in field_values.items():
            if len(values) <= 20:  # Only show if reasonable number of unique values
                categorical_summary[field] = dict(values.most_common(5))
        stats["metadata_sample_values"] = categorical_summary

    return stats


def get_all_stats(client) -> List[Dict[str, Any]]:
    """Get statistics for all collections in ChromaDB."""
    collections = client.list_collections()
    return [get_collection_stats(client, col.name) for col in collections]


def print_stats(stats: Dict[str, Any]) -> None:
    """Print formatted statistics for a collection."""
    print(f"\n{'='*60}")
    print(f"Collection: {stats['name']}")
    print(f"{'='*60}")

    if "error" in stats:
        print(f"  Error: {stats['error']}")
        return

    print(f"  Records: {stats['record_count']:,}")
    print(f"  Embedding Dimension: {stats.get('embedding_dimension', 'N/A')}")

    if "avg_document_length" in stats:
        print(f"\n  Document Length (chars):")
        print(f"    Average: {stats['avg_document_length']:,}")
        print(f"    Min: {stats['min_document_length']:,}")
        print(f"    Max: {stats['max_document_length']:,}")

    if stats.get("metadata"):
        print(f"\n  Collection Metadata:")
        for key, value in stats["metadata"].items():
            print(f"    {key}: {value}")

    if stats.get("metadata_fields"):
        print(f"\n  Metadata Fields (from sample):")
        for field, count in sorted(stats["metadata_fields"].items()):
            print(f"    {field}: {count} records")

    # Show wine-specific metadata if present
    wine_fields = ["grapes", "regions", "vintages", "appellations", "producers"]
    sample_values = stats.get("metadata_sample_values", {})

    wine_metadata_present = any(f in sample_values for f in wine_fields)
    if wine_metadata_present:
        print(f"\n  Wine Metadata Samples:")
        for field in wine_fields:
            if field in sample_values and sample_values[field]:
                values = list(sample_values[field].keys())[:3]
                if values:
                    print(f"    {field}: {', '.join(values)}")


def main():
    parser = argparse.ArgumentParser(description="Display ChromaDB statistics")
    parser.add_argument(
        "--collection", "-c",
        type=str,
        help="Specific collection name (default: all collections)"
    )
    parser.add_argument(
        "--json", "-j",
        action="store_true",
        help="Output as JSON"
    )
    args = parser.parse_args()

    cfg = get_config()
    chroma_cfg = cfg.chroma

    try:
        client = initialize_chroma_client(chroma_cfg.client.host, chroma_cfg.client.port)
    except Exception as e:
        print(f"Error connecting to ChromaDB: {e}")
        print(f"Make sure ChromaDB is running on {chroma_cfg.client.host}:{chroma_cfg.client.port}")
        return 1

    # Get stats
    if args.collection:
        all_stats = [get_collection_stats(client, args.collection)]
    else:
        all_stats = get_all_stats(client)

    if not all_stats:
        print("No collections found in ChromaDB")
        return 0

    # Output
    if args.json:
        import json
        print(json.dumps(all_stats, indent=2, default=str))
    else:
        print("\n" + "="*60)
        print("ChromaDB Statistics")
        print(f"Server: {chroma_cfg.client.host}:{chroma_cfg.client.port}")
        print(f"Total Collections: {len(all_stats)}")

        total_records = sum(s.get("record_count", 0) for s in all_stats if "error" not in s)
        print(f"Total Records: {total_records:,}")

        for stats in all_stats:
            print_stats(stats)

        print("\n" + "="*60)

    return 0


if __name__ == "__main__":
    exit(main())

