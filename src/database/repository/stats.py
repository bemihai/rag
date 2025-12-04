"""Stats repository"""
from datetime import datetime

from src.database import get_db_connection
from src.utils import get_default_db_path


class StatsRepository:
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
                    t.personal_rating,
                    t.community_rating,
                    COUNT(b.id) as bottles_owned
                FROM wines w
                LEFT JOIN producers p ON w.producer_id = p.id
                LEFT JOIN regions r ON w.region_id = r.id
                LEFT JOIN tastings t ON w.id = t.wine_id
                LEFT JOIN bottles b ON w.id = b.wine_id AND b.status = 'in_cellar'
                WHERE t.personal_rating IS NOT NULL
                GROUP BY w.id
                ORDER BY t.personal_rating DESC, t.community_rating DESC
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

    def get_consumed_with_ratings(self, wine_type: str | None = None, limit: int | None = None) -> list[dict]:
        """
        Get consumed bottles with wine details and ratings.

        Args:
            wine_type: Filter by wine type
            limit: Maximum number of results

        Returns:
            List of dictionaries with combined bottle and wine info, sorted by rating (descending)
        """
        with get_db_connection(self.db_path) as conn:
            cursor = conn.cursor()

            query = """
                SELECT 
                    b.*,
                    w.wine_name, w.wine_type, w.vintage,
                    p.name as producer_name,
                    r.country, 
                    COALESCE(r.primary_name || COALESCE(' - ' || r.secondary_name, ''), '') as region_name,
                    t.personal_rating,
                    t.tasting_notes
                FROM bottles b
                JOIN wines w ON b.wine_id = w.id
                LEFT JOIN producers p ON w.producer_id = p.id
                LEFT JOIN regions r ON w.region_id = r.id
                LEFT JOIN tastings t ON w.id = t.wine_id
                WHERE b.status = 'consumed' AND t.personal_rating IS NOT NULL
            """
            params = []

            if wine_type:
                query += " AND w.wine_type = ?"
                params.append(wine_type)

            query += " ORDER BY t.personal_rating DESC, b.consumed_date DESC"
            if limit:
                query += " LIMIT ?"
                params.append(limit)

            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def get_cellar_value(self) -> dict:
        """
        Calculate total cellar value based on purchase prices.

        Returns:
            Dictionary with value statistics by currency
        """
        with get_db_connection(self.db_path) as conn:
            cursor = conn.cursor()

            # Get total value by currency
            cursor.execute("""
                SELECT 
                    currency,
                    SUM(quantity * purchase_price) as total_value,
                    COUNT(DISTINCT wine_id) as wines_with_price
                FROM bottles
                WHERE status = 'in_cellar' AND purchase_price IS NOT NULL
                GROUP BY currency
                ORDER BY total_value DESC
            """)
            by_currency = [dict(row) for row in cursor.fetchall()]

            # Get bottles without price info
            cursor.execute("""
                SELECT SUM(quantity) as count
                FROM bottles
                WHERE status = 'in_cellar' AND purchase_price IS NULL
            """)
            bottles_without_price = cursor.fetchone()['count'] or 0

            return {
                'by_currency': by_currency,
                'bottles_without_price': bottles_without_price
            }

    def get_drinking_window_stats(self) -> dict:
        """
        Get statistics about bottles by drinking window status.

        Returns:
            Dictionary with counts for ready, hold, and unknown categories
        """
        current_year = datetime.now().year

        with get_db_connection(self.db_path) as conn:
            cursor = conn.cursor()

            # Bottles ready to drink
            cursor.execute("""
                SELECT SUM(b.quantity) as count
                FROM bottles b
                JOIN wines w ON b.wine_id = w.id
                WHERE b.status = 'in_cellar'
                  AND w.drink_from_year IS NOT NULL
                  AND w.drink_from_year <= ?
                  AND (w.drink_to_year >= ? OR w.drink_to_year IS NULL)
            """, (current_year, current_year))
            ready_to_drink = cursor.fetchone()['count'] or 0

            # Bottles to hold (not yet in drinking window)
            cursor.execute("""
                SELECT SUM(b.quantity) as count
                FROM bottles b
                JOIN wines w ON b.wine_id = w.id
                WHERE b.status = 'in_cellar'
                  AND w.drink_from_year IS NOT NULL
                  AND w.drink_from_year > ?
            """, (current_year,))
            to_hold = cursor.fetchone()['count'] or 0

            # Bottles with unknown drinking window
            cursor.execute("""
                SELECT SUM(b.quantity) as count
                FROM bottles b
                JOIN wines w ON b.wine_id = w.id
                WHERE b.status = 'in_cellar'
                  AND w.drink_from_year IS NULL
            """)
            unknown = cursor.fetchone()['count'] or 0

            return {
                'ready_to_drink': ready_to_drink,
                'to_hold': to_hold,
                'unknown': unknown
            }

    def get_rating_statistics(self) -> dict:
        """
        Get comprehensive rating statistics for consumed wines.

        Returns:
            Dictionary with rating metrics (avg, min, max, count, distribution)
        """
        with get_db_connection(self.db_path) as conn:
            cursor = conn.cursor()

            # Overall rating stats
            cursor.execute("""
                SELECT 
                    AVG(t.personal_rating) as avg_rating,
                    MIN(t.personal_rating) as min_rating,
                    MAX(t.personal_rating) as max_rating,
                    COUNT(DISTINCT b.id) as wines_rated
                FROM bottles b
                JOIN wines w ON b.wine_id = w.id
                LEFT JOIN tastings t ON w.id = t.wine_id
                WHERE b.status = 'consumed' AND t.personal_rating IS NOT NULL
            """)
            overall = dict(cursor.fetchone())

            # Rating distribution
            cursor.execute("""
                SELECT 
                    CASE 
                        WHEN t.personal_rating < 50 THEN '0-49'
                        WHEN t.personal_rating < 70 THEN '50-69'
                        WHEN t.personal_rating < 80 THEN '70-79'
                        WHEN t.personal_rating < 90 THEN '80-89'
                        ELSE '90-100'
                    END as rating_range,
                    COUNT(*) as count
                FROM bottles b
                JOIN wines w ON b.wine_id = w.id
                LEFT JOIN tastings t ON w.id = t.wine_id
                WHERE b.status = 'consumed' AND t.personal_rating IS NOT NULL
                GROUP BY rating_range
                ORDER BY rating_range
            """)
            distribution = [dict(row) for row in cursor.fetchall()]

            return {
                'overall': overall,
                'distribution': distribution
            }

    def get_wine_type_stats(self) -> list[dict]:
        """
        Get statistics by wine type for consumed wines.

        Returns:
            List of dicts with type, count, avg_rating, highest_rated, most_recent
        """
        with get_db_connection(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT 
                    w.wine_type,
                    COUNT(DISTINCT b.id) as wines_tasted,
                    AVG(t.personal_rating) as avg_rating,
                    MAX(t.personal_rating) as highest_rating,
                    MAX(b.consumed_date) as most_recent_date
                FROM bottles b
                JOIN wines w ON b.wine_id = w.id
                LEFT JOIN tastings t ON w.id = t.wine_id
                WHERE b.status = 'consumed'
                GROUP BY w.wine_type
                ORDER BY wines_tasted DESC
            """)

            return [dict(row) for row in cursor.fetchall()]

    def get_varietal_preferences(self, limit: int = 10) -> list[dict]:
        """
        Get top varietal preferences based on consumed wines.

        Args:
            limit: Maximum number of varietals to return

        Returns:
            List of dicts with varietal, count, avg_rating
        """
        with get_db_connection(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT 
                    w.varietal,
                    COUNT(DISTINCT b.id) as wines_tasted,
                    AVG(t.personal_rating) as avg_rating,
                    MAX(t.personal_rating) as highest_rating
                FROM bottles b
                JOIN wines w ON b.wine_id = w.id
                LEFT JOIN tastings t ON w.id = t.wine_id
                WHERE b.status = 'consumed' AND w.varietal IS NOT NULL
                GROUP BY w.varietal
                HAVING COUNT(DISTINCT b.id) >= 1
                ORDER BY wines_tasted DESC, avg_rating DESC
                LIMIT ?
            """, (limit,))

            return [dict(row) for row in cursor.fetchall()]

    def get_producer_preferences(self, limit: int = 10) -> list[dict]:
        """
        Get top producer preferences based on consumed wines.

        Args:
            limit: Maximum number of producers to return

        Returns:
            List of dicts with producer info and stats
        """
        with get_db_connection(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT 
                    p.name as producer_name,
                    p.country,
                    COUNT(DISTINCT b.id) as wines_tasted,
                    AVG(t.personal_rating) as avg_rating,
                    MAX(t.personal_rating) as highest_rating
                FROM bottles b
                JOIN wines w ON b.wine_id = w.id
                LEFT JOIN producers p ON w.producer_id = p.id
                LEFT JOIN tastings t ON w.id = t.wine_id
                WHERE b.status = 'consumed' AND p.name IS NOT NULL
                GROUP BY p.id
                HAVING COUNT(DISTINCT b.id) >= 1
                ORDER BY wines_tasted DESC, avg_rating DESC
                LIMIT ?
            """, (limit,))

            return [dict(row) for row in cursor.fetchall()]

    def get_region_preferences(self, limit: int = 10) -> list[dict]:
        """
        Get top region preferences based on consumed wines.

        Args:
            limit: Maximum number of regions to return

        Returns:
            List of dicts with region info and stats
        """
        with get_db_connection(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT 
                    COALESCE(r.primary_name || COALESCE(' - ' || r.secondary_name, ''), 'Unknown') as region_name,
                    r.country,
                    COUNT(DISTINCT b.id) as wines_tasted,
                    AVG(t.personal_rating) as avg_rating,
                    MAX(t.personal_rating) as highest_rating
                FROM bottles b
                JOIN wines w ON b.wine_id = w.id
                LEFT JOIN regions r ON w.region_id = r.id
                LEFT JOIN tastings t ON w.id = t.wine_id
                WHERE b.status = 'consumed' AND r.primary_name IS NOT NULL
                GROUP BY r.id
                HAVING COUNT(DISTINCT b.id) >= 1
                ORDER BY wines_tasted DESC, avg_rating DESC
                LIMIT ?
            """, (limit,))

            return [dict(row) for row in cursor.fetchall()]

    def get_rating_timeline(self) -> list[dict]:
        """
        Get rating trends over time (by month).

        Returns:
            List of dicts with month, avg_rating, count
        """
        with get_db_connection(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT 
                    strftime('%Y-%m', b.consumed_date) as month,
                    AVG(t.personal_rating) as avg_rating,
                    COUNT(DISTINCT b.id) as wines_count
                FROM bottles b
                JOIN wines w ON b.wine_id = w.id
                LEFT JOIN tastings t ON w.id = t.wine_id
                WHERE b.status = 'consumed' 
                  AND b.consumed_date IS NOT NULL
                  AND t.personal_rating IS NOT NULL
                GROUP BY month
                ORDER BY month
            """)

            return [dict(row) for row in cursor.fetchall()]

    def get_tasting_streak_days(self) -> int:
        """
        Calculate the number of consecutive months with tastings.

        Returns:
            Number of consecutive months with wine tastings
        """
        with get_db_connection(self.db_path) as conn:
            cursor = conn.cursor()

            # Get months with tastings, ordered by date descending
            cursor.execute("""
                SELECT DISTINCT strftime('%Y-%m', b.consumed_date) as month
                FROM bottles b
                WHERE b.status = 'consumed' AND b.consumed_date IS NOT NULL
                ORDER BY month DESC
            """)

            months = [row['month'] for row in cursor.fetchall()]

            if not months:
                return 0

            # Count consecutive months from most recent
            from datetime import datetime
            streak = 1
            current = datetime.strptime(months[0], '%Y-%m')

            for i in range(1, len(months)):
                prev = datetime.strptime(months[i], '%Y-%m')
                # Check if months are consecutive
                month_diff = (current.year - prev.year) * 12 + (current.month - prev.month)
                if month_diff == 1:
                    streak += 1
                    current = prev
                else:
                    break

            return streak


    def get_varietal_distribution(self, limit: int = 5) -> list[dict]:
        """
        Get distribution of wines by main grape/varietal.

        Args:
            limit: Maximum number of varietals to return

        Returns:
            List of dictionaries with varietal and bottle counts
        """
        with get_db_connection(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT 
                    w.varietal,
                    COUNT(DISTINCT w.id) as unique_wines,
                    SUM(b.quantity) as bottles
                FROM wines w
                JOIN bottles b ON w.id = b.wine_id
                WHERE b.status = 'in_cellar' 
                  AND w.varietal IS NOT NULL 
                  AND w.varietal != ''
                GROUP BY w.varietal
                ORDER BY bottles DESC
                LIMIT ?
            """, (limit,))

            return [dict(row) for row in cursor.fetchall()]

    def get_region_distribution(self, limit: int = 5) -> list[dict]:
        """
        Get distribution of wines by region.

        Args:
            limit: Maximum number of regions to return

        Returns:
            List of dictionaries with region and bottle counts
        """
        with get_db_connection(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT 
                    COALESCE(r.primary_name || COALESCE(' - ' || r.secondary_name, ''), '') as region,
                    r.country,
                    COUNT(DISTINCT w.id) as unique_wines,
                    SUM(b.quantity) as bottles
                FROM wines w
                JOIN bottles b ON w.id = b.wine_id
                LEFT JOIN regions r ON w.region_id = r.id
                WHERE b.status = 'in_cellar' 
                  AND r.primary_name IS NOT NULL 
                  AND r.primary_name != ''
                GROUP BY r.id, r.country
                ORDER BY bottles DESC
                LIMIT ?
            """, (limit,))

            return [dict(row) for row in cursor.fetchall()]

    def get_cellar_size_over_time(self) -> list[dict]:
        """
        Get cellar size progression over time for CellarTracker bottles only.
        Tracks cumulative bottle count by month based on purchase dates.

        Returns:
            List of dictionaries with month and cumulative bottle count
        """
        with get_db_connection(self.db_path) as conn:
            cursor = conn.cursor()

            # Get monthly cellar size progression for CellarTracker bottles only
            cursor.execute("""
                WITH monthly_purchases AS (
                    SELECT 
                        DATE(purchase_date, 'start of month') as month,
                        SUM(quantity) as bottles_added
                    FROM bottles b
                    JOIN wines w ON b.wine_id = w.id
                    WHERE b.source = 'cellar_tracker' 
                      AND b.purchase_date IS NOT NULL
                    GROUP BY DATE(purchase_date, 'start of month')
                ),
                monthly_consumption AS (
                    SELECT 
                        DATE(consumed_date, 'start of month') as month,
                        SUM(quantity) as bottles_consumed
                    FROM bottles b
                    JOIN wines w ON b.wine_id = w.id
                    WHERE b.source = 'cellar_tracker' 
                      AND b.consumed_date IS NOT NULL
                      AND b.status = 'consumed'
                    GROUP BY DATE(consumed_date, 'start of month')
                ),
                all_months AS (
                    SELECT month FROM monthly_purchases
                    UNION 
                    SELECT month FROM monthly_consumption
                ),
                monthly_net_change AS (
                    SELECT 
                        am.month,
                        COALESCE(mp.bottles_added, 0) - COALESCE(mc.bottles_consumed, 0) as net_change
                    FROM all_months am
                    LEFT JOIN monthly_purchases mp ON am.month = mp.month
                    LEFT JOIN monthly_consumption mc ON am.month = mc.month
                )
                SELECT 
                    month,
                    net_change,
                    SUM(net_change) OVER (ORDER BY month) as cumulative_bottles
                FROM monthly_net_change
                ORDER BY month
            """)

            results = [dict(row) for row in cursor.fetchall()]

            # Format month for better display
            for result in results:
                if result['month']:
                    # Convert YYYY-MM-DD to YYYY-MM format for display
                    result['month_display'] = result['month'][:7]

            return results
