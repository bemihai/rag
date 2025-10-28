"""CellarTracker API importer for wine cellar database."""
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
        Import all data from CellarTracker.

        Returns:
            Import statistics dictionary
        """
        logger.info("Starting full CellarTracker import")

        sync_id = self._start_sync_log()

        try:
            # Import wines from list
            logger.info("Fetching wine list...")
            wines_list = self.client.get_list()
            self._process_wine_list(wines_list)

            # Import bottles from inventory
            logger.info("Fetching inventory...")
            inventory = self.client.get_inventory()
            self._process_inventory(inventory)

            # Import consumed bottles
            logger.info("Fetching consumed bottles...")
            consumed = self.client.get_consumed()
            self._process_consumed(consumed)

            # Import tasting notes
            logger.info("Fetching tasting notes...")
            notes = self.client.get_notes()
            self._process_notes(notes)

            # Import purchase history (if needed for additional context)
            logger.info("Fetching purchase history...")
            purchases = self.client.get_purchase()
            self._process_purchases(purchases)

            self._complete_sync_log(sync_id, 'success')
            logger.info(f"Import completed successfully: {self.stats}")

        except Exception as e:
            error_msg = f"Import failed: {e}"
            logger.error(error_msg)
            self.stats['errors'].append(error_msg)
            self._complete_sync_log(sync_id, 'failed', error_msg)

        return self.stats

    def import_inventory_only(self) -> Dict:
        """
        Import only current inventory (in-cellar bottles).

        Returns:
            Import statistics dictionary
        """
        logger.info("Starting CellarTracker inventory import")

        sync_id = self._start_sync_log('inventory')

        try:
            inventory = self.client.get_inventory()
            self._process_inventory(inventory)

            self._complete_sync_log(sync_id, 'success')
            logger.info(f"Inventory import completed: {self.stats}")

        except Exception as e:
            error_msg = f"Inventory import failed: {e}"
            logger.error(error_msg)
            self.stats['errors'].append(error_msg)
            self._complete_sync_log(sync_id, 'failed', error_msg)

        return self.stats

    def _process_wine_list(self, wines_list: List[Dict]):
        """Process wines from get_list() API call."""
        logger.info(f"Processing {len(wines_list)} wines from list")

        with get_db_connection(self.db_path) as conn:
            for wine_data in wines_list:
                self.stats['wines_processed'] += 1

                try:
                    self._import_wine(conn, wine_data)
                except Exception as e:
                    error_msg = f"Error processing wine {wine_data.get('iWine')}: {e}"
                    logger.error(error_msg)
                    self.stats['errors'].append(error_msg)

    def _process_inventory(self, inventory: List[Dict]):
        """Process bottles from get_inventory() API call."""
        logger.info(f"Processing {len(inventory)} bottles from inventory")

        with get_db_connection(self.db_path) as conn:
            for bottle_data in inventory:
                self.stats['bottles_processed'] += 1

                try:
                    # First ensure wine exists
                    wine_id = self._ensure_wine_exists(conn, bottle_data)

                    # Then import the bottle
                    self._import_bottle(conn, bottle_data, wine_id, status='in_cellar')

                except Exception as e:
                    error_msg = f"Error processing bottle {bottle_data.get('Barcode')}: {e}"
                    logger.error(error_msg)
                    self.stats['errors'].append(error_msg)

    def _process_consumed(self, consumed: List[Dict]):
        """Process consumed bottles from get_consumed() API call."""
        logger.info(f"Processing {len(consumed)} consumed bottles")

        with get_db_connection(self.db_path) as conn:
            for bottle_data in consumed:
                self.stats['bottles_processed'] += 1

                try:
                    # First ensure wine exists
                    wine_id = self._ensure_wine_exists(conn, bottle_data)

                    # Then import the consumed bottle
                    self._import_consumed_bottle(conn, bottle_data, wine_id)

                except Exception as e:
                    error_msg = f"Error processing consumed bottle {bottle_data.get('iConsumed')}: {e}"
                    logger.error(error_msg)
                    self.stats['errors'].append(error_msg)

    def _process_notes(self, notes: List[Dict]):
        """Process tasting notes from get_notes() API call."""
        logger.info(f"Processing {len(notes)} tasting notes")

        with get_db_connection(self.db_path) as conn:
            for note_data in notes:
                self.stats['notes_processed'] += 1

                try:
                    self._update_wine_with_note(conn, note_data)
                except Exception as e:
                    error_msg = f"Error processing note {note_data.get('iNote')}: {e}"
                    logger.error(error_msg)
                    self.stats['errors'].append(error_msg)

    def _process_purchases(self, purchases: List[Dict]):
        """Process purchase history from get_purchase() API call."""
        logger.info(f"Processing {len(purchases)} purchase records")

        # Purchase data is primarily used to enrich bottle information
        # Most of this data should already be in inventory/bottles
        # We'll use it to fill in missing purchase details

        with get_db_connection(self.db_path) as conn:
            for purchase_data in purchases:
                try:
                    self._update_bottle_purchase_info(conn, purchase_data)
                except Exception as e:
                    error_msg = f"Error processing purchase {purchase_data.get('iPurchase')}: {e}"
                    logger.debug(error_msg)  # Debug level since this is supplementary

    def _import_wine(self, conn, wine_data: Dict) -> int:
        """
        Import or update a wine record.

        Args:
            conn: Database connection
            wine_data: Wine data from CellarTracker

        Returns:
            Wine ID
        """
        cursor = conn.cursor()

        # Extract wine data
        iwine = wine_data.get('iWine')
        wine_name = clean_text(wine_data.get('Wine', ''))
        vintage = parse_vintage(wine_data.get('Vintage'))
        wine_type = normalize_wine_type(wine_data.get('Type', ''))

        # Get or create producer
        producer_name = clean_text(wine_data.get('Producer', ''))
        producer_id = self._get_or_create_producer(
            conn,
            producer_name,
            wine_data.get('SortProducer'),
            wine_data.get('Country')
        )

        # Get or create region
        region_id = self._get_or_create_region(
            conn,
            wine_data.get('Region'),
            wine_data.get('Country')
        )

        # Check if wine exists
        cursor.execute(
            "SELECT id FROM wines WHERE source = ? AND external_id = ?",
            ('cellar_tracker', iwine)
        )
        existing = cursor.fetchone()

        # Parse drinking window
        begin_consume = wine_data.get('BeginConsume')
        end_consume = wine_data.get('EndConsume')
        drink_from_year, drink_to_year = parse_drinking_window(begin_consume, end_consume)

        if existing:
            # Update existing wine
            wine_id = existing[0]
            cursor.execute("""
                UPDATE wines SET
                    wine_name = ?,
                    producer_id = ?,
                    vintage = ?,
                    wine_type = ?,
                    color = ?,
                    varietal = ?,
                    designation = ?,
                    region_id = ?,
                    appellation = ?,
                    bottle_size = ?,
                    drink_from_year = ?,
                    drink_to_year = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (
                wine_name,
                producer_id,
                vintage,
                wine_type,
                wine_data.get('Color'),
                wine_data.get('Varietal'),
                wine_data.get('Designation'),
                region_id,
                wine_data.get('Appellation'),
                wine_data.get('Size', '750ml'),
                drink_from_year,
                drink_to_year,
                wine_id
            ))
            self.stats['wines_updated'] += 1
            logger.debug(f"Updated wine: {wine_name} ({vintage})")

        else:
            # Insert new wine
            cursor.execute("""
                INSERT INTO wines (
                    source, external_id, wine_name, producer_id, vintage,
                    wine_type, color, varietal, designation, region_id,
                    appellation, bottle_size, drink_from_year, drink_to_year
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                'cellar_tracker',
                iwine,
                wine_name,
                producer_id,
                vintage,
                wine_type,
                wine_data.get('Color'),
                wine_data.get('Varietal'),
                wine_data.get('Designation'),
                region_id,
                wine_data.get('Appellation'),
                wine_data.get('Size', '750ml'),
                drink_from_year,
                drink_to_year
            ))
            wine_id = cursor.lastrowid
            self.stats['wines_imported'] += 1
            logger.debug(f"Imported wine: {wine_name} ({vintage})")

        conn.commit()
        return wine_id

    def _ensure_wine_exists(self, conn, bottle_data: Dict) -> int:
        """Ensure wine exists in database, create if needed."""
        cursor = conn.cursor()

        iwine = bottle_data.get('iWine')

        # Check if wine already exists
        cursor.execute(
            "SELECT id FROM wines WHERE source = ? AND external_id = ?",
            ('cellar_tracker', iwine)
        )
        existing = cursor.fetchone()

        if existing:
            return existing[0]

        # Create wine record from bottle data
        return self._import_wine(conn, bottle_data)

    def _import_bottle(self, conn, bottle_data: Dict, wine_id: int, status: str = 'in_cellar') -> int:
        """
        Import or update a bottle record.

        Args:
            conn: Database connection
            bottle_data: Bottle data from CellarTracker
            wine_id: Wine ID
            status: Bottle status (in_cellar, consumed, etc.)

        Returns:
            Bottle ID
        """
        cursor = conn.cursor()

        barcode = bottle_data.get('Barcode') or bottle_data.get('WineBarcode')

        # Check if bottle exists
        cursor.execute(
            "SELECT id FROM bottles WHERE source = ? AND external_bottle_id = ?",
            ('cellar_tracker', barcode)
        )
        existing = cursor.fetchone()

        # Parse dates
        purchase_date = parse_date(bottle_data.get('PurchaseDate'))
        consumed_date = None
        if status != 'in_cellar':
            consumed_date = parse_date(bottle_data.get('ConsumptionDate') or bottle_data.get('Consumed'))

        # Get price
        price = None
        price_str = bottle_data.get('BottleCost') or bottle_data.get('Price')
        if price_str:
            try:
                price = float(price_str)
            except (ValueError, TypeError):
                pass

        if existing:
            # Update existing bottle
            bottle_id = existing[0]
            cursor.execute("""
                UPDATE bottles SET
                    wine_id = ?,
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
                status,
                bottle_data.get('Location'),
                bottle_data.get('Bin'),
                purchase_date,
                price,
                bottle_data.get('Currency') or bottle_data.get('BottleCostCurrency', 'RON'),
                bottle_data.get('Store') or bottle_data.get('StoreName'),
                consumed_date,
                bottle_data.get('BottleNote'),
                bottle_id
            ))
            self.stats['bottles_updated'] += 1

        else:
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
                1,  # Each record is one bottle
                status,
                bottle_data.get('Location'),
                bottle_data.get('Bin'),
                purchase_date,
                price,
                bottle_data.get('Currency') or bottle_data.get('BottleCostCurrency', 'RON'),
                bottle_data.get('Store') or bottle_data.get('StoreName'),
                consumed_date,
                bottle_data.get('BottleNote')
            ))
            bottle_id = cursor.lastrowid
            self.stats['bottles_imported'] += 1

        conn.commit()
        return bottle_id

    def _import_consumed_bottle(self, conn, bottle_data: Dict, wine_id: int):
        """Import a consumed bottle."""
        # Determine consumption type
        short_type = bottle_data.get('ShortType', 'Drank').lower()
        consumption_type_map = {
            'drank': 'drank',
            'gifted': 'gifted',
            'gift': 'gifted',
            'spoiled': 'spoiled',
            'dumped': 'spoiled'
        }
        consumption_type = consumption_type_map.get(short_type, 'drank')

        # Determine status
        status_map = {
            'drank': 'consumed',
            'gifted': 'gifted',
            'spoiled': 'lost'
        }
        status = status_map.get(consumption_type, 'consumed')

        # Import bottle with consumed status
        bottle_id = self._import_bottle(conn, bottle_data, wine_id, status)

        # Update consumption type
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE bottles SET
                consumption_type = ?,
                bottle_note = COALESCE(?, bottle_note)
            WHERE id = ?
        """, (
            consumption_type,
            bottle_data.get('ConsumptionNote'),
            bottle_id
        ))
        conn.commit()

    def _update_wine_with_note(self, conn, note_data: Dict):
        """Update wine with tasting note information."""
        cursor = conn.cursor()

        iwine = note_data.get('iWine')

        # Find the wine
        cursor.execute(
            "SELECT id, tasting_notes, last_tasted_date FROM wines WHERE source = ? AND external_id = ?",
            ('cellar_tracker', iwine)
        )
        wine = cursor.fetchone()

        if not wine:
            logger.warning(f"Wine {iwine} not found for note update")
            return

        wine_id = wine[0]
        existing_notes = wine[1] or ""
        last_tasted = wine[2]

        # Parse rating (CT uses 0-100 scale)
        rating = None
        rating_str = note_data.get('Rating')
        if rating_str:
            try:
                rating = int(rating_str)
            except (ValueError, TypeError):
                pass

        # Parse tasting date
        tasting_date = parse_date(note_data.get('TastingDate'))

        # Get note text
        note_text = clean_text(note_data.get('Note', ''))

        # Combine notes if there are multiple
        if note_text:
            if existing_notes:
                # Append new note with date
                date_str = tasting_date or datetime.now().strftime('%Y-%m-%d')
                combined_notes = f"{existing_notes}\n\n[{date_str}] {note_text}"
            else:
                combined_notes = note_text
        else:
            combined_notes = existing_notes

        # Update if this is a newer tasting
        should_update_date = True
        if last_tasted and tasting_date:
            try:
                last_tasted_obj = datetime.strptime(last_tasted, '%Y-%m-%d').date()
                tasting_date_obj = datetime.strptime(tasting_date, '%Y-%m-%d').date()
                should_update_date = tasting_date_obj >= last_tasted_obj
            except:
                pass

        # Update wine record
        if should_update_date:
            cursor.execute("""
                UPDATE wines SET
                    personal_rating = COALESCE(?, personal_rating),
                    tasting_notes = ?,
                    last_tasted_date = COALESCE(?, last_tasted_date),
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (rating, combined_notes, tasting_date, wine_id))
        else:
            # Just update notes and rating, not date
            cursor.execute("""
                UPDATE wines SET
                    personal_rating = COALESCE(?, personal_rating),
                    tasting_notes = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (rating, combined_notes, wine_id))

        conn.commit()

    def _update_bottle_purchase_info(self, conn, purchase_data: Dict):
        """Update bottle with additional purchase information."""
        cursor = conn.cursor()

        iwine = purchase_data.get('iWine')
        purchase_date = parse_date(purchase_data.get('PurchaseDate'))

        # Try to find matching bottle
        cursor.execute("""
            SELECT b.id FROM bottles b
            JOIN wines w ON b.wine_id = w.id
            WHERE w.source = ? AND w.external_id = ?
            AND b.purchase_date = ?
            AND b.purchase_price IS NULL
        """, ('cellar_tracker', iwine, purchase_date))

        bottle = cursor.fetchone()

        if bottle:
            price = None
            price_str = purchase_data.get('Price') or purchase_data.get('NativePrice')
            if price_str:
                try:
                    price = float(price_str)
                except (ValueError, TypeError):
                    pass

            cursor.execute("""
                UPDATE bottles SET
                    purchase_price = ?,
                    currency = ?,
                    store_name = COALESCE(?, store_name)
                WHERE id = ?
            """, (
                price,
                purchase_data.get('Currency') or purchase_data.get('NativePriceCurrency', 'RON'),
                purchase_data.get('StoreName'),
                bottle[0]
            ))
            conn.commit()

    def _get_or_create_producer(self, conn, name: str, sort_name: Optional[str], country: Optional[str]) -> Optional[int]:
        """Get or create producer, return ID."""
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
            # Create new producer
            cursor.execute("""
                INSERT INTO producers (name, sort_name, country)
                VALUES (?, ?, ?)
            """, (name, sort_name, country))
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
                self.stats['wines_processed'] + self.stats['bottles_processed'],
                self.stats['wines_imported'] + self.stats['bottles_imported'],
                self.stats['wines_updated'] + self.stats['bottles_updated'],
                self.stats['wines_skipped'],
                len(self.stats['errors']),
                error_message,
                sync_id
            ))
            conn.commit()

