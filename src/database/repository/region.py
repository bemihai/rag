"""Region repository."""
from datetime import datetime

from src.database import get_db_connection
from src.database.models import Region
from src.utils import get_default_db_path, logger


class RegionRepository:
    """Repository for region-related database operations."""

    def __init__(self, db_path: str | None = None):
        """
        Initialize region repository.

        Args:
            db_path: Optional path to database file
        """
        self.db_path = db_path or get_default_db_path()

    def get_by_id(self, region_id: int) -> Region | None:
        """Get region by ID."""
        with get_db_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM regions WHERE id = ?", (region_id,))

            row = cursor.fetchone()
            if row:
                return Region(**dict(row))
            return None

    def get_by_name_and_country(self, primary_name: str, country: str, secondary_name: str | None = None) -> Region | None:
        """
        Get region by primary name, country, and optional secondary name.

        Args:
            primary_name: Primary region name
            country: Country name
            secondary_name: Optional secondary region name

        Returns:
            Region agents or None if not found
        """
        with get_db_connection(self.db_path) as conn:
            cursor = conn.cursor()

            if secondary_name:
                cursor.execute("""
                    SELECT * FROM regions
                    WHERE LOWER(primary_name) = LOWER(?) 
                    AND LOWER(country) = LOWER(?)
                    AND LOWER(secondary_name) = LOWER(?)
                """, (primary_name, country, secondary_name))
            else:
                cursor.execute("""
                    SELECT * FROM regions
                    WHERE LOWER(primary_name) = LOWER(?) 
                    AND LOWER(country) = LOWER(?)
                    AND secondary_name IS NULL
                """, (primary_name, country))

            row = cursor.fetchone()
            if row:
                return Region(**dict(row))
            return None

    def get_or_create(self, primary_name: str, country: str, secondary_name: str | None = None, description: str | None = None) -> int:
        """
        Get existing region or create new one.

        Args:
            primary_name: Primary region name (e.g., Loire Valley, Bordeaux)
            country: Country name
            secondary_name: Optional secondary region name (e.g., Médoc, Sancerre)
            description: Optional description

        Returns:
            Region ID
        """
        existing = self.get_by_name_and_country(primary_name, country, secondary_name)
        if existing:
            return existing.id

        with get_db_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO regions (primary_name, country, secondary_name, description, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (primary_name, country, secondary_name, description, datetime.now()))

            conn.commit()
            region_id = cursor.lastrowid
            logger.debug(f"Created region: {primary_name}, {country} (ID: {region_id})")
            return region_id

    def get_all(self) -> list[Region]:
        """Get all regions."""
        with get_db_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM regions ORDER BY country, primary_name")
            return [Region(**dict(row)) for row in cursor.fetchall()]
