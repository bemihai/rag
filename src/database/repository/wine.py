"""Wine repository"""
from datetime import datetime

from src.database import get_db_connection, build_update_query
from src.database.models import Wine
from src.database.utils import calculate_similarity
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
                SELECT 
                    w.*, 
                    p.name as producer_name, 
                    COALESCE(r.primary_name || COALESCE(' - ' || r.secondary_name, ''), '') as region_name,
                    r.country,
                    t.personal_rating,
                    t.community_rating,
                    t.tasting_notes,
                    t.last_tasted_date
                FROM wines w
                LEFT JOIN producers p ON w.producer_id = p.id
                LEFT JOIN regions r ON w.region_id = r.id
                LEFT JOIN tastings t ON w.id = t.wine_id
                WHERE w.id = ?
            """, (wine_id,))

            row = cursor.fetchone()
            if row:
                return Wine(**dict(row))
            return None

    def get_by_external_id(self, external_id: str) -> Wine | None:
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
                SELECT 
                    w.*, 
                    p.name as producer_name, 
                    COALESCE(r.primary_name || COALESCE(' - ' || r.secondary_name, ''), '') as region_name,
                    r.country,
                    t.personal_rating,
                    t.community_rating,
                    t.tasting_notes,
                    t.last_tasted_date
                FROM wines w
                LEFT JOIN producers p ON w.producer_id = p.id
                LEFT JOIN regions r ON w.region_id = r.id
                LEFT JOIN tastings t ON w.id = t.wine_id
                WHERE w.external_id = ?
            """, (external_id,))

            row = cursor.fetchone()
            if row:
                return Wine(**dict(row))
            return None

    def find_duplicates(
            self, wine_name: str, producer: str, wine_type: str, vintage: int | None, confidence: float = 0.85
    ) -> list[Wine] | None:
        """
        Get duplicate wines based on wine name, producer, type, and vintage.

        Matching Algorithm:
            - Producer similarity: max 30% (weighted by string similarity)
            - Wine name similarity: max 30% (weighted by string similarity)
            - Vintage match: 40% (if both have vintage)
            - Confidence threshold: default 85%

        Returns:
            List of Wine models that are duplicates or None.
        """
        matches = []

        with get_db_connection(self.db_path) as conn:
            cursor = conn.cursor()

            # Get all the wines with same type
            cursor.execute("""
                SELECT w.id, w.wine_name, p.name as producer_name, w.vintage
                FROM wines w
                LEFT JOIN producers p ON w.producer_id = p.id
                WHERE w.wine_type = ?
            """, (wine_type,))
            existing_wines = cursor.fetchall()

            for existing in existing_wines:
                score = 0.0

                # Vintage match
                if vintage and existing["vintage"]:
                    if vintage == existing["vintage"]:
                        score += 30
                elif not vintage and not existing["vintage"]:
                    score += 30

                # Producer match
                if producer and existing["producer_name"]:
                    producer_similarity = calculate_similarity(producer, existing["producer_name"])
                    score += producer_similarity * 30

                # Wine name match
                if wine_name and existing["wine_name"]:
                    name_similarity = calculate_similarity(
                        wine_name,
                        existing["wine_name"]
                    )
                    score += name_similarity * 40

                if score >= 100 * confidence:
                    matches.append(
                        (existing["id"], score, existing["wine_name"], existing["producer_name"], existing["vintage"])
                    )

            # Sort matches by confidence score
            matches.sort(key=lambda x: x[1], reverse=True)

            return matches


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
                SELECT 
                    w.*, 
                    p.name as producer_name, 
                    COALESCE(r.primary_name || COALESCE(' - ' || r.secondary_name, ''), '') as region_name,
                    r.country,
                    t.personal_rating,
                    t.community_rating,
                    t.tasting_notes,
                    t.last_tasted_date
                FROM wines w
                LEFT JOIN producers p ON w.producer_id = p.id
                LEFT JOIN regions r ON w.region_id = r.id
                LEFT JOIN tastings t ON w.id = t.wine_id
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
                query += " AND t.personal_rating >= ?"
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
                    vineyard, bottle_size, drink_from_year, drink_to_year, drink_index,
                    q_purchased, q_quantity, q_consumed,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                wine.source, wine.external_id, wine.wine_name, wine.producer_id,
                wine.vintage, wine.wine_type, wine.varietal, wine.designation,
                wine.region_id, wine.appellation, wine.vineyard, wine.bottle_size,
                wine.drink_from_year, wine.drink_to_year, wine.drink_index,
                wine.q_purchased, wine.q_quantity, wine.q_consumed,
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
                "wines", wine, "id", ["producer_name", "region_name", "country", "personal_rating", "community_rating", "tasting_notes", "last_tasted_date"]
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


