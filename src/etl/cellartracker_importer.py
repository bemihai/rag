"""
CellarTracker API importer for wine cellar database.
"""
from typing import Dict, List, Optional
from datetime import datetime
from cellartracker import cellartracker

from src.database import Wine, Bottle, Tasting
from src.database.repository import (
    SyncLogRepository, WineRepository, BottleRepository, ProducerRepository, RegionRepository, TastingRepository
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
        self.tasting_repo = TastingRepository(self.db_path)

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
            available = self.client.get_availability()
            self._process_inventory(inventory)
            self._process_availability(available)

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

        Note: Tasting data will be created separately from notes.json processing
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

                # Process Bottle (without tasting link - will be added from notes processing)
                self.stats["bottles_processed"] += 1
                bottle = self._get_bottle_object_from_inventory_record(record, wine_id, None)
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


    def _process_availability(self, available: List[Dict]):
        """
        Process availability data - Updates wine catalog with drinking index scores.

        Updates Wine entities with:
        - drink_index (availability score from Available column, converted to 0-100 scale)
        """
        logger.info(f"Processing {len(available)} wines from availability data")

        for record in available:
            try:
                iwine = record.get("iWine")
                wine = self.wine_repo.get_by_external_id(iwine)

                if not wine:
                    logger.debug(f"Wine {iwine} not found in availability processing, skipping")
                    continue

                # Update drink_index (availability score)
                available_score = record.get("Available")
                if available_score:
                    try:
                        # Convert decimal score to 0-100 scale
                        drink_index = int(float(available_score) * 100)
                        if drink_index != wine.drink_index:
                            wine.drink_index = drink_index
                            self.wine_repo.update(wine)
                            self.stats["wines_updated"] += 1
                            logger.debug(f"Updated drink_index for wine {iwine}: {drink_index}")
                    except (ValueError, TypeError):
                        logger.warning(f"Could not parse available score '{available_score}' for wine {iwine}")

            except Exception as e:
                error_msg = f"Error processing availability record for wine {record.get('iWine')}: {e}"
                logger.error(error_msg)
                self.stats["errors"].append(error_msg)


    def _process_bottles(self, bottles: List[Dict]):
        """
        Process bottles.json - Complete bottle lifecycle.

        Creates/Updates:
        - Bottle: Complete lifecycle (in_cellar, consumed, gifted, lost)

        Note: Tasting data will be created separately from notes.json processing
        """
        logger.info(f"Processing {len(bottles)} bottles from complete lifecycle")

        for record in bottles:
            self.stats["bottles_processed"] += 1

            try:
                iwine = record.get("iWine")
                wine = self.wine_repo.get_by_external_id(iwine)

                if not wine:
                    # Wine doesn't exist - create it
                    wine = self._get_wine_object_from_inventory_record(record)
                    wine_id = self.wine_repo.create(wine)
                    self.stats["wines_processed"] += 1
                    self.stats["wines_imported"] += 1
                    logger.debug(f"Created wine from bottles: {wine.wine_name}")
                else:
                    wine_id = wine.id

                # Create/update bottle (without tasting link - will be added from notes processing)
                bottle = self._get_bottle_object_from_bottles_record(record, wine_id, None)

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

        Creates/Updates Tasting entities with:
        - personal_rating (0-100 scale, keep highest)
        - tasting_notes (merge with date stamps)
        - last_tasted_date (keep most recent)
        - is_defective flag
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

                wine_id = wine.id

                # Get existing tasting or create new one
                existing_tasting = self.tasting_repo.get_latest_by_wine(wine_id)

                if existing_tasting:
                    # Update existing tasting
                    updated = False

                    # Merge ratings (keep highest)
                    new_rating = self._extract_rating_from_note(record)
                    if new_rating and (not existing_tasting.personal_rating or new_rating > existing_tasting.personal_rating):
                        existing_tasting.personal_rating = new_rating
                        updated = True

                    # Merge tasting notes (append with date stamp)
                    new_notes = self._extract_tasting_notes_from_note(record, existing_tasting.tasting_notes or "")
                    if new_notes != existing_tasting.tasting_notes:
                        existing_tasting.tasting_notes = new_notes
                        updated = True

                    # Update tasting date (keep most recent)
                    tasting_date_str = parse_date(record.get("TastingDate"))
                    if tasting_date_str:
                        from datetime import date as date_cls
                        tasting_date = date_cls.fromisoformat(tasting_date_str)
                        if not existing_tasting.last_tasted_date or tasting_date > existing_tasting.last_tasted_date:
                            existing_tasting.last_tasted_date = tasting_date
                            updated = True

                    # Update defective flag
                    is_defective = record.get("IsDefective", False)
                    if is_defective and not existing_tasting.is_defective:
                        existing_tasting.is_defective = True
                        updated = True

                    if updated:
                        self.tasting_repo.update(existing_tasting)
                        logger.debug(f"Updated tasting for wine {iwine}")
                else:
                    # Create new tasting
                    from datetime import date as date_cls
                    tasting_date_str = parse_date(record.get("TastingDate"))
                    tasting_date = date_cls.fromisoformat(tasting_date_str) if tasting_date_str else None

                    tasting = Tasting(
                        wine_id=wine_id,
                        personal_rating=self._extract_rating_from_note(record),
                        tasting_notes=self._extract_tasting_notes_from_note(record, ""),
                        last_tasted_date=tasting_date,
                        is_defective=record.get("IsDefective", False),
                        do_like=self._extract_do_like_from_note(record)
                    )
                    self.tasting_repo.create(tasting)
                    logger.debug(f"Created tasting for wine {iwine}")

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

        # Region: primary_name from "Region", secondary_name from "SubRegion" or "Appellation"
        region_primary = clean_text(record.get("Region"))
        region_secondary = clean_text(record.get("SubRegion")) or clean_text(record.get("Appellation"))

        region_id = self.region_repo.get_or_create(
            region_primary,
            parse_country(record.get("Country")),
            region_secondary,
        )

        # Parse community inventory data
        q_purchased = int(record.get("PurchasedCommunity", 0) or 0)
        q_quantity = int(record.get("QuantityCommunity", 0) or 0)
        q_consumed = int(record.get("ConsumedCommunity", 0) or 0)

        # Parse drinking window
        drink_from_year, drink_to_year = parse_drinking_window(
            record.get("BeginConsume"),
            record.get("EndConsume")
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
            vineyard=clean_text(record.get("Vineyard")),
            bottle_size=record.get("Size", "750ml"),
            drink_from_year=drink_from_year,
            drink_to_year=drink_to_year,
            q_purchased=q_purchased,
            q_quantity=q_quantity,
            q_consumed=q_consumed
        )

    @staticmethod
    def _get_bottle_object_from_inventory_record(record: Dict, wine_id: int, tasting_id: Optional[int] = None) -> Bottle:
        """
        Create a Bottle object from an inventory record.

        Args:
            record: Inventory CSV record
            wine_id: Wine ID
            tasting_id: Optional tasting ID to link to this bottle
        """
        # Parse purchase price
        purchase_price = None
        price_str = record.get("Price")
        if price_str:
            try:
                purchase_price = float(price_str)
            except (ValueError, TypeError):
                logger.warning(f"Could not parse price '{price_str}' in record: {record.get('Barcode')}")

        # Parse valuation price (current market value)
        valuation_price = None
        valuation_str = record.get("Valuation")
        if valuation_str:
            try:
                valuation_price = float(valuation_str)
            except (ValueError, TypeError):
                logger.warning(f"Could not parse valuation '{valuation_str}' in record: {record.get('Barcode')}")

        return Bottle(
            wine_id=wine_id,
            tasting_id=tasting_id,
            source="cellar_tracker",
            external_bottle_id=record.get("Barcode"),
            location=clean_text(record.get("Location")),
            bin=clean_text(record.get("Bin")),
            purchase_date=parse_date(record.get("PurchaseDate")),
            bottle_note=clean_text(record.get("BottleNote")),
            purchase_price=purchase_price,
            valuation_price=valuation_price,
            currency=record.get("Currency", "RON"),
            store_name=clean_text(record.get("StoreName"))
        )


    def _get_bottle_object_from_bottles_record(self, record: Dict, wine_id: int, tasting_id: Optional[int] = None) -> Bottle:
        """
        Create or update Bottle from bottles.csv record.

        Args:
            record: Bottles CSV record
            wine_id: Wine ID
            tasting_id: Optional tasting ID to link to this bottle
        """
        barcode = record.get("Barcode")
        quantity = int(record.get("Quantity", 1))

        # Determine bottle status from BottleState and ConsumptionDate
        bottle_state = record.get("BottleState", "1")
        consumption_date = record.get("ConsumptionDate")

        if bottle_state == "1" or (bottle_state == "0" and not consumption_date):
            # BottleState=1 means in cellar, or BottleState=0 without consumption date
            status = "in_cellar"
        elif consumption_date:
            # Bottle was consumed - check consumption type
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

        # Parse purchase price (BottleCost)
        purchase_price = None
        price_str = record.get("BottleCost")
        if price_str:
            try:
                purchase_price = float(price_str)
            except (ValueError, TypeError):
                logger.warning(f"Could not parse bottle cost '{price_str}' for {barcode}")

        # Merge notes from PurchaseNote and ConsumptionNote
        purchase_note = clean_text(record.get("PurchaseNote"))
        consumption_note = clean_text(record.get("ConsumptionNote"))
        bottle_note = self._merge_bottle_notes(purchase_note, consumption_note)

        return Bottle(
            wine_id=wine_id,
            tasting_id=tasting_id,
            source="cellar_tracker",
            external_bottle_id=barcode,
            quantity=quantity,
            status=status,
            location=clean_text(record.get("Location")),
            bin=clean_text(record.get("Bin")),
            purchase_date=purchase_date,
            purchase_price=purchase_price,
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
    def _extract_rating_from_note(record: Dict) -> Optional[int]:
        """Extract personal rating from note record (0-100 scale)."""
        rating_str = record.get("Rating")
        if rating_str:
            try:
                return int(rating_str)
            except (ValueError, TypeError) as e:
                logger.warning(f"Failed to convert rating '{rating_str}' to int: {e}")
        return None

    @staticmethod
    def _extract_tasting_notes_from_note(record: Dict, existing_notes: str) -> str:
        """Extract and merge tasting notes from note record with date stamps."""
        tasting_date = parse_date(record.get("TastingDate"))
        note_text = clean_text(record.get("TastingNotes"))

        if note_text:
            # parse_date returns a string in YYYY-MM-DD format or None
            date_str = tasting_date if tasting_date else datetime.now().strftime('%Y-%m-%d')

            if existing_notes:
                return f"{existing_notes}\n\n[{date_str}] {note_text}"
            else:
                return f"[{date_str}] {note_text}"

        return existing_notes

    @staticmethod
    def _extract_do_like_from_note(record: Dict) -> bool:
        """Extract do_like flag from note record based on rating."""
        rating = CellarTrackerImporter._extract_rating_from_note(record)
        if rating:
            return rating >= 85
        return True  # Default to True if rating not available but note exists
