"""CLI tool for importing Vivino data."""
import sys
from pathlib import Path

from src.etl.vivino_importer import VivinoImporter
from src.utils import get_project_root
from src.utils.logger import logger


def main():
    """Import Vivino CSV data into wine cellar database."""

    cellar_csv = get_project_root() / "data/vivino/cellar.csv"
    full_wine_list_csv = get_project_root() / "data/vivino/full_wine_list.csv"

    if not (Path(cellar_csv).exists() and Path(full_wine_list_csv).exists()):
        logger.error(f"Vivino csv files not found: {cellar_csv}, {full_wine_list_csv}")
        sys.exit(1)

    importer = VivinoImporter()
    # cellar_stats = importer.import_cellar_csv(cellar_csv)
    # importer.reset_stats()
    full_stats = importer.import_full_wine_list_csv(full_wine_list_csv)

    print("\n" + "=" * 60)
    print("IMPORT SUMMARY")
    print("=" * 60)

    # print("\nCellar.csv:")
    # print(f"  Wines processed: {cellar_stats['wines_processed']}")
    # print(f"  Wines imported: {cellar_stats['wines_imported']}")
    # print(f"  Wines updated: {cellar_stats['wines_updated']}")
    # print(f"  Wines skipped: {cellar_stats['wines_skipped']}")
    # print(f"  Bottles imported: {cellar_stats['bottles_imported']}")
    # print(f"  Producers created: {cellar_stats['producers_created']}")
    # print(f"  Regions created: {cellar_stats['regions_created']}")
    # print(f"  Errors: {len(cellar_stats['errors'])}")

    print("\nFull_wine_list.csv:")
    print(f"  Wines processed: {full_stats['wines_processed']}")
    print(f"  Wines imported: {full_stats['wines_imported']}")
    print(f"  Wines updated: {full_stats['wines_updated']}")
    print(f"  Wines skipped: {full_stats['wines_skipped']}")
    print(f"  Bottles imported: {full_stats['bottles_imported']}")
    print(f"  Producers created: {full_stats['producers_created']}")
    print(f"  Regions created: {full_stats['regions_created']}")
    print(f"  Errors: {len(full_stats['errors'])}")
    print("\n✅ Import completed!")
    print("=" * 60)


if __name__ == '__main__':
    main()

