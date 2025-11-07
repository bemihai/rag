"""Wine repository"""
from datetime import datetime

from src.database import get_db_connection, build_update_query
from src.database.models import Wine
from src.utils import get_default_db_path, logger


class WineRepository:
    """Repository for wine-related database operations."""

    def __init__(self, db_path: str | None = None):
        """
        Initialize wine repository.

        Args:
            db_path: Optional path to database file
        """
        self.db_path = db_path or get_default_db_path()

    def get_by_id(self, wine_id: int) -> Wine | None:
        """
        Get wine by ID.

        Args:
            wine_id: Wine ID

        Returns:
            Wine model or None if not found
        """
        with get_db_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT w.*, p.name as producer_name, r.name as region_name, r.country
                FROM wines w
                LEFT JOIN producers p ON w.producer_id = p.id
                LEFT JOIN regions r ON w.region_id = r.id
                WHERE w.id = ?
            """, (wine_id,))

            row = cursor.fetchone()
            if row:
                return Wine(**dict(row))
            return None

    def get_by_external_id(self, external_id: int) -> Wine | None:
        """
        Get wine by external ID.

        Args:
            external_id: External ID from source system

        Returns:
            Wine model or None if not found
        """
        with get_db_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT w.*, p.name as producer_name, r.name as region_name, r.country
                FROM wines w
                LEFT JOIN producers p ON w.producer_id = p.id
                LEFT JOIN regions r ON w.region_id = r.id
                WHERE w.external_id = ?
            """, (external_id,))

            row = cursor.fetchone()
            if row:
                return Wine(**dict(row))
            return None

    def get_all(
        self, wine_type: str | None = None, country: str | None = None, min_rating: int | None = None,
        search: str | None = None, limit: int | None = None, offset: int = 0
    ) -> list[Wine]:
        """
        Get all wines with optional filters.

        Args:
            wine_type: Filter by wine type
            country: Filter by country
            min_rating: Minimum personal rating
            search: Search in wine name, producer, varietal
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of Wine models
        """
        with get_db_connection(self.db_path) as conn:
            cursor = conn.cursor()

            query = """
                SELECT w.*, p.name as producer_name, r.name as region_name, r.country
                FROM wines w
                LEFT JOIN producers p ON w.producer_id = p.id
                LEFT JOIN regions r ON w.region_id = r.id
                WHERE 1=1
            """
            params = []

            if wine_type:
                query += " AND w.wine_type = ?"
                params.append(wine_type)

            if country:
                query += " AND r.country = ?"
                params.append(country)

            if min_rating:
                query += " AND w.personal_rating >= ?"
                params.append(min_rating)

            if search:
                query += " AND (w.wine_name LIKE ? OR p.name LIKE ? OR w.varietal LIKE ?)"
                search_param = f'%{search}%'
                params.extend([search_param, search_param, search_param])

            query += " ORDER BY p.name, w.vintage DESC"

            if limit:
                query += " LIMIT ? OFFSET ?"
                params.extend([limit, offset])

            cursor.execute(query, params)
            return [Wine(**dict(row)) for row in cursor.fetchall()]

    def create(self, wine: Wine) -> int:
        """
        Create new wine record.

        Args:
            wine: Wine model

        Returns:
            ID of created wine
        """
        with get_db_connection(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO wines (
                    source, external_id, wine_name, producer_id, vintage,
                    wine_type, varietal, designation, region_id, appellation,
                    bottle_size, personal_rating, community_rating, tasting_notes,
                    last_tasted_date, drink_from_year, drink_to_year,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                wine.source, wine.external_id, wine.wine_name, wine.producer_id,
                wine.vintage, wine.wine_type, wine.varietal, wine.designation,
                wine.region_id, wine.appellation, wine.bottle_size,
                wine.personal_rating, wine.community_rating, wine.tasting_notes,
                wine.last_tasted_date, wine.drink_from_year, wine.drink_to_year,
                wine.created_at or datetime.now(), wine.updated_at or datetime.now()
            ))

            conn.commit()
            wine_id = cursor.lastrowid
            logger.debug(f"Created wine: {wine.wine_name} (ID: {wine_id})")
            return wine_id

    def update(self, wine: Wine) -> bool:
        """
        Update existing wine record.

        Args:
            wine: Wine model with updated data

        Returns:
            True if successful
        """
        if not wine.id:
            raise ValueError("Wine ID is required for update")

        with get_db_connection(self.db_path) as conn:
            cursor = conn.cursor()
            update_query, params = build_update_query(
                "wines", wine, "id", ["producer_name", "region_name", "country"]
            )
            cursor.execute(update_query, params)

            conn.commit()
            logger.debug(f"Updated wine: {wine.wine_name} (ID: {wine.id})")
            return True

    def delete(self, wine_id: int) -> bool:
        """
        Delete wine record (and cascade to bottles).

        Args:
            wine_id: Wine ID

        Returns:
            True if successful
        """
        with get_db_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM wines WHERE id = ?", (wine_id,))
            conn.commit()
            logger.debug(f"Deleted wine ID: {wine_id}")
            return True

    def count(
        self,
        wine_type: str | None = None,
        country: str | None = None
    ) -> int:
        """
        Count wines with optional filters.

        Args:
            wine_type: Filter by wine type
            country: Filter by country

        Returns:
            Number of wines
        """
        with get_db_connection(self.db_path) as conn:
            cursor = conn.cursor()

            query = """
                SELECT COUNT(*) as count
                FROM wines w
                LEFT JOIN regions r ON w.region_id = r.id
                WHERE 1=1
            """
            params = []

            if wine_type:
                query += " AND w.wine_type = ?"
                params.append(wine_type)

            if country:
                query += " AND r.country = ?"
                params.append(country)

            cursor.execute(query, params)
            return cursor.fetchone()['count']
