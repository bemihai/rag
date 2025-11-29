"""Vivino CSV importer for wine cellar database."""
import csv
from pathlib import Path

from src.database.models import Wine, Bottle, Tasting
from src.database.repository import (
    ProducerRepository, RegionRepository, WineRepository, BottleRepository, TastingRepository
)
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
        self.tasting_repository = TastingRepository(self.db_path)

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
                        except (ValueError, TypeError):
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
            self.wine_repository.update(wine_import)
            self.stats["wines_updated"] += 1
        elif duplicates := self.wine_repository.find_duplicates(
            wine_import.wine_name,
            data["row"]["Winery"],
            wine_import.wine_type,
            wine_import.vintage,
        ):
            self.stats["wines_skipped"] += 1
            logger.debug(f"Found duplicate wines for {wine_import.wine_name} ({wine_import.vintage}): {duplicates}")
            return
        else:
            wine_id = self.wine_repository.create(wine_import)
            self.stats['wines_imported'] += 1

        # Create or update tasting record
        tasting_id = self._create_or_update_tasting(data, wine_id)

        # Create bottle record (quantity = 1 for full_wine_list as it tracks activity not inventory)
        bottle = Bottle(
            wine_id=wine_id,
            tasting_id=tasting_id,
            source="vivino",
            external_bottle_id=wine_import.external_id,
            quantity=1,
            status="consumed",
            consumed_date=self._get_last_tasted_date(data) or parse_date("2010-01-01"),
        )

        if existing_bottle := self.bottle_repository.get_by_wine_and_external_id(wine_id, bottle.external_bottle_id):
            bottle.id = existing_bottle.id
            self.bottle_repository.update(bottle)
            self.stats["bottles_updated"] += 1
        else:
            self.bottle_repository.create(bottle)
            self.stats["bottles_imported"] += 1

    def _create_wine_object_from_data(self, data: dict) -> Wine | None:
        """Create Wine object from aggregated data (without tasting fields)."""
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
        region_id = self.region_repository.get_or_create(region, country)  # primary_name, country

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
        )

    def _create_or_update_tasting(self, data: dict, wine_id: int) -> int | None:
        """
        Create or update tasting record from Vivino data.

        Args:
            data: Aggregated wine data with ratings and reviews
            wine_id: Wine ID to associate tasting with

        Returns:
            Tasting ID if created/updated, None otherwise
        """
        row = data["row"]

        # Extract personal rating (convert from 0-5 to 0-100 scale)
        personal_rating = normalize_rating(max(data["ratings"]), "vivino") if data["ratings"] else None

        # Merge tasting notes
        tasting_notes = '\n\n'.join(data["reviews"]) if data["reviews"] else None

        # Get last tasted date
        last_tasted = self._get_last_tasted_date(data)

        # Extract community rating (convert from 0-5 to 0-100 scale if enough votes)
        community_rating = None
        if row.get("Average rating"):
            try:
                avg_rating = float(row["Average rating"])
                # Only use community rating if there are enough votes (placeholder logic)
                community_rating = normalize_rating(avg_rating, "vivino")
            except (ValueError, TypeError):
                pass

        # Check if we have any tasting data
        if not (personal_rating or tasting_notes or community_rating):
            return None

        # Get existing tasting or create new one
        existing_tasting = self.tasting_repository.get_latest_by_wine(wine_id)

        if existing_tasting:
            # Update existing tasting
            updated = False

            # Merge ratings (keep highest personal rating)
            if personal_rating and (not existing_tasting.personal_rating or personal_rating > existing_tasting.personal_rating):
                existing_tasting.personal_rating = personal_rating
                updated = True

            # Merge tasting notes
            if tasting_notes:
                if existing_tasting.tasting_notes:
                    combined_notes = '\n\n'.join([existing_tasting.tasting_notes, tasting_notes])
                    if combined_notes != existing_tasting.tasting_notes:
                        existing_tasting.tasting_notes = combined_notes
                        updated = True
                else:
                    existing_tasting.tasting_notes = tasting_notes
                    updated = True

            # Update community rating (always use latest)
            if community_rating and community_rating != existing_tasting.community_rating:
                existing_tasting.community_rating = community_rating
                updated = True

            # Update tasting date (keep most recent)
            if last_tasted and (not existing_tasting.last_tasted_date or last_tasted > existing_tasting.last_tasted_date):
                existing_tasting.last_tasted_date = last_tasted
                updated = True

            if updated:
                self.tasting_repository.update(existing_tasting)
                logger.debug(f"Updated tasting for wine {wine_id}")

            return existing_tasting.id
        else:
            # Create new tasting
            tasting = Tasting(
                wine_id=wine_id,
                personal_rating=personal_rating,
                tasting_notes=tasting_notes,
                community_rating=community_rating,
                last_tasted_date=last_tasted,
                do_like=True if personal_rating and personal_rating >= 85 else False,
                is_defective=False
            )
            tasting_id = self.tasting_repository.create(tasting)
            logger.debug(f"Created tasting for wine {wine_id}")
            return tasting_id

    def _get_last_tasted_date(self, data: dict):
        """Extract the most recent tasting date from scan dates."""
        scan_dates = [parse_date(scan.get("Scan date")) for scan in data["scans"] if scan.get("Scan date")]
        return max(scan_dates) if scan_dates else None




