"""Stats repository"""
from datetime import datetime

from src.database import get_db_connection
from src.utils import get_default_db_path


class StatisticsRepository:
    """Repository for wine cellar statistics and aggregations."""

    def __init__(self, db_path: str | None = None):
        """
        Initialize statistics repository.

        Args:
            db_path: Optional path to database file
        """
        self.db_path = db_path or get_default_db_path()

    def get_cellar_overview(self) -> dict:
        """
        Get overall cellar statistics.

        Returns:
            Dictionary with statistics
        """
        with get_db_connection(self.db_path) as conn:
            cursor = conn.cursor()

            # Total bottles
            cursor.execute("""
                SELECT SUM(quantity) as total
                FROM bottles WHERE status = 'in_cellar'
            """)
            total_bottles = cursor.fetchone()['total'] or 0

            # Unique wines
            cursor.execute("""
                SELECT COUNT(DISTINCT wine_id) as count
                FROM bottles WHERE status = 'in_cellar'
            """)
            unique_wines = cursor.fetchone()['count'] or 0

            # By type
            cursor.execute("""
                SELECT 
                    w.wine_type,
                    COUNT(DISTINCT w.id) as unique_wines,
                    SUM(b.quantity) as bottles
                FROM wines w
                JOIN bottles b ON w.id = b.wine_id
                WHERE b.status = 'in_cellar'
                GROUP BY w.wine_type
                ORDER BY bottles DESC
            """)
            by_type = [dict(row) for row in cursor.fetchall()]

            # By country
            cursor.execute("""
                SELECT 
                    r.country,
                    COUNT(DISTINCT w.id) as unique_wines,
                    SUM(b.quantity) as bottles
                FROM wines w
                JOIN bottles b ON w.id = b.wine_id
                LEFT JOIN regions r ON w.region_id = r.id
                WHERE b.status = 'in_cellar'
                GROUP BY r.country
                ORDER BY bottles DESC
                LIMIT 10
            """)
            by_country = [dict(row) for row in cursor.fetchall()]

            return {
                'total_bottles': total_bottles,
                'unique_wines': unique_wines,
                'by_type': by_type,
                'by_country': by_country
            }

    def get_top_rated_wines(self, limit: int = 10) -> list[dict]:
        """Get the highest rated wines in collection."""
        with get_db_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    w.id, w.wine_name, w.vintage, w.wine_type,
                    p.name as producer,
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
                LIMIT ?
            """, (limit,))

            return [dict(row) for row in cursor.fetchall()]

    def get_drinking_window_wines(self) -> dict[str, list[dict]]:
        """Get wines organized by drinking window status."""
        current_year = datetime.now().year

        with get_db_connection(self.db_path) as conn:
            cursor = conn.cursor()

            # Wines ready to drink now
            cursor.execute("""
                SELECT 
                    w.id, w.wine_name, w.vintage, w.wine_type,
                    p.name as producer,
                    w.drink_from_year, w.drink_to_year,
                    COUNT(b.id) as bottles
                FROM wines w
                LEFT JOIN producers p ON w.producer_id = p.id
                JOIN bottles b ON w.id = b.wine_id
                WHERE b.status = 'in_cellar'
                  AND w.drink_from_year <= ?
                  AND (w.drink_to_year >= ? OR w.drink_to_year IS NULL)
                GROUP BY w.id
                ORDER BY w.drink_to_year
            """, (current_year, current_year))
            ready_now = [dict(row) for row in cursor.fetchall()]

            # Wines to drink soon (window closing)
            cursor.execute("""
                SELECT 
                    w.id, w.wine_name, w.vintage, w.wine_type,
                    p.name as producer,
                    w.drink_from_year, w.drink_to_year,
                    COUNT(b.id) as bottles
                FROM wines w
                LEFT JOIN producers p ON w.producer_id = p.id
                JOIN bottles b ON w.id = b.wine_id
                WHERE b.status = 'in_cellar'
                  AND w.drink_to_year BETWEEN ? AND ?
                GROUP BY w.id
                ORDER BY w.drink_to_year
            """, (current_year, current_year + 2))
            drink_soon = [dict(row) for row in cursor.fetchall()]

            # Wines for aging
            cursor.execute("""
                SELECT 
                    w.id, w.wine_name, w.vintage, w.wine_type,
                    p.name as producer,
                    w.drink_from_year, w.drink_to_year,
                    COUNT(b.id) as bottles
                FROM wines w
                LEFT JOIN producers p ON w.producer_id = p.id
                JOIN bottles b ON w.id = b.wine_id
                WHERE b.status = 'in_cellar'
                  AND w.drink_from_year > ?
                GROUP BY w.id
                ORDER BY w.drink_from_year
            """, (current_year,))
            for_aging = [dict(row) for row in cursor.fetchall()]

            return {
                'ready_now': ready_now,
                'drink_soon': drink_soon,
                'for_aging': for_aging
            }


