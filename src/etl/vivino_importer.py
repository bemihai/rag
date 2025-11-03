"""Vivino CSV importer for wine cellar database."""
import csv
import sqlite3
from difflib import SequenceMatcher
from pathlib import Path

from src.database.db import get_db_connection
from src.etl.utils import (
    normalize_wine_type,
    clean_text,
    parse_date,
    parse_vintage,
    parse_drinking_window,
    normalize_rating,
    generate_external_id,
    parse_country
)
from src.utils import get_project_root
from src.utils.logger import logger


class VivinoImporter:
    """Import wine data from Vivino CSV exports."""

    def __init__(self, db_path: str = 'data/wine_cellar.db'):
        """
        Initialize Vivino importer.

        Args:
            db_path: Path to SQLite database
        """
        self.db_path = get_project_root() / db_path
        self.stats = {
            'wines_processed': 0,
            'wines_imported': 0,
            'wines_updated': 0,
            'wines_skipped': 0,
            'bottles_imported': 0,
            'producers_created': 0,
            'regions_created': 0,
            'errors': []
        }

    def import_cellar_csv(self, csv_path: str | Path) -> dict:
        """
        Import wines from Vivino cellar.csv export.

        Args:
            csv_path: Path to cellar.csv file

        Returns:
            Import statistics dictionary
        """
        logger.info(f"Starting import from {csv_path}")

        try:
            with open(csv_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)

                for row in reader:
                    self.stats["wines_processed"] += 1

                    try:
                        self._process_cellar_row(row)
                    except Exception as e:
                        error_msg = f"Error processing row {self.stats['wines_processed']}: {e}"
                        logger.error(error_msg)
                        self.stats["errors"].append(error_msg)

            logger.info(f"Import completed: {self.stats}")
            return self.stats

        except Exception as e:
            logger.error(f"Failed to import from {csv_path}: {e}")
            self.stats["errors"].append(str(e))
            return self.stats


    def import_full_wine_list_csv(self, csv_path: str | Path) -> dict:
        """
        Import wines from Vivino full_wine_list.csv export.
        This includes tasting notes and ratings.

        Args:
            csv_path: Path to full_wine_list.csv file

        Returns:
            Import statistics dictionary
        """
        logger.info(f"Starting import from {csv_path}")

        try:
            # Group rows by wine (same wine may appear multiple times with different scans)
            wines_data = {}

            with open(csv_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)

                for row in reader:
                    # Generate unique key for grouping
                    winery = clean_text(row.get("Winery"))
                    wine_name = clean_text(row.get("Wine name"))
                    vintage = parse_vintage(row.get("Vintage"))

                    if not (winery and wine_name):
                        continue

                    key = (winery, wine_name, vintage)

                    if key not in wines_data:
                        wines_data[key] = {
                            "row": row,
                            "scans": [],
                            "ratings": [],
                            "reviews": []
                        }

                    wines_data[key]["scans"].append(row)

                    if row.get("Your rating"):
                        try:
                            rating = float(row["Your rating"])
                            wines_data[key]["ratings"].append(rating)
                        except:
                            pass

                    review = clean_text(row.get("Your review") or row.get("Personal Note"))
                    if review:
                        wines_data[key]["reviews"].append(review)

            # Process each unique wine
            for key, data in wines_data.items():
                self.stats["wines_processed"] += 1

                try:
                    self._process_full_wine_list_data(data)
                except Exception as e:
                    error_msg = f"Error processing wine {key}: {e}"
                    logger.error(error_msg)
                    self.stats["errors"].append(error_msg)

            logger.info("Import completed.")
            return self.stats

        except Exception as e:
            logger.error(f"Failed to import from {csv_path}: {e}")
            self.stats['errors'].append(str(e))
            return self.stats


    def _process_cellar_row(self, row: dict):
        """Process a single row from cellar.csv."""
        with get_db_connection(self.db_path) as conn:
            cursor = conn.cursor()

            winery = clean_text(row['Winery'])
            wine_name = clean_text(row['Wine name'])
            vintage = parse_vintage(row.get('Vintage'))
            country = parse_country(row['Country'])
            region = clean_text(row['Region'])

            # skip if essential data is missing
            if not (winery and wine_name and country):
                self.stats["wines_skipped"] += 1
                return

            producer_id = self._get_or_create_producer(cursor, winery, country, region)
            region_id = self._get_or_create_region(cursor, country, region) if region else None
            external_id = generate_external_id(winery, wine_name, vintage)

            cursor.execute(
                "SELECT id FROM wines WHERE source = ? AND external_id = ?",
                ('vivino', external_id)
            )
            existing = cursor.fetchone()

            if existing:
                wine_id = existing["id"]
                self._update_wine(cursor, wine_id, row)
                self.stats["wines_updated"] += 1
            else:
                wine_id = self._insert_wine(cursor, row, producer_id, region_id, external_id)
                self.stats["wines_imported"] += 1

            # Create bottle record
            quantity = int(row.get("User cellar count", 1))
            self._insert_bottle(cursor, wine_id, external_id, "in_cellar", quantity)
            self.stats["bottles_imported"] += 1

            conn.commit()

    def _process_full_wine_list_data(self, data: dict):
        """Process aggregated data from full_wine_list.csv."""
        row = data["row"]

        with get_db_connection(self.db_path) as conn:
            cursor = conn.cursor()

            winery = clean_text(row["Winery"])
            wine_name = clean_text(row["Wine name"])
            vintage = parse_vintage(row.get("Vintage"))
            country = parse_country(row["Country"])
            region = clean_text(row["Region"])

            if not (winery and wine_name and country):
                self.stats["wines_skipped"] += 1
                return

            producer_id = self._get_or_create_producer(cursor, winery, country, region)
            region_id = self._get_or_create_region(cursor, country, region)
            external_id = generate_external_id(winery, wine_name, vintage)

            cursor.execute(
                "SELECT id FROM wines WHERE source = ? AND external_id = ?",
                ("vivino", external_id)
            )
            existing = cursor.fetchone()

            # Calculate best rating and merge reviews
            best_rating = max(data["ratings"]) if data["ratings"] else None
            merged_reviews = '\n\n'.join(data["reviews"]) if data["reviews"] else None

            # Get most recent scan date
            scan_dates = [parse_date(scan.get("Scan date")) for scan in data["scans"] if scan.get("Scan date")]
            last_tasted = max(scan_dates) if scan_dates else None

            if existing:
                wine_id = existing["id"]
                self._update_wine(cursor, wine_id, row, best_rating, merged_reviews, last_tasted)
                self.stats["wines_updated"] += 1
            else:
                wine_id = self._insert_wine(
                    cursor, row, producer_id, region_id, external_id,
                    best_rating, merged_reviews, last_tasted
                )
                self.stats['wines_imported'] += 1

            # Create bottle record (quantity = 1 for full_wine_list as it tracks activity not inventory)
            consumed_date = last_tasted or "2010-01-01"
            self._insert_bottle(cursor, wine_id, external_id, "consumed", quantity=1, consumed_date=consumed_date)
            self.stats["bottles_imported"] += 1

            conn.commit()


    def _get_or_create_producer(self, cursor, name: str, country: str, region: str | None) -> int:
        """Get existing producer or create new one."""
        # Exact matching on name and country
        cursor.execute("SELECT id FROM producers WHERE name = ? AND country = ?", (name, country))
        result = cursor.fetchone()
        if result:
            return result['id']

        # Create new producer
        try:
            cursor.execute(
                """INSERT INTO producers (name, country, region) 
                   VALUES (?, ?, ?)""",
                (name, country, region)
            )
        except sqlite3.IntegrityError as err:
            # Fuzzy matching on name and country
            cursor.execute("SELECT id, name, country FROM producers")
            all_producers = cursor.fetchall()
            target = f"{name} {country}".lower()

            for producer in all_producers:
                candidate = f"{producer['name']} {producer['country']}".lower()
                similarity = SequenceMatcher(None, target, candidate).ratio()

                if similarity >= 0.84:
                    logger.info(
                        f"Matched '{name}' ({country}) to existing producer '{producer['name']}' ({producer['country']}) "
                        f"with similarity {similarity:.2f}")
                    return producer['id']

            logger.error(f"Failed to create producer with name '{name}', country '{country}', region '{region}': {err}")

        self.stats["producers_created"] += 1
        return cursor.lastrowid


    def _get_or_create_region(self, cursor, country: str, region: str | None) -> int:
        """Get existing region or create new one."""
        cursor.execute(
            "SELECT id FROM regions WHERE name = ? AND country = ?",
            (region, country)
        )
        result = cursor.fetchone()

        if result:
            return result['id']

        # Create new region
        cursor.execute(
            """INSERT INTO regions (name, country) 
               VALUES (?, ?)""",
            (region, country)
        )
        self.stats["regions_created"] += 1
        return cursor.lastrowid


    @staticmethod
    def _insert_wine(
            cursor, row: dict, producer_id: int, region_id: int | None, external_id: int,
            personal_rating: float | None = None, tasting_notes: str | None = None, last_tasted_date: str | None = None
    ) -> int:
        """Insert new wine record with tasting data."""
        vintage = parse_vintage(row.get("Vintage"))
        wine_type = normalize_wine_type(row["Wine type"])
        drink_from, drink_to = parse_drinking_window(row.get("Drinking Window", ""))
        community_rating = float(row["Average rating"]) \
            if row.get("Average rating") and int(row.get("Wine ratings count", 0)) > 10 else None

        # Convert rating to 0-100 scale
        personal_rating = normalize_rating(personal_rating, "vivino") if personal_rating else None
        community_rating = normalize_rating(community_rating, "vivino") if community_rating else None

        cursor.execute(
            """INSERT INTO wines (
                source, external_id, wine_name, producer_id, vintage,
                wine_type, region_id, personal_rating, community_rating, 
                tasting_notes, last_tasted_date,
                drink_from_year, drink_to_year
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                "vivino",
                external_id,
                clean_text(row["Wine name"]),
                producer_id,
                vintage,
                wine_type,
                region_id,
                personal_rating,
                community_rating,
                tasting_notes,
                last_tasted_date,
                drink_from,
                drink_to
            )
        )

        return cursor.lastrowid


    @staticmethod
    def _update_wine(
            cursor, wine_id: int, row: dict, personal_rating: float | None = None,
            tasting_notes: str | None = None, last_tasted_date: str | None = None
    ):
        """Update existing wine with tasting data."""
        normalized_rating = normalize_rating(personal_rating, "vivino") if personal_rating else None
        cursor.execute(
            "SELECT personal_rating, tasting_notes FROM wines WHERE id = ?",
            (wine_id,)
        )
        current = cursor.fetchone()

        # Merge tasting notes if both exist
        merged_notes = tasting_notes
        if current and current["tasting_notes"] and tasting_notes:
            merged_notes = f"{current['tasting_notes']}\n\n{tasting_notes}"
        elif current and current["tasting_notes"]:
            merged_notes = current["tasting_notes"]

        # Use higher rating
        final_rating = normalized_rating
        if current and current["personal_rating"]:
            if normalized_rating:
                final_rating = max(current["personal_rating"], normalized_rating)
            else:
                final_rating = current["personal_rating"]

        community_rating  = float(row["Average rating"]) \
            if row.get("Average rating") and int(row.get("Wine ratings count", 0)) > 10 else None
        community_rating = normalize_rating(community_rating, "vivino") if community_rating else None

        cursor.execute(
            """
            UPDATE wines SET
                personal_rating = ?,
                tasting_notes = ?,
                last_tasted_date = COALESCE(?, last_tasted_date),
                community_rating = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                final_rating,
                merged_notes,
                last_tasted_date,
                community_rating,
                wine_id
            )
        )


    @staticmethod
    def _insert_bottle(
            cursor, wine_id: int, external_id: int, status: str,
            quantity: int = 1, consumed_date: str | None = None
    ):
        """Insert bottle record for wine."""
        if status == "consumed" and not consumed_date:
            raise ValueError("consumed_date must be provided for consumed bottles")

        cursor.execute(
            """INSERT INTO bottles (
                wine_id, source, external_bottle_id, quantity, status, consumed_date
            ) VALUES (?, ?, ?, ?, ?, ?)""",
            (wine_id, "vivino", external_id, quantity, status, consumed_date)
        )

    def reset_stats(self):
        """Reset import statistics."""
        self.stats = {
            'wines_processed': 0,
            'wines_imported': 0,
            'wines_updated': 0,
            'wines_skipped': 0,
            'bottles_imported': 0,
            'producers_created': 0,
            'regions_created': 0,
            'errors': []
        }

