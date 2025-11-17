"""Database connection and initialization."""
import sqlite3
from pathlib import Path
from contextlib import contextmanager

from src.utils import logger, get_default_db_path


DEFAULT_DB_PATH = get_default_db_path()


@contextmanager
def get_db_connection(db_path: str = DEFAULT_DB_PATH):
    """
    Context manager for database connections.

    Args:
        db_path: Path to SQLite database file

    Yields:
        sqlite3.Connection: Database connection
    """
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        conn.execute('PRAGMA foreign_keys = ON')
        conn.row_factory = sqlite3.Row
        yield conn
    finally:
        if conn:
            conn.close()


def initialize_database(db_path: str = DEFAULT_DB_PATH) -> bool:
    """
    Initialize the wine cellar database with schema.

    Args:
        db_path: Path to SQLite database file

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        logger.info(f"Initializing database at: {db_path}")

        with get_db_connection(db_path) as conn:
            cursor = conn.cursor()

            # Create tables in order of dependencies
            _create_producers_table(cursor)
            _create_regions_table(cursor)
            _create_wines_table(cursor)
            _create_bottles_table(cursor)
            _create_sync_log_table(cursor)
            _create_schema_version_table(cursor)
            _create_views(cursor)

            conn.commit()

        logger.info(f"✅ Database initialized successfully at: {db_path}")
        return True

    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        return False


def _create_producers_table(cursor: sqlite3.Cursor):
    """Create producers table."""
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS producers (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            name                TEXT NOT NULL UNIQUE,
            country             TEXT,
            region              TEXT,
            notes               TEXT,
            created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_producers_name ON producers(name)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_producers_country ON producers(country)")


def _create_regions_table(cursor: sqlite3.Cursor):
    """Create regions table."""
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS regions (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            name                TEXT NOT NULL,
            country             TEXT NOT NULL,
            sub_region          TEXT,
            created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(name, country)
        )
    """)

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_regions_country ON regions(country)")


