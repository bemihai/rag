"""Vivino CSV importer for wine cellar database."""
import csv
from pathlib import Path

from src.database.models import Wine, Bottle
from src.database.repository import ProducerRepository, RegionRepository, WineRepository, BottleRepository
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
from src.utils import get_default_db_path
from src.utils.logger import logger


class VivinoImporter:
    """Import wine data from Vivino CSV exports."""

    def __init__(self, db_path: str | None = None):
        """
        Initialize Vivino importer.

        Args:
            db_path: Path to SQLite database
        """
        self.db_path = db_path or get_default_db_path()
        self.producer_repository = ProducerRepository(self.db_path)
        self.region_repository = RegionRepository(self.db_path)
        self.wine_repository = WineRepository(self.db_path)
        self.bottle_repository = BottleRepository(self.db_path)

        self.stats = {
            'wines_processed': 0,
            'wines_imported': 0,
            'wines_updated': 0,
            'wines_skipped': 0,
            'bottles_imported': 0,
            'bottles_updated': 0,
            'producers_created': 0,
            'regions_created': 0,
            'errors': []
        }

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

    def _process_full_wine_list_data(self, data: dict):
        """Process aggregated data from full_wine_list.csv."""

        if not (wine_import := self._create_wine_object_from_data(data)):
            self.stats["wines_skipped"] += 1
            return

        # Check if wine already exists: if yes, update; if no, insert
        if wine_record := self.wine_repository.get_by_external_id(wine_import.external_id):
            wine_import.id = wine_record.id
            wine_id = wine_record.id

            # use the best personal rating
            wine_import.personal_rating = max(
                wine_record.personal_rating or 0,
                wine_import.personal_rating or 0
            ) or None

            # merge tasting notes
            wine_import.tasting_notes = '\n\n'.join(filter(None, [
                wine_record.tasting_notes,
                wine_import.tasting_notes
            ])) or None

            self.wine_repository.update(wine_import)
            self.stats["wines_updated"] += 1
        else:
            wine_id = self.wine_repository.create(wine_import)
            self.stats['wines_imported'] += 1

        # Create bottle record (quantity = 1 for full_wine_list as it tracks activity not inventory)
        bottle = Bottle(
            wine_id=wine_id,
            source="vivino",
            external_bottle_id=wine_import.external_id,
            quantity=1,
            status="consumed",
            consumed_date=wine_import.last_tasted_date or "2010-01-01",
        )

        if existing_bottle := self.bottle_repository.get_by_wine_and_external_id(wine_id, bottle.external_bottle_id):
            bottle.id = existing_bottle.id
            self.bottle_repository.update(bottle)
            self.stats["bottles_updated"] += 1
        else:
            self.bottle_repository.create(bottle)
            self.stats["bottles_imported"] += 1

    def _create_wine_object_from_data(self, data: dict) -> Wine | None:
        """Create Wine object from aggregated data."""
        row = data["row"]
        winery = clean_text(row["Winery"])
        wine_name = clean_text(row["Wine name"])
        country = parse_country(row["Country"])

        # Validate required fields and return None if missing
        if not (winery and wine_name and country):
            return None

        # Prepare fields for insertion/update
        vintage = parse_vintage(row.get("Vintage"))
        region = clean_text(row["Region"])
        wine_type = normalize_wine_type(row["Wine type"])
        drink_from, drink_to = parse_drinking_window(row.get("Drinking Window", ""))
        external_id = generate_external_id(winery, wine_name, vintage)
        producer_id = self.producer_repository.get_or_create(winery, country, region)
        region_id = self.region_repository.get_or_create(region, country)
        personal_rating = normalize_rating(max(data["ratings"]), "vivino") if data["ratings"] else None
        tasting_notes = '\n\n'.join(data["reviews"]) if data["reviews"] else None
        scan_dates = [parse_date(scan.get("Scan date")) for scan in data["scans"] if scan.get("Scan date")]
        last_tasted = max(scan_dates) if scan_dates else None
        community_rating = float(row["Average rating"]) \
            if row.get("Average rating") and int(row.get("Wine ratings count", 0)) > 10 else None
        community_rating = normalize_rating(community_rating, "vivino") if community_rating else None

        return Wine(
            source="vivino",
            wine_name=wine_name,
            wine_type=wine_type,
            vintage=vintage,
            drink_from_year=drink_from,
            drink_to_year=drink_to,
            external_id=external_id,
            producer_id=producer_id,
            region_id=region_id,
            personal_rating=personal_rating,
            tasting_notes=tasting_notes,
            last_tasted_date=last_tasted,
            community_rating=community_rating,
        )




