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

    def get_by_name_and_country(self, name: str, country: str) -> Region | None:
        """Get region by name and country."""
        with get_db_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM regions
                WHERE LOWER(name) = LOWER(?) AND LOWER(country) = LOWER(?)
            """, (name, country))

            row = cursor.fetchone()
            if row:
                return Region(**dict(row))
            return None

    def get_or_create(self, name: str, country: str, sub_region: str | None = None) -> int:
        """
        Get existing region or create new one.

        Args:
            name: Region name
            country: Country name
            sub_region: Optional sub-region

        Returns:
            Region ID
        """
        existing = self.get_by_name_and_country(name, country)
        if existing:
            return existing.id

        with get_db_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO regions (name, country, sub_region, created_at)
                VALUES (?, ?, ?, ?)
            """, (name, country, sub_region, datetime.now()))

            conn.commit()
            region_id = cursor.lastrowid
            logger.info(f"Created region: {name}, {country} (ID: {region_id})")
            return region_id

    def get_all(self) -> list[Region]:
        """Get all regions."""
        with get_db_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM regions ORDER BY country, name")
            return [Region(**dict(row)) for row in cursor.fetchall()]