def _create_wines_table(cursor: sqlite3.Cursor):
    """Create wines table."""
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS wines (
            id                      INTEGER PRIMARY KEY AUTOINCREMENT,
            source                  TEXT NOT NULL CHECK(source IN ('cellar_tracker', 'vivino', 'manual')),
            external_id             TEXT NOT NULL,
            wine_name               TEXT NOT NULL,
            producer_id             INTEGER REFERENCES producers(id),
            vintage                 INTEGER,
            wine_type               TEXT NOT NULL,
            varietal                TEXT,
            designation             TEXT,
            region_id               INTEGER REFERENCES regions(id),
            appellation             TEXT,
            bottle_size             TEXT DEFAULT '750ml',
            personal_rating         INTEGER,
            community_rating        DECIMAL(3,2),
            tasting_notes           TEXT,
            last_tasted_date        DATE,
            drink_from_year         INTEGER,
            drink_to_year           INTEGER,
            created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(source, external_id)
        )
    """)

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_wines_producer ON wines(producer_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_wines_region ON wines(region_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_wines_vintage ON wines(vintage)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_wines_type ON wines(wine_type)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_wines_name ON wines(wine_name)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_wines_rating ON wines(personal_rating)")


def _create_bottles_table(cursor: sqlite3.Cursor):
    """Create bottles table."""
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bottles (
            id                      INTEGER PRIMARY KEY AUTOINCREMENT,
            wine_id                 INTEGER NOT NULL REFERENCES wines(id) ON DELETE CASCADE,
            source                  TEXT NOT NULL CHECK(source IN ('cellar_tracker', 'vivino', 'manual')),
            external_bottle_id      TEXT NOT NULL,
            quantity                INTEGER NOT NULL DEFAULT 1,
            status                  TEXT NOT NULL DEFAULT 'in_cellar' 
                                    CHECK(status IN ('in_cellar', 'consumed', 'gifted', 'lost')),
            location                TEXT,
            bin                     TEXT,
            purchase_date           DATE,
            purchase_price          DECIMAL(10,2),
            currency                TEXT DEFAULT 'RON',
            store_name              TEXT,
            consumed_date           DATE,
            bottle_note             TEXT,
            created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            CHECK(
                (status = 'in_cellar' AND consumed_date IS NULL) OR
                (status = 'consumed' AND consumed_date IS NOT NULL)
            )
        )
    """)

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_bottles_wine ON bottles(wine_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_bottles_status ON bottles(status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_bottles_location ON bottles(location)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_bottles_consumed_date ON bottles(consumed_date)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_bottles_location_status ON bottles(location, status)")


def _create_sync_log_table(cursor: sqlite3.Cursor):
    """Create sync_log table."""
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sync_log (
            id                      INTEGER PRIMARY KEY AUTOINCREMENT,
            source                  TEXT NOT NULL,
            sync_type               TEXT NOT NULL,
            sync_started_at         TIMESTAMP NOT NULL,
            sync_completed_at       TIMESTAMP,
            status                  TEXT NOT NULL,
            records_processed       INTEGER DEFAULT 0,
            records_imported        INTEGER DEFAULT 0,
            records_updated         INTEGER DEFAULT 0,
            records_skipped         INTEGER DEFAULT 0,
            records_failed          INTEGER DEFAULT 0,
            error_message           TEXT,
            error_details           TEXT,
            created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sync_log_source ON sync_log(source)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sync_log_status ON sync_log(status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sync_log_date ON sync_log(sync_started_at)")


def _create_schema_version_table(cursor: sqlite3.Cursor):
    """Create schema_version table for tracking migrations."""
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS schema_version (
            version         INTEGER PRIMARY KEY,
            applied_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            description     TEXT
        )
    """)
    cursor.execute("""
        INSERT OR IGNORE INTO schema_version (version, description)
        VALUES (1, 'Initial schema')
    """)


def _create_views(cursor: sqlite3.Cursor):
    """Create database views."""

    # Current Inventory View
    cursor.execute("""
        CREATE VIEW IF NOT EXISTS current_inventory AS
        SELECT 
            w.id as wine_id,
            w.wine_name,
            p.name as producer,
            w.vintage,
            w.wine_type,
            r.country,
            r.name as region,
            b.location,
            b.bin,
            SUM(b.quantity) as total_bottles,
            w.personal_rating,
            w.community_rating,
            w.drink_from_year,
            w.drink_to_year,
            b.purchase_date as last_purchase_date
        FROM wines w
        JOIN bottles b ON w.id = b.wine_id
        LEFT JOIN producers p ON w.producer_id = p.id
        LEFT JOIN regions r ON w.region_id = r.id
        WHERE b.status = 'in_cellar'
        GROUP BY w.id, b.location, b.bin
        ORDER BY p.name, w.vintage DESC
    """)

    # Top Rated Wines View
    cursor.execute("""
        CREATE VIEW IF NOT EXISTS top_rated_wines AS
        SELECT 
            w.wine_name,
            p.name as producer,
            w.vintage,
            w.wine_type,
            r.country,
            w.personal_rating,
            w.community_rating,
            COUNT(b.id) as bottles_owned
        FROM wines w
        LEFT JOIN producers p ON w.producer_id = p.id
        LEFT JOIN regions r ON w.region_id = r.id
        LEFT JOIN bottles b ON w.id = b.wine_id AND b.status = 'in_cellar'
        WHERE w.personal_rating IS NOT NULL
        GROUP BY w.id
        ORDER BY w.personal_rating DESC, w.community_rating DESC
    """)

    # Cellar Statistics View
    cursor.execute("""
        CREATE VIEW IF NOT EXISTS cellar_stats AS
        SELECT 
            w.wine_type,
            r.country,
            COUNT(DISTINCT w.id) as unique_wines,
            SUM(b.quantity) as total_bottles,
            AVG(w.personal_rating) as avg_personal_rating,
            AVG(w.community_rating) as avg_community_rating
        FROM wines w
        JOIN bottles b ON w.id = b.wine_id
        LEFT JOIN regions r ON w.region_id = r.id
        WHERE b.status = 'in_cellar'
        GROUP BY w.wine_type, r.country
        ORDER BY total_bottles DESC
    """)


def drop_all_tables(db_path: str = DEFAULT_DB_PATH) -> bool:
    """
    Drop all tables (for testing/reset purposes).

    Args:
        db_path: Path to SQLite database file

    Returns:
        bool: True if successful
    """
    try:
        with get_db_connection(db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("DROP VIEW IF EXISTS current_inventory")
            cursor.execute("DROP VIEW IF EXISTS top_rated_wines")
            cursor.execute("DROP VIEW IF EXISTS cellar_stats")
            cursor.execute("DROP TABLE IF EXISTS sync_log")
            cursor.execute("DROP TABLE IF EXISTS bottles")
            cursor.execute("DROP TABLE IF EXISTS wines")
            cursor.execute("DROP TABLE IF EXISTS regions")
            cursor.execute("DROP TABLE IF EXISTS producers")
            cursor.execute("DROP TABLE IF EXISTS schema_version")

            conn.commit()

        logger.info("✅ All tables dropped successfully")
        return True

    except Exception as e:
        logger.error(f"Failed to drop tables: {e}")
        return False

