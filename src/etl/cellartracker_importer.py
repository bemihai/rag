"""
CellarTracker API importer for wine cellar database.
"""
from typing import Dict, List, Optional
from datetime import datetime
from cellartracker import cellartracker

from src.database.db import get_db_connection
from src.etl.utils import (
    normalize_wine_type,
    clean_text,
    parse_date,
    parse_vintage,
    parse_drinking_window
)
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
        self.db_path = db_path
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

        # Cache for producer and region IDs to avoid duplicate lookups
        self.producer_cache: Dict[str, int] = {}
        self.region_cache: Dict[tuple, int] = {}

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
        sync_id = self._start_sync_log('full')

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

            self._complete_sync_log(sync_id, 'success')
            logger.info(f"✅ Import completed successfully!")

        except Exception as e:
            error_msg = f"Import failed: {e}"
            logger.error(error_msg)
            self.stats['errors'].append(error_msg)
            self._complete_sync_log(sync_id, 'failed', error_msg)

        return self.stats


    def _process_inventory(self, inventory: List[Dict]):
        """
        Process inventory.json - Current cellar snapshot.

        Maps to: BOTH Wine + Bottle entities
        Priority: HIGH - This is the starting point

        Creates:
        - Wine entities with catalog info (name, producer, vintage, type, etc.)
        - Bottle entities for current cellar (location, purchase info, status='in_cellar')
        """
        logger.info(f"Processing {len(inventory)} bottles from inventory (current bottles in cellar)")

        with get_db_connection(self.db_path) as conn:
            for record in inventory:
                self.stats['bottles_processed'] += 1

                try:
                    # Step 1: Create or find Wine entity
                    wine_id = self._import_wine_from_inventory(conn, record)

                    # Step 2: Create Bottle entity linked to wine
                    self._import_bottle_from_inventory(conn, record, wine_id)

                except Exception as e:
                    error_msg = f"Error processing inventory record {record.get('iWine')}/{record.get('Barcode')}: {e}"
                    logger.error(error_msg)
                    self.stats['errors'].append(error_msg)


    def _process_bottles(self, bottles: List[Dict]):
        """
        Process bottles.json - Complete bottle lifecycle.

        Maps to: Bottle (primary), Wine (drinking window update)
        Priority: HIGH - Complete history

        Updates:
        - Wine: drink_from_year, drink_to_year (drinking window)
        - Bottle: Creates or updates complete lifecycle (active + consumed + gifted)
        """
        logger.info(f"Processing {len(bottles)} bottles from complete lifecycle")

        with get_db_connection(self.db_path) as conn:
            for record in bottles:
                self.stats['bottles_processed'] += 1

                try:
                    wine_id = self._find_and_update_wine_from_bottles(conn, record)
                    self._import_bottle_from_bottles_json(conn, record, wine_id)

                except Exception as e:
                    error_msg = f"Error processing bottle {record.get('Barcode')}: {e}"
                    logger.error(error_msg)
                    self.stats['errors'].append(error_msg)


    def _process_notes(self, notes: List[Dict]):
        """
        Process notes.json - Tasting notes and ratings.

        Maps to: Wine ONLY
        Priority: MEDIUM - Enhances quality

        Updates Wine with:
        - personal_rating (0-100 scale, keep highest)
        - tasting_notes (merge with date stamps)
        - last_tasted_date (keep most recent)
        """
        logger.info(f"Processing {len(notes)} tasting notes")

        with get_db_connection(self.db_path) as conn:
            for record in notes:
                self.stats['notes_processed'] += 1

                try:
                    self._update_wine_with_note(conn, record)
                except Exception as e:
                    error_msg = f"Error processing note {record.get('iNote')}: {e}"
                    logger.error(error_msg)
                    self.stats['errors'].append(error_msg)


    def _import_wine_from_inventory(self, conn, record: Dict) -> int:
        """
        Create or update Wine from inventory.json record.

        Per mapping: inventory.json → Wine entity
        Creates Wine with basic catalog info.
        """
        cursor = conn.cursor()
        self.stats['wines_processed'] += 1

        # Extract required fields per mapping
        iwine = record.get('iWine')
        wine_name = clean_text(record.get('Wine', ''))
        vintage = parse_vintage(record.get('Vintage'))
        wine_type = normalize_wine_type(record.get('Type', ''))

        # Get or create producer (from Producer field)
        producer_name = clean_text(record.get('Producer', ''))
        producer_id = self._get_or_create_producer(
            conn,
            producer_name,
            record.get('Country')
        )

        # Get or create region (from Region + Country)
        region_id = self._get_or_create_region(
            conn,
            record.get('Region'),
            record.get('Country')
        )

        # Check if wine exists
        cursor.execute(
            "SELECT id FROM wines WHERE source = ? AND external_id = ?",
            ('cellar_tracker', iwine)
        )
        existing = cursor.fetchone()

        if existing:
            # Update existing wine
            wine_id = existing[0]
            cursor.execute("""
                UPDATE wines SET
                    wine_name = ?,
                    producer_id = ?,
                    vintage = ?,
                    wine_type = ?,
                    varietal = ?,
                    designation = ?,
                    region_id = ?,
                    appellation = ?,
                    bottle_size = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (
                wine_name,
                producer_id,
                vintage,
                wine_type,
                clean_text(record.get('Varietal')),
                clean_text(record.get('Designation')),
                region_id,
                clean_text(record.get('Appellation')),
                record.get('Size', '750ml'),
                wine_id
            ))
            self.stats['wines_updated'] += 1
            logger.debug(f"Updated wine: {wine_name} ({vintage})")

        else:
            # Insert new wine
            cursor.execute("""
                INSERT INTO wines (
                    source, external_id, wine_name, producer_id, vintage,
                    wine_type, varietal, designation, region_id,
                    appellation, bottle_size
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                'cellar_tracker',
                iwine,
                wine_name,
                producer_id,
                vintage,
                wine_type,
                clean_text(record.get('Varietal')),
                clean_text(record.get('Designation')),
                region_id,
                clean_text(record.get('Appellation')),
                record.get('Size', '750ml')
            ))
            wine_id = cursor.lastrowid
            self.stats['wines_imported'] += 1
            logger.debug(f"Imported wine: {wine_name} ({vintage})")

        conn.commit()
        return wine_id


    def _find_and_update_wine_from_bottles(self, conn, record: Dict) -> Optional[int]:
        """
        Find Wine and update drinking window from bottles.json record.

        Per mapping: bottles.json → Wine (drinking window update)
        Updates: drink_from_year, drink_to_year
        """
        cursor = conn.cursor()
        iwine = record.get('iWine')
        cursor.execute(
            "SELECT id FROM wines WHERE source = ? AND external_id = ?",
            ('cellar_tracker', iwine)
        )
        wine = cursor.fetchone()

        # Add a new wine if not found
        if not wine:
            wine_id = self._import_wine_from_inventory(conn, record)
        else:
            wine_id = wine[0]

        begin_consume = record.get('BeginConsume')
        end_consume = record.get('EndConsume')

        if begin_consume or end_consume:
            drink_from_year, drink_to_year = parse_drinking_window(begin_consume, end_consume)

            cursor.execute("""
                UPDATE wines SET
                    drink_from_year = COALESCE(?, drink_from_year),
                    drink_to_year = COALESCE(?, drink_to_year),
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (drink_from_year, drink_to_year, wine_id))

            conn.commit()
            logger.debug(f"Updated drinking window for wine {iwine}: {drink_from_year}-{drink_to_year}")

        return wine_id


    def _import_bottle_from_inventory(self, conn, record: Dict, wine_id: int) -> int:
        """
        Create Bottle from inventory.json record.

        Per mapping: inventory.json → Bottle entity
        Creates Bottle with status='in_cellar' for current cellar inventory.
        """
        cursor = conn.cursor()

        # Extract bottle fields per mapping
        barcode = record.get('Barcode')
        location = clean_text(record.get('Location'))
        bin_location = clean_text(record.get('Bin'))
        purchase_date = parse_date(record.get('PurchaseDate'))
        bottle_note = clean_text(record.get('BottleNote'))

        # Parse price
        price = None
        price_str = record.get('Price')
        if price_str:
            try:
                price = float(price_str)
            except (ValueError, TypeError):
                pass

        # Check if bottle already exists
        if barcode:
            cursor.execute(
                "SELECT id FROM bottles WHERE source = ? AND external_bottle_id = ?",
                ('cellar_tracker', barcode)
            )
            existing = cursor.fetchone()

            if existing:
                # Update existing bottle
                bottle_id = existing[0]
                cursor.execute("""
                    UPDATE bottles SET
                        wine_id = ?,
                        quantity = 1,
                        status = 'in_cellar',
                        location = ?,
                        bin = ?,
                        purchase_date = ?,
                        purchase_price = ?,
                        currency = ?,
                        store_name = ?,
                        bottle_note = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (
                    wine_id,
                    location,
                    bin_location,
                    purchase_date,
                    price,
                    record.get('Currency', 'RON'),
                    clean_text(record.get('StoreName')),
                    bottle_note,
                    bottle_id
                ))
                self.stats['bottles_updated'] += 1
                logger.debug(f"Updated bottle: {barcode}")
                conn.commit()
                return bottle_id

        # Insert new bottle
        cursor.execute("""
            INSERT INTO bottles (
                wine_id, source, external_bottle_id, quantity, status,
                location, bin, purchase_date, purchase_price, currency,
                store_name, bottle_note
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            wine_id,
            'cellar_tracker',
            barcode,
            1,  # Quantity is always 1 per inventory record
            'in_cellar',  # Status is always in_cellar for inventory.json
            location,
            bin_location,
            purchase_date,
            price,
            record.get('Currency', 'RON'),
            clean_text(record.get('StoreName')),
            bottle_note
        ))
        bottle_id = cursor.lastrowid
        self.stats['bottles_imported'] += 1
        logger.debug(f"Imported bottle: {barcode or bottle_id}")

        conn.commit()
        return bottle_id


    def _import_bottle_from_bottles_json(self, conn, record: Dict, wine_id: int) -> int:
        """
        Create or update Bottle from bottles.json record.

        Per mapping: bottles.json → Bottle entity
        Complete bottle lifecycle including consumption tracking.
        """
        cursor = conn.cursor()

        # Extract bottle fields
        barcode = record.get('Barcode')
        quantity = int(record.get('Quantity', 1))

        # Map BottleState to status
        bottle_state = record.get('BottleState', '0')
        consumption_date = record.get('ConsumptionDate')

        if bottle_state == '0' and not consumption_date:
            status = 'in_cellar'
        elif consumption_date:
            # Determine status from consumption type
            short_type = record.get('ShortType', '').lower()
            if 'gift' in short_type:
                status = 'gifted'
            elif 'spoil' in short_type or 'dump' in short_type:
                status = 'lost'
            else:
                status = 'consumed'
        else:
            status = 'in_cellar'

        # Parse dates
        purchase_date = parse_date(record.get('PurchaseDate'))
        consumed_date = parse_date(consumption_date) if consumption_date else None

        # Parse price
        price = None
        price_str = record.get('BottleCost')
        if price_str:
            try:
                price = float(price_str)
            except (ValueError, TypeError):
                pass

        # Merge notes
        purchase_note = clean_text(record.get('PurchaseNote'))
        consumption_note = clean_text(record.get('ConsumptionNote'))
        bottle_note = self._merge_bottle_notes(purchase_note, consumption_note)

        # Check if bottle exists
        if barcode:
            cursor.execute(
                "SELECT id FROM bottles WHERE source = ? AND external_bottle_id = ?",
                ('cellar_tracker', barcode)
            )
            existing = cursor.fetchone()

            if existing:
                # Update existing bottle
                bottle_id = existing[0]
                cursor.execute("""
                    UPDATE bottles SET
                        wine_id = ?,
                        quantity = ?,
                        status = ?,
                        location = ?,
                        bin = ?,
                        purchase_date = ?,
                        purchase_price = ?,
                        currency = ?,
                        store_name = ?,
                        consumed_date = ?,
                        bottle_note = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (
                    wine_id,
                    quantity,
                    status,
                    clean_text(record.get('Location')),
                    clean_text(record.get('Bin')),
                    purchase_date,
                    price,
                    record.get('BottleCostCurrency', 'RON'),
                    clean_text(record.get('Store')),
                    consumed_date,
                    bottle_note,
                    bottle_id
                ))
                self.stats['bottles_updated'] += 1
                logger.debug(f"Updated bottle from bottles.json: {barcode}")
                conn.commit()
                return bottle_id

        # Insert new bottle
        cursor.execute("""
            INSERT INTO bottles (
                wine_id, source, external_bottle_id, quantity, status,
                location, bin, purchase_date, purchase_price, currency,
                store_name, consumed_date, bottle_note
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            wine_id,
            'cellar_tracker',
            barcode,
            quantity,
            status,
            clean_text(record.get('Location')),
            clean_text(record.get('Bin')),
            purchase_date,
            price,
            record.get('BottleCostCurrency', 'RON'),
            clean_text(record.get('Store')),
            consumed_date,
            bottle_note
        ))
        bottle_id = cursor.lastrowid
        self.stats['bottles_imported'] += 1
        logger.debug(f"Imported bottle from bottles.json: {barcode or bottle_id}")

        conn.commit()
        return bottle_id

    @staticmethod
    def _update_wine_with_note(conn, record: Dict):
        """
        Update Wine from notes.json record.

        Per mapping: notes.json → Wine entity ONLY
        Updates: personal_rating, tasting_notes, last_tasted_date
        """
        cursor = conn.cursor()

        iwine = record.get('iWine')

        # Find the wine
        cursor.execute(
            "SELECT id, personal_rating, tasting_notes, last_tasted_date FROM wines WHERE source = ? AND external_id = ?",
            ('cellar_tracker', iwine)
        )
        wine = cursor.fetchone()

        if not wine:
            logger.warning(f"Wine {iwine} not found for note update")
            return

        wine_id = wine[0]
        existing_rating = wine[1]
        existing_notes = wine[2] or ""
        last_tasted = wine[3]

        # Parse rating (CT uses 0-100 scale) - keep highest
        rating = existing_rating
        rating_str = record.get('Rating')
        if rating_str:
            try:
                new_rating = int(rating_str)
                if existing_rating is None or new_rating > existing_rating:
                    rating = new_rating
            except (ValueError, TypeError):
                pass

        # Parse tasting date
        tasting_date = parse_date(record.get('TastingDate'))

        # Get note text
        note_text = clean_text(record.get('TastingNotes'))

        # Merge notes with date stamp
        if note_text:
            if existing_notes:
                # Append new note with date
                date_str = tasting_date or datetime.now().strftime('%Y-%m-%d')
                combined_notes = f"{existing_notes}\n\n[{date_str}] {note_text}"
            else:
                date_str = tasting_date or datetime.now().strftime('%Y-%m-%d')
                combined_notes = f"[{date_str}] {note_text}"
        else:
            combined_notes = existing_notes

        # Update if this is a newer tasting (keep most recent)
        should_update_date = True
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

        # Update wine record
        if should_update_date and tasting_date:
            cursor.execute("""
                UPDATE wines SET
                    personal_rating = ?,
                    tasting_notes = ?,
                    last_tasted_date = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (rating, combined_notes, tasting_date, wine_id))
        else:
            # Just update notes and rating, not date
            cursor.execute("""
                UPDATE wines SET
                    personal_rating = ?,
                    tasting_notes = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (rating, combined_notes, wine_id))

        logger.debug(f"Updated wine {iwine} with note (rating: {rating})")
        conn.commit()


    @staticmethod
    def _merge_bottle_notes(purchase_note: Optional[str], consumption_note: Optional[str]) -> Optional[str]:
        """Merge purchase and consumption notes."""
        if purchase_note and consumption_note:
            return f"{purchase_note}\n\nConsumed: {consumption_note}"
        return purchase_note or consumption_note


    def _get_or_create_producer(self, conn, name: str, country: Optional[str]) -> Optional[int]:
        """
        Get or create producer, return ID.

        Note: sort_name field removed per schema update.
        """
        if not name:
            return None

        # Check cache
        if name in self.producer_cache:
            return self.producer_cache[name]

        cursor = conn.cursor()

        # Check if exists
        cursor.execute("SELECT id FROM producers WHERE name = ?", (name,))
        existing = cursor.fetchone()

        if existing:
            producer_id = existing[0]
        else:
            # Create new producer (no sort_name field)
            cursor.execute("""
                INSERT INTO producers (name, country)
                VALUES (?, ?)
            """, (name, country))
            producer_id = cursor.lastrowid
            self.stats['producers_created'] += 1
            conn.commit()

        # Cache it
        self.producer_cache[name] = producer_id
        return producer_id


    def _get_or_create_region(self, conn, name: Optional[str], country: Optional[str]) -> Optional[int]:
        """Get or create region, return ID."""
        if not name or not country:
            return None

        # Check cache
        cache_key = (name, country)
        if cache_key in self.region_cache:
            return self.region_cache[cache_key]

        cursor = conn.cursor()

        # Check if exists
        cursor.execute("SELECT id FROM regions WHERE name = ? AND country = ?", (name, country))
        existing = cursor.fetchone()

        if existing:
            region_id = existing[0]
        else:
            # Create new region
            cursor.execute("""
                INSERT INTO regions (name, country)
                VALUES (?, ?)
            """, (name, country))
            region_id = cursor.lastrowid
            self.stats['regions_created'] += 1
            conn.commit()

        # Cache it
        self.region_cache[cache_key] = region_id
        return region_id


    def _start_sync_log(self, sync_type: str = 'full') -> int:
        """Create sync log entry and return ID."""
        with get_db_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO sync_log (
                    source, sync_type, sync_started_at, status
                ) VALUES (?, ?, ?, ?)
            """, ('cellar_tracker', sync_type, datetime.now(), 'in_progress'))
            conn.commit()
            return cursor.lastrowid


    def _complete_sync_log(self, sync_id: int, status: str, error_message: Optional[str] = None):
        """Update sync log entry with completion status."""
        with get_db_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE sync_log SET
                    sync_completed_at = ?,
                    status = ?,
                    records_processed = ?,
                    records_imported = ?,
                    records_updated = ?,
                    records_skipped = ?,
                    records_failed = ?,
                    error_message = ?
                WHERE id = ?
            """, (
                datetime.now(),
                status,
                self.stats.get('wines_processed', 0)+ self.stats.get('bottles_processed', 0),
                self.stats.get('wines_imported', 0) + self.stats.get('bottles_imported', 0),
                self.stats.get('wines_updated', 0) + self.stats.get('bottles_updated', 0),
                self.stats.get('wines_skipped', 0) + self.stats.get('bottles_skipped', 0),
                len(self.stats['errors']),
                error_message,
                sync_id
            ))
            conn.commit()




