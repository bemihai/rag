"""CLI tool for importing Vivino data."""
import sys
from pathlib import Path

from src.etl.vivino_importer import VivinoImporter
from src.utils.logger import logger


def main():
    """Import Vivino CSV data into wine cellar database."""

    # Paths to Vivino CSV files
    cellar_csv = 'data/vivino/cellar.csv'
    full_wine_list_csv = 'data/vivino/full_wine_list.csv'

    # Check if files exist
    if not Path(cellar_csv).exists():
        logger.error(f"Cellar CSV not found: {cellar_csv}")
        sys.exit(1)

    if not Path(full_wine_list_csv).exists():
        logger.error(f"Full wine list CSV not found: {full_wine_list_csv}")
        sys.exit(1)

    # Create importer
    importer = VivinoImporter()

    # Import cellar.csv
    logger.info("=" * 60)
    logger.info("Importing from cellar.csv...")
    logger.info("=" * 60)
    cellar_stats = importer.import_cellar_csv(cellar_csv)

    # Reset stats for next import
    importer.reset_stats()

    # Import full_wine_list.csv
    logger.info("")
    logger.info("=" * 60)
    logger.info("Importing from full_wine_list.csv...")
    logger.info("=" * 60)
    full_stats = importer.import_full_wine_list_csv(full_wine_list_csv)

    # Print summary
    print("\n" + "=" * 60)
    print("IMPORT SUMMARY")
    print("=" * 60)

    print("\nCellar.csv:")
    print(f"  Wines processed: {cellar_stats['wines_processed']}")
    print(f"  Wines imported: {cellar_stats['wines_imported']}")
    print(f"  Wines updated: {cellar_stats['wines_updated']}")
    print(f"  Wines skipped: {cellar_stats['wines_skipped']}")
    print(f"  Bottles imported: {cellar_stats['bottles_imported']}")
    print(f"  Producers created: {cellar_stats['producers_created']}")
    print(f"  Regions created: {cellar_stats['regions_created']}")
    print(f"  Errors: {len(cellar_stats['errors'])}")

    print("\nFull_wine_list.csv:")
    print(f"  Wines processed: {full_stats['wines_processed']}")
    print(f"  Wines imported: {full_stats['wines_imported']}")
    print(f"  Wines updated: {full_stats['wines_updated']}")
    print(f"  Wines skipped: {full_stats['wines_skipped']}")
    print(f"  Bottles imported: {full_stats['bottles_imported']}")
    print(f"  Producers created: {full_stats['producers_created']}")
    print(f"  Regions created: {full_stats['regions_created']}")
    print(f"  Errors: {len(full_stats['errors'])}")

    # Print errors if any
    all_errors = cellar_stats['errors'] + full_stats['errors']
    if all_errors:
        print("\n⚠️  ERRORS:")
        for error in all_errors[:10]:  # Show first 10 errors
            print(f"  - {error}")
        if len(all_errors) > 10:
            print(f"  ... and {len(all_errors) - 10} more errors")

    print("\n✅ Import completed!")
    print("=" * 60)


if __name__ == '__main__':
    main()

