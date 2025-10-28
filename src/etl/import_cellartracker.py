"""CLI script to import data from CellarTracker."""
import argparse
import sys
import os
from pathlib import Path

from src.etl.cellartracker_importer import CellarTrackerImporter
from src.database.db import initialize_database
from src.utils.logger import logger
from src.utils.env import load_env


def main():
    """Main entry point for CellarTracker import."""
    parser = argparse.ArgumentParser(
        description='Import wine data from CellarTracker API'
    )

    parser.add_argument(
        '--username',
        help='CellarTracker username (or set CELLAR_TRACKER_USERNAME env var)'
    )

    parser.add_argument(
        '--password',
        help='CellarTracker password (or set CELLAR_TRACKER_PASSWORD env var)'
    )

    parser.add_argument(
        '--db-path',
        default='data/wine_cellar.db',
        help='Path to SQLite database (default: data/wine_cellar.db)'
    )

    parser.add_argument(
        '--init-db',
        action='store_true',
        help='Initialize database schema before import'
    )

    parser.add_argument(
        '--inventory-only',
        action='store_true',
        help='Import only current inventory (skip consumed, notes, etc.)'
    )

    args = parser.parse_args()

    # Load environment variables from .env file
    from dotenv import load_dotenv
    load_dotenv()

    # Get credentials
    username = args.username or os.getenv('CELLAR_TRACKER_USERNAME')
    password = args.password or os.getenv('CELLAR_TRACKER_PASSWORD')

    if not username or not password:
        logger.error("CellarTracker credentials required!")
        logger.error("Provide via --username/--password or set CELLAR_TRACKER_USERNAME/CELLAR_TRACKER_PASSWORD env vars")
        sys.exit(1)

    # Initialize database if requested
    if args.init_db:
        logger.info("Initializing database schema...")
        if not initialize_database(args.db_path):
            logger.error("Failed to initialize database")
            sys.exit(1)

    # Create importer
    try:
        logger.info("Connecting to CellarTracker API...")
        importer = CellarTrackerImporter(username, password, args.db_path)

        # Run import
        if args.inventory_only:
            logger.info("Starting inventory-only import...")
            stats = importer.import_inventory_only()
        else:
            logger.info("Starting full import...")
            stats = importer.import_all()

        # Print summary
        print("\n" + "="*60)
        print("IMPORT SUMMARY")
        print("="*60)
        print(f"Wines processed:      {stats['wines_processed']}")
        print(f"  - Imported:         {stats['wines_imported']}")
        print(f"  - Updated:          {stats['wines_updated']}")
        print(f"  - Skipped:          {stats['wines_skipped']}")
        print(f"\nBottles processed:    {stats['bottles_processed']}")
        print(f"  - Imported:         {stats['bottles_imported']}")
        print(f"  - Updated:          {stats['bottles_updated']}")
        print(f"\nProducers created:    {stats['producers_created']}")
        print(f"Regions created:      {stats['regions_created']}")
        print(f"Notes processed:      {stats['notes_processed']}")
        print(f"\nErrors:               {len(stats['errors'])}")

        if stats['errors']:
            print("\nErrors encountered:")
            for error in stats['errors'][:10]:  # Show first 10 errors
                print(f"  - {error}")
            if len(stats['errors']) > 10:
                print(f"  ... and {len(stats['errors']) - 10} more")

        print("="*60)

        # Exit with error code if there were errors
        if stats['errors']:
            sys.exit(1)

    except Exception as e:
        logger.error(f"Import failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
"""CLI script to import data from CellarTracker."""
import argparse
import sys
import os

from src.etl.cellartracker_importer import CellarTrackerImporter
from src.database.db import initialize_database
from src.utils.logger import logger


def main():
    """Main entry point for CellarTracker import."""
    parser = argparse.ArgumentParser(
        description='Import wine data from CellarTracker API'
    )

    parser.add_argument(
        '--username',
        help='CellarTracker username (or set CELLAR_TRACKER_USERNAME env var)'
    )

    parser.add_argument(
        '--password',
        help='CellarTracker password (or set CELLAR_TRACKER_PASSWORD env var)'
    )

    parser.add_argument(
        '--db-path',
        default='data/wine_cellar.db',
        help='Path to SQLite database (default: data/wine_cellar.db)'
    )

    parser.add_argument(
        '--init-db',
        action='store_true',
        help='Initialize database schema before import'
    )

    parser.add_argument(
        '--inventory-only',
        action='store_true',
        help='Import only current inventory (skip consumed, notes, etc.)'
    )

    args = parser.parse_args()

    # Load environment variables
    import os
    load_env()

    # Get credentials
    username = args.username or os.getenv('CELLAR_TRACKER_USERNAME')
    password = args.password or os.getenv('CELLAR_TRACKER_PASSWORD')

    if not username or not password:
        logger.error("CellarTracker credentials required!")
        logger.error("Provide via --username/--password or set CELLAR_TRACKER_USERNAME/CELLARTRACKER_PASSWORD env vars")
        sys.exit(1)

    # Initialize database if requested
    if args.init_db:
        logger.info("Initializing database schema...")
        if not initialize_database(args.db_path):
            logger.error("Failed to initialize database")
            sys.exit(1)

    # Create importer
    try:
        logger.info("Connecting to CellarTracker API...")
        importer = CellarTrackerImporter(username, password, args.db_path)

        # Run import
        if args.inventory_only:
            logger.info("Starting inventory-only import...")
            stats = importer.import_inventory_only()
        else:
            logger.info("Starting full import...")
            stats = importer.import_all()

        # Print summary
        print("\n" + "="*60)
        print("IMPORT SUMMARY")
        print("="*60)
        print(f"Wines processed:      {stats['wines_processed']}")
        print(f"  - Imported:         {stats['wines_imported']}")
        print(f"  - Updated:          {stats['wines_updated']}")
        print(f"  - Skipped:          {stats['wines_skipped']}")
        print(f"\nBottles processed:    {stats['bottles_processed']}")
        print(f"  - Imported:         {stats['bottles_imported']}")
        print(f"  - Updated:          {stats['bottles_updated']}")
        print(f"\nProducers created:    {stats['producers_created']}")
        print(f"Regions created:      {stats['regions_created']}")
        print(f"Notes processed:      {stats['notes_processed']}")
        print(f"\nErrors:               {len(stats['errors'])}")

        if stats['errors']:
            print("\nErrors encountered:")
            for error in stats['errors'][:10]:  # Show first 10 errors
                print(f"  - {error}")
            if len(stats['errors']) > 10:
                print(f"  ... and {len(stats['errors']) - 10} more")

        print("="*60)

        # Exit with error code if there were errors
        if stats['errors']:
            sys.exit(1)

    except Exception as e:
        logger.error(f"Import failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()

