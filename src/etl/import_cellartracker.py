"""CLI script to import data from CellarTracker."""
import argparse
import sys
import os
import traceback
from dotenv import load_dotenv

from src.etl.cellartracker_importer import CellarTrackerImporter
from src.database.db import initialize_database
from src.utils import find_project_root
from src.utils.logger import logger


def main():
    """Main entry point for CellarTracker import."""
    parser = argparse.ArgumentParser(description='Import wine data from CellarTracker API')

    parser.add_argument(
        '-u', '--username', type=str, required=False,
        help='CellarTracker username (or set CELLAR_TRACKER_USERNAME env var)'
    )

    parser.add_argument(
        '-p', '--password', type=str, required=False,
        help='CellarTracker password (or set CELLAR_TRACKER_PASSWORD env var)'
    )

    parser.add_argument(
        '--db-path', type=str, required=False,
        default='data/wine_cellar.db',
        help='Path to SQLite database (default: data/wine_cellar.db)'
    )

    parser.add_argument(
        '--init-db',
        action='store_true',
        help='Initialize database schema before import'
    )

    args = parser.parse_args()
    args.db_path = f"{find_project_root()}/{args.db_path}"
    load_dotenv()

    username = args.username or os.getenv('CELLAR_TRACKER_USERNAME')
    password = args.password or os.getenv('CELLAR_TRACKER_PASSWORD')

    if not username or not password:
        logger.error("CellarTracker credentials required!")
        sys.exit(1)

    # Initialize database if requested
    if args.init_db:
        logger.info("Initializing database schema...")
        success =  initialize_database(args.db_path)
        if not success:
            logger.error("Failed to initialize database")
            sys.exit(1)

    try:
        logger.info("Connecting to CellarTracker API...")
        importer = CellarTrackerImporter(username, password, args.db_path)

        logger.info("Starting full import from CellarTracker...")
        stats = importer.import_all()

        # Print summary
        print("\n" + "="*60)
        print("IMPORT SUMMARY")
        print("="*60)
        print(f"Wines processed:      {stats['wines_processed']}")
        print(f"  - Imported:         {stats['wines_imported']}")
        print(f"  - Updated:          {stats['wines_updated']}")
        print(f"  - Skipped:          {stats.get('wines_skipped', 0)}")
        print(f"\nBottles processed:    {stats['bottles_processed']}")
        print(f"  - Imported:         {stats['bottles_imported']}")
        print(f"  - Updated:          {stats['bottles_updated']}")
        print(f"  - Skipped:          {stats.get('bottles_skipped', 0)}")
        print(f"\nProducers created:    {stats['producers_created']}")
        print(f"Regions created:      {stats['regions_created']}")
        print(f"Notes processed:      {stats['notes_processed']}")
        print(f"\nErrors:               {len(stats['errors'])}")
        print("="*60)

        # Exit with error code if there were errors
        if stats['errors']:
            sys.exit(1)

    except Exception as e:
        logger.error(f"Import failed: {e}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()

