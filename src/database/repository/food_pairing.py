"""Food pairing rules repository."""
from datetime import datetime

from src.database import get_db_connection
from src.database.models import FoodPairingRule
from src.utils import get_default_db_path, logger


class FoodPairingRepository:
    """Repository for food pairing rules database operations."""

    def __init__(self, db_path: str | None = None):
        """
        Initialize food pairing repository.

        Args:
            db_path: Optional path to database file
        """
        self.db_path = db_path or get_default_db_path()

    def get_by_id(self, rule_id: int) -> FoodPairingRule | None:
        """
        Get pairing rule by ID.

        Args:
            rule_id: Rule ID

        Returns:
            FoodPairingRule agents or None if not found
        """
        with get_db_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM food_pairing_rules WHERE id = ?", (rule_id,))

            row = cursor.fetchone()
            if row:
                return FoodPairingRule(**dict(row))
            return None

    def get_by_food_name(self, food_name: str) -> FoodPairingRule | None:
        """
        Get pairing rule by food name (exact match).

        Args:
            food_name: Food name to search for

        Returns:
            FoodPairingRule agents or None if not found
        """
        with get_db_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM food_pairing_rules WHERE LOWER(food_name) = LOWER(?)",
                (food_name,)
            )

            row = cursor.fetchone()
            if row:
                return FoodPairingRule(**dict(row))
            return None

    def search_by_food_name(self, search_term: str) -> list[FoodPairingRule]:
        """
        Search pairing rules by food name (partial match).

        Args:
            search_term: Search term to match against food names

        Returns:
            List of FoodPairingRule models
        """
        with get_db_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM food_pairing_rules WHERE LOWER(food_name) LIKE LOWER(?) ORDER BY food_name",
                (f"%{search_term}%",)
            )

            return [FoodPairingRule(**dict(row)) for row in cursor.fetchall()]

    def get_by_category(self, category: str) -> list[FoodPairingRule]:
        """
        Get all pairing rules for a specific category.

        Args:
            category: Category name (e.g., 'red_meats', 'seafood', 'cheese')

        Returns:
            List of FoodPairingRule models
        """
        with get_db_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM food_pairing_rules WHERE category = ? ORDER BY food_name",
                (category,)
            )

            return [FoodPairingRule(**dict(row)) for row in cursor.fetchall()]

    def get_all(self) -> list[FoodPairingRule]:
        """
        Get all pairing rules.

        Returns:
            List of FoodPairingRule models
        """
        with get_db_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM food_pairing_rules ORDER BY category, food_name")

            return [FoodPairingRule(**dict(row)) for row in cursor.fetchall()]

    def get_all_categories(self) -> list[str]:
        """
        Get list of all unique categories.

        Returns:
            List of category names
        """
        with get_db_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT DISTINCT category FROM food_pairing_rules WHERE category IS NOT NULL ORDER BY category"
            )

            return [row['category'] for row in cursor.fetchall()]

    def create(self, rule: FoodPairingRule) -> int:
        """
        Create new pairing rule.

        Args:
            rule: FoodPairingRule agents

        Returns:
            ID of created rule
        """
        with get_db_connection(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO food_pairing_rules (
                    food_name, category, wine_types, varietals, 
                    characteristics, pairing_explanation,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                rule.food_name, rule.category, rule.wine_types, rule.varietals,
                rule.characteristics, rule.pairing_explanation,
                rule.created_at or datetime.now(), rule.updated_at or datetime.now()
            ))

            conn.commit()
            rule_id = cursor.lastrowid
            logger.debug(f"Created pairing rule: {rule.food_name} (ID: {rule_id})")
            return rule_id

    def update(self, rule: FoodPairingRule) -> bool:
        """
        Update existing pairing rule.

        Args:
            rule: FoodPairingRule agents with updated data

        Returns:
            True if successful
        """
        if not rule.id:
            raise ValueError("Rule ID is required for update")

        with get_db_connection(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE food_pairing_rules
                SET food_name = ?, category = ?, wine_types = ?, varietals = ?,
                    characteristics = ?, pairing_explanation = ?, updated_at = ?
                WHERE id = ?
            """, (
                rule.food_name, rule.category, rule.wine_types, rule.varietals,
                rule.characteristics, rule.pairing_explanation,
                datetime.now(), rule.id
            ))

            conn.commit()
            logger.debug(f"Updated pairing rule ID: {rule.id}")
            return True

    def delete(self, rule_id: int) -> bool:
        """
        Delete pairing rule.

        Args:
            rule_id: Rule ID to delete

        Returns:
            True if successful
        """
        with get_db_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM food_pairing_rules WHERE id = ?", (rule_id,))
            conn.commit()
            logger.debug(f"Deleted pairing rule ID: {rule_id}")
            return True

    def find_matching_rule(self, food_input: str) -> FoodPairingRule | None:
        """
        Find a matching pairing rule for user input.

        First tries exact match, then partial match.

        Args:
            food_input: User's food input (e.g., "steak", "grilled salmon")

        Returns:
            FoodPairingRule agents or None if not found
        """
        food_lower = food_input.lower().strip()

        # Try exact match first
        exact_match = self.get_by_food_name(food_lower)
        if exact_match:
            return exact_match

        # Try partial match on all rules
        with get_db_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM food_pairing_rules ORDER BY LENGTH(food_name) DESC")

            all_rules = [FoodPairingRule(**dict(row)) for row in cursor.fetchall()]

            # Check if any food name is contained in the input or vice versa
            for rule in all_rules:
                rule_name_lower = rule.food_name.lower()
                if rule_name_lower in food_lower or food_lower in rule_name_lower:
                    return rule

        return None

