"""Test CellarTracker importer with sample JSON data."""
import json
from pathlib import Path

from src.etl.cellartracker_importer import CellarTrackerImporter
from src.database.db import initialize_database, get_db_connection
from src.utils.logger import logger


class MockCellarTracker:
    """Mock CellarTracker API client that loads from local JSON files."""

    def __init__(self, data_dir: str = 'data/cellar-tracker'):
        self.data_dir = Path(data_dir)

    def get_list(self):
        """Return wine list from JSON file."""
        with open(self.data_dir / 'wines_list.json', 'r') as f:
            return json.load(f)

    def get_inventory(self):
        """Return inventory from JSON file."""
        with open(self.data_dir / 'inventory.json', 'r') as f:
            return json.load(f)

    def get_notes(self):
        """Return notes from JSON file."""
        with open(self.data_dir / 'notes.json', 'r') as f:
            return json.load(f)

    def get_purchase(self):
        """Return purchase history from JSON file."""
        with open(self.data_dir / 'purchase.json', 'r') as f:
            return json.load(f)

    def get_consumed(self):
        """Return consumed bottles from JSON file."""
        with open(self.data_dir / 'consumed.json', 'r') as f:
            return json.load(f)

    def get_bottles(self):
        """Return all bottles from JSON file."""
        with open(self.data_dir / 'bottles.json', 'r') as f:
            return json.load(f)


def test_import_with_sample_data():
    """Test import using sample JSON data instead of API."""

    # Initialize test database
    test_db_path = 'data/wine_cellar_test.db'
    logger.info("Initializing test database...")
    initialize_database(test_db_path)

    # Create importer with mock client
    logger.info("Creating importer with sample data...")
    importer = CellarTrackerImporter(
        username='test',
        password='test',
        db_path=test_db_path
    )

    # Replace real API client with mock
    importer.client = MockCellarTracker()

    # Run import
    logger.info("Starting import from sample data...")
    stats = importer.import_all()

    # Print results
    print("\n" + "="*60)
    print("TEST IMPORT SUMMARY")
    print("="*60)
    print(f"Wines processed:      {stats['wines_processed']}")
    print(f"  - Imported:         {stats['wines_imported']}")
    print(f"  - Updated:          {stats['wines_updated']}")
    print(f"\nBottles processed:    {stats['bottles_processed']}")
    print(f"  - Imported:         {stats['bottles_imported']}")
    print(f"  - Updated:          {stats['bottles_updated']}")
    print(f"\nProducers created:    {stats['producers_created']}")
    print(f"Regions created:      {stats['regions_created']}")
    print(f"Notes processed:      {stats['notes_processed']}")
    print(f"\nErrors:               {len(stats['errors'])}")

    if stats['errors']:
        print("\nErrors:")
        for error in stats['errors'][:5]:
            print(f"  - {error}")

    print("="*60)

    # Query some results
    logger.info("\nQuerying imported data...")
    with get_db_connection(test_db_path) as conn:
        cursor = conn.cursor()

        # Count wines
        cursor.execute("SELECT COUNT(*) FROM wines")
        wine_count = cursor.fetchone()[0]
        print(f"\nTotal wines in database: {wine_count}")

        # Count bottles by status
        cursor.execute("""
            SELECT status, COUNT(*) 
            FROM bottles 
            GROUP BY status
        """)
        print("\nBottles by status:")
        for row in cursor.fetchall():
            print(f"  {row[0]}: {row[1]}")

        # Show some wines
        cursor.execute("""
            SELECT w.wine_name, w.vintage, p.name, w.wine_type
            FROM wines w
            LEFT JOIN producers p ON w.producer_id = p.id
            LIMIT 5
        """)
        print("\nSample wines:")
        for row in cursor.fetchall():
            print(f"  {row[1]} {row[2]} {row[0]} ({row[3]})")

    logger.info(f"\n✅ Test completed! Database: {test_db_path}")


if __name__ == '__main__':
    test_import_with_sample_data()

