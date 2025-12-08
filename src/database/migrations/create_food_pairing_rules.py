"""
Migration script to create food_pairing_rules table and populate it with initial data.

This migration creates the food_pairing_rules table and inserts the pairing rules
that were previously hardcoded in the pairing_tools.py file.
"""

import sqlite3
from datetime import datetime
from pathlib import Path


def create_food_pairing_rules_table(conn: sqlite3.Connection):
    """Create food_pairing_rules table."""
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS food_pairing_rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            food_name TEXT NOT NULL UNIQUE,
            category TEXT,
            wine_types TEXT NOT NULL,
            varietals TEXT NOT NULL,
            characteristics TEXT,
            pairing_explanation TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create index on food_name for faster lookups
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_food_pairing_food_name 
        ON food_pairing_rules(food_name)
    """)

    # Create index on category for filtering
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_food_pairing_category 
        ON food_pairing_rules(category)
    """)

    conn.commit()
    print("✓ Created food_pairing_rules table")


def insert_pairing_rules(conn: sqlite3.Connection):
    """Insert initial pairing rules."""
    cursor = conn.cursor()

    # Pairing rules from the original FOOD_PAIRING_RULES dict
    rules = [
        # Red meats
        ("steak", "red_meats", "Red",
         "Cabernet Sauvignon,Malbec,Syrah,Shiraz,Tempranillo,Nebbiolo",
         "Full-bodied reds with firm tannins",
         "Tannins cut through fat, bold flavors match rich meat"),

        ("beef", "red_meats", "Red",
         "Cabernet Sauvignon,Malbec,Syrah,Merlot,Zinfandel",
         "Full-bodied reds",
         "Rich flavors complement beef, tannins balance fat"),

        ("lamb", "red_meats", "Red",
         "Bordeaux Blend,Syrah,Rioja,Chianti,Barolo",
         "Medium to full-bodied reds with good structure",
         "Earthy notes complement lamb's gaminess"),

        ("pork", "red_meats", "Red,White",
         "Pinot Noir,Chardonnay,Riesling,Beaujolais",
         "Light to medium-bodied wines",
         "Lighter meats need softer wines"),

        # Poultry
        ("chicken", "poultry", "White,Red",
         "Chardonnay,Pinot Grigio,Pinot Noir,Beaujolais",
         "Light to medium-bodied wines",
         "Versatile pairing depends on preparation"),

        ("duck", "poultry", "Red",
         "Pinot Noir,Syrah,Merlot,Burgundy",
         "Medium-bodied reds with good acidity",
         "Rich duck meat needs wines with acidity and fruit"),

        ("turkey", "poultry", "White,Red",
         "Pinot Noir,Chardonnay,Riesling,Beaujolais",
         "Medium-bodied wines with good acidity",
         "Versatile for various preparations"),

        # Seafood
        ("salmon", "seafood", "White,Rosé,Red",
         "Pinot Noir,Chardonnay,Rosé,Burgundy",
         "Light reds or fuller whites",
         "Rich fish can handle light reds or oaked whites"),

        ("tuna", "seafood", "White,Rosé,Red",
         "Pinot Noir,Rosé,Sauvignon Blanc",
         "Light reds or crisp whites",
         "Meaty fish pairs well with light reds"),

        ("white fish", "seafood", "White",
         "Sauvignon Blanc,Pinot Grigio,Albariño,Chablis",
         "Crisp, light-bodied whites",
         "Light flavors need delicate wines"),

        ("fish", "seafood", "White",
         "Sauvignon Blanc,Pinot Grigio,Albariño,Chablis",
         "Crisp, light-bodied whites",
         "Light flavors need delicate wines"),

        ("shellfish", "seafood", "White,Sparkling",
         "Champagne,Chablis,Muscadet,Albariño",
         "High acidity, mineral whites",
         "Acidity and minerality complement briny shellfish"),

        # Italian
        ("pasta", "italian", "Red,White",
         "Chianti,Sangiovese,Pinot Grigio,Barbera",
         "Medium-bodied Italian wines",
         "Match wine origin with food origin"),

        ("pizza", "italian", "Red",
         "Chianti,Sangiovese,Barbera,Primitivo",
         "Medium-bodied Italian reds",
         "Acidity cuts through tomato sauce and cheese"),

        ("risotto", "italian", "White",
         "Pinot Grigio,Soave,Gavi,Chardonnay",
         "Creamy whites with good acidity",
         "Match richness, acidity balances creaminess"),

        # Cheese
        ("soft cheese", "cheese", "White,Sparkling",
         "Champagne,Sauvignon Blanc,Chardonnay",
         "Crisp whites or sparkling",
         "Acidity cuts through creamy texture"),

        ("hard cheese", "cheese", "Red,White",
         "Cabernet Sauvignon,Chardonnay,Rioja",
         "Full-bodied wines",
         "Strong flavors need bold wines"),

        ("blue cheese", "cheese", "Dessert,White",
         "Sauternes,Port,Riesling",
         "Sweet wines",
         "Sweetness balances saltiness and pungency"),

        ("cheese", "cheese", "Red,White",
         "Chardonnay,Pinot Noir,Cabernet Sauvignon",
         "Depends on cheese type",
         "Match intensity of wine to cheese"),

        # Other
        ("curry", "other", "White",
         "Riesling,Gewürztraminer,Chenin Blanc",
         "Off-dry aromatic whites",
         "Sweetness balances spice, aromatics complement flavors"),

        ("sushi", "other", "White,Sparkling",
         "Champagne,Sake,Riesling,Pinot Grigio",
         "Delicate, high-acidity wines",
         "Subtle flavors need delicate wines"),

        ("dessert", "other", "Dessert",
         "Port,Sauternes,Moscato,Ice Wine",
         "Sweet wines",
         "Wine should be sweeter than dessert"),
    ]

    now = datetime.now()

    for food_name, category, wine_types, varietals, characteristics, explanation in rules:
        try:
            cursor.execute("""
                INSERT INTO food_pairing_rules 
                (food_name, category, wine_types, varietals, characteristics, pairing_explanation, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (food_name, category, wine_types, varietals, characteristics, explanation, now, now))
        except sqlite3.IntegrityError:
            # Rule already exists, skip
            print(f"  - Skipped existing rule: {food_name}")
            continue

    conn.commit()
    count = cursor.execute("SELECT COUNT(*) FROM food_pairing_rules").fetchone()[0]
    print(f"✓ Inserted pairing rules (total: {count})")


def run_migration(db_path: str):
    """Run the migration."""
    print(f"Running migration on database: {db_path}")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    try:
        create_food_pairing_rules_table(conn)
        insert_pairing_rules(conn)
        print("✓ Migration completed successfully")
    except Exception as e:
        conn.rollback()
        print(f"✗ Migration failed: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    import sys

    # Add project root to path
    sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

    from src.utils import get_default_db_path

    # Use the same method as the rest of the application
    db_path = get_default_db_path()
    run_migration(str(db_path))

