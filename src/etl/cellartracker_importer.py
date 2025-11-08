"""
CellarTracker API importer for wine cellar database.
"""
from typing import Dict, List, Optional
from datetime import datetime, date
from cellartracker import cellartracker

from src.database import Wine, Bottle
from src.database.repository import (
    SyncLogRepository, WineRepository, BottleRepository, ProducerRepository, RegionRepository
)
from src.etl.utils import (
    normalize_wine_type,
    clean_text,
    parse_date,
    parse_vintage,
    parse_drinking_window, parse_country
)
from src.utils import get_default_db_path
from src.utils.logger import logger


class CellarTrackerImporter:
    """Import wine data from CellarTracker API."""

    def __init__(self, username: str, password: str, db_path: str = 'data/wine_cellar.db'):
        """
        Initialize CellarTracker importer.

        Args:
            username: CellarTracker username
            password: CellarTracker password
            db_path: Path to SQLite database
        """
        self.client = cellartracker.CellarTracker(username, password)
        self.db_path = db_path or get_default_db_path()
        self.stats = {
            'wines_processed': 0,
            'wines_imported': 0,
            'wines_updated': 0,
            'wines_skipped': 0,
            'bottles_processed': 0,
            'bottles_imported': 0,
            'bottles_updated': 0,
            'producers_created': 0,
            'regions_created': 0,
            'notes_processed': 0,
            'errors': []
        }
        self.sync_log_repo = SyncLogRepository(self.db_path)
        self.wine_repo = WineRepository(self.db_path)
        self.bottle_repo = BottleRepository(self.db_path)
        self.producer_repo = ProducerRepository(self.db_path)
        self.region_repo = RegionRepository(self.db_path)

    def import_all(self) -> Dict:
        """
        Import all data from CellarTracker following recommended strategy.

        Import Order:
        1. inventory.json - Build Wine catalog + current Bottle inventory
        2. bottles.json - Complete bottle lifecycle (adds drinking windows to Wines)
        3. notes.json - Enhance Wines with ratings & tasting notes

        Returns:
            Import statistics dictionary
        """
        logger.info("Starting full CellarTracker import")
        sync_id = self.sync_log_repo.start_sync_log("full")

        try:
            logger.info("Step 1/3: Fetching and importing inventory...")
            inventory = self.client.get_inventory()
            self._process_inventory(inventory)

            logger.info("Step 2/3: Fetching and importing bottles (complete history)...")
            bottles = self.client.get_bottles()
            self._process_bottles(bottles)

            logger.info("Step 3/3: Fetching and importing tasting notes...")
            notes = self.client.get_notes()
            self._process_notes(notes)

            self.sync_log_repo.complete_sync_log(sync_id, self.stats, status="success")
            logger.info(f"✅ Import completed successfully!")

        except Exception as e:
            error_msg = f"Import failed: {e}"
            logger.error(error_msg)
            self.stats["errors"].append(error_msg)
            self.sync_log_repo.complete_sync_log(sync_id, self.stats, "failed", error_msg)

        return self.stats


    def _process_inventory(self, inventory: List[Dict]):
        """
        Process inventory.json - Current cellar snapshot.

        Creates:
        - Wine entities with catalog info (name, producer, vintage, type, etc.)
        - Bottle entities for current cellar (location, purchase info, status='in_cellar')
        """
        logger.info(f"Processing {len(inventory)} bottles from inventory (current bottles in cellar)")

        for record in inventory:
            try:
                # Process Wine
                self.stats["wines_processed"] += 1
                iwine = record.get("iWine")
                wine = self._get_wine_object_from_inventory_record(record)
                if existing := self.wine_repo.get_by_external_id(iwine):
                    wine.id = existing.id
                    wine_id = existing.id
                    self.wine_repo.update(wine)
                    self.stats["wines_updated"] += 1
                    logger.debug(f"Updated wine: {wine.wine_name} ({wine.vintage})")
                else:
                    wine_id = self.wine_repo.create(wine)
                    self.stats["wines_imported"] += 1
                    logger.debug(f"Imported wine: {wine.wine_name} ({wine.vintage})")

                # Process Bottle
                self.stats["bottles_processed"] += 1
                bottle = self._get_bottle_object_from_inventory_record(record, wine_id)
                barcode = record.get("Barcode")
                if existing := self.bottle_repo.get_by_wine_and_external_id(wine_id, barcode):
                    bottle.id = existing.id
                    self.bottle_repo.update(bottle)
                    self.stats["bottles_updated"] += 1
                    logger.debug(f"Updated bottle: {barcode}")
                else:
                    bottle.quantity = 1
                    bottle.status = "in_cellar"
                    self.bottle_repo.create(bottle)

                    self.stats["bottles_imported"] += 1
                    logger.debug(f"Imported bottle: {barcode}")
            except Exception as e:
                error_msg = f"Error processing inventory record {record.get('iWine')}/{record.get('Barcode')}: {e}"
                logger.error(error_msg)
                self.stats["errors"].append(error_msg)


    def _process_bottles(self, bottles: List[Dict]):
        """
        Process bottles.json - Complete bottle lifecycle.
        Updates:
        - Wine: drink_from_year, drink_to_year (drinking window)
        - Bottle: Creates or updates complete lifecycle (active + consumed + gifted)
        """
        logger.info(f"Processing {len(bottles)} bottles from complete lifecycle")

        for record in bottles:
            self.stats["bottles_processed"] += 1

            try:
                wine_id = self._find_and_update_wine_from_bottles(record)
                bottle = self._get_bottle_object_from_bottles_record(record, wine_id)

                barcode = record.get("Barcode")
                if existing := self.bottle_repo.get_by_wine_and_external_id(wine_id, barcode):
                    bottle.id = existing.id
                    self.bottle_repo.update(bottle)
                    self.stats["bottles_updated"] += 1
                    logger.debug(f"Updated bottle from bottles: {barcode}")
                else:
                    self.bottle_repo.create(bottle)
                    self.stats["bottles_imported"] += 1
                    logger.debug(f"Imported bottle from bottles: {barcode}")

            except Exception as e:
                error_msg = f"Error processing bottle {record.get('Barcode')}: {e}"
                logger.error(error_msg)
                self.stats["errors"].append(error_msg)


    def _process_notes(self, notes: List[Dict]):
        """
        Process notes.json - Tasting notes and ratings.
        Updates Wine with:
        - personal_rating (0-100 scale, keep highest)
        - tasting_notes (merge with date stamps)
        - last_tasted_date (keep most recent)
        """
        logger.info(f"Processing {len(notes)} tasting notes")

        for record in notes:
            self.stats["notes_processed"] += 1
            try:
                iwine = record.get("iWine")
                wine = self.wine_repo.get_by_external_id(iwine)

                if not wine:
                    logger.warning(f"Wine {iwine} not found for note update")
                    continue

                existing_rating = wine.personal_rating
                existing_notes = wine.tasting_notes or ""
                last_tasted = wine.last_tasted_date

                wine.personal_rating = self._merge_ratings(existing_rating, record)
                wine.tasting_notes = self._merge_tasting_notes(existing_notes, record)

                should_update_date, tasting_date = self._update_tasting_date(last_tasted, record)
                if should_update_date and tasting_date:
                    wine.last_tasted_date = tasting_date

                self.wine_repo.update(wine)
                logger.debug(f"Updated wine {iwine} with tasting note and rating)")

            except Exception as e:
                error_msg = f"Error processing note {record.get('iNote')}: {e}"
                logger.error(error_msg)
                self.stats['errors'].append(error_msg)


    def _get_wine_object_from_inventory_record(self, record: Dict) -> Wine:
        """
        Create a Wine object from an inventory record.
        """
        iwine = record.get("iWine")
        wine_name = clean_text(record.get("Wine", ""))
        vintage = parse_vintage(record.get("Vintage"))
        wine_type = normalize_wine_type(record.get("Type", ""))

        producer_id = self.producer_repo.get_or_create(
            clean_text(record.get("Producer", "")),
            parse_country(record.get("Country")),
            clean_text(record.get("Locale")),
        )

        region_id = self.region_repo.get_or_create(
            clean_text(record.get("Region")),
            parse_country(record.get("Country")),
            clean_text(record.get("SubRegion") or record.get("Appellation")),
        )

        return Wine(
            source="cellar_tracker",
            external_id=iwine,
            wine_name=wine_name,
            producer_id=producer_id,
            vintage=vintage,
            wine_type=wine_type,
            varietal=clean_text(record.get("Varietal")),
            designation=clean_text(record.get("Designation")),
            region_id=region_id,
            appellation=clean_text(record.get("Appellation")),
            bottle_size=record.get("Size", "750ml")
        )


    def _find_and_update_wine_from_bottles(self, record: Dict) -> Optional[int]:
        """
        Find Wine and update drinking window from bottles.json record.
        """
        iwine = record.get("iWine")
        wine = self.wine_repo.get_by_external_id(iwine)

        if not wine:
            wine = self._get_wine_object_from_inventory_record(record)
            wine.id = self.wine_repo.create(wine)
            self.stats["wines_processed"] += 1
            self.stats["wines_imported"] += 1

        begin_consume = record.get("BeginConsume")
        end_consume = record.get("EndConsume")
        if begin_consume or end_consume:
            drink_from_year, drink_to_year = parse_drinking_window(begin_consume, end_consume)
            wine.drink_from_year = drink_from_year or wine.drink_from_year
            wine.drink_to_year = drink_to_year or wine.drink_to_year
            self.wine_repo.update(wine)
            self.wine_repo.update(wine)

        return wine.id


    @staticmethod
    def _get_bottle_object_from_inventory_record(record: Dict, wine_id: int) -> Bottle:
        """
        Create a Bottle object from an inventory record.
        """
        price = None
        price_str = record.get("Price")
        if price_str:
            try:
                price = float(price_str)
            except (ValueError, TypeError):
                pass

        return Bottle(
            wine_id=wine_id,
            source="cellar_tracker",
            external_bottle_id=record.get("Barcode"),
            location=clean_text(record.get("Location")),
            bin=clean_text(record.get("Bin")),
            purchase_date=parse_date(record.get("PurchaseDate")),
            bottle_note=clean_text(record.get("BottleNote")),
            purchase_price=price,
            currency=record.get("Currency", "RON"),
            store_name=clean_text(record.get("StoreName"))
        )


    def _get_bottle_object_from_bottles_record(self, record: Dict, wine_id: int) -> Bottle:
        """
        Create or update Bottle from bottles.json record.
        """
        barcode = record.get("Barcode")
        quantity = int(record.get("Quantity", 1))

        bottle_state = record.get("BottleState", "0")
        consumption_date = record.get("ConsumptionDate")
        if bottle_state == "0" and not consumption_date:
            status = "in_cellar"
        elif consumption_date:
            short_type = record.get("ShortType", "").lower()
            if "gift" in short_type:
                status = "gifted"
            elif "spoil" in short_type or "dump" in short_type:
                status = "lost"
            else:
                status = "consumed"
        else:
            status = "in_cellar"

        purchase_date = parse_date(record.get("PurchaseDate"))
        consumed_date = parse_date(consumption_date) if consumption_date else None

        price = None
        price_str = record.get("BottleCost")
        if price_str:
            try:
                price = float(price_str)
            except (ValueError, TypeError):
                pass

        purchase_note = clean_text(record.get("PurchaseNote"))
        consumption_note = clean_text(record.get("ConsumptionNote"))
        bottle_note = self._merge_bottle_notes(purchase_note, consumption_note)

        return Bottle(
            wine_id=wine_id,
            source="cellar_tracker",
            external_bottle_id=barcode,
            quantity=quantity,
            status=status,
            location=clean_text(record.get("Location")),
            bin=clean_text(record.get("Bin")),
            purchase_date=purchase_date,
            purchase_price=price,
            currency=record.get("BottleCostCurrency", "RON"),
            store_name=clean_text(record.get("Store")),
            consumed_date=consumed_date,
            bottle_note=bottle_note
        )


    @staticmethod
    def _merge_bottle_notes(purchase_note: Optional[str], consumption_note: Optional[str]) -> Optional[str]:
        """Merge purchase and consumption notes."""
        if purchase_note and consumption_note:
            return f"{purchase_note}\n\nConsumed: {consumption_note}"
        return purchase_note or consumption_note


    @staticmethod
    def _merge_ratings(existing_rating: int | None, record: Dict) -> int | None:
        """Merge existing rating with new rating, keeping the highest."""
        rating = existing_rating
        rating_str = record.get("Rating")
        if rating_str:
            try:
                new_rating = int(rating_str)
                if existing_rating is None or new_rating > existing_rating:
                    rating = new_rating
            except (ValueError, TypeError):
                pass

        return rating


    @staticmethod
    def _merge_tasting_notes(existing_notes: str, record: Dict) -> str:
        """Merge existing tasting notes with new notes, adding date stamps."""
        tasting_date = parse_date(record.get("TastingDate"))
        note_text = clean_text(record.get("TastingNotes"))
        if note_text:
            if existing_notes:
                date_str = tasting_date or datetime.now().strftime('%Y-%m-%d')
                combined_notes = f"{existing_notes}\n\n[{date_str}] {note_text}"
            else:
                date_str = tasting_date or datetime.now().strftime('%Y-%m-%d')
                combined_notes = f"[{date_str}] {note_text}"
        else:
            combined_notes = existing_notes

        return combined_notes


    @staticmethod
    def _update_tasting_date(last_tasted: str | date, record: Dict) -> tuple[bool, date | None]:
        should_update_date = True
        tasting_date = parse_date(record.get("TastingDate"))
        if last_tasted and tasting_date:
            try:
                if isinstance(last_tasted, str):
                    last_tasted_obj = datetime.strptime(last_tasted, '%Y-%m-%d').date()
                else:
                    last_tasted_obj = last_tasted

                if isinstance(tasting_date, str):
                    tasting_date_obj = datetime.strptime(tasting_date, '%Y-%m-%d').date()
                else:
                    tasting_date_obj = tasting_date

                should_update_date = tasting_date_obj >= last_tasted_obj
            except:
                pass

        return should_update_date, tasting_date





