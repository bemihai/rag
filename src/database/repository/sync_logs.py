"""Sync logs repository"""
from datetime import datetime

from src.database import get_db_connection
from src.utils import get_default_db_path


class SyncLogRepository:
    """Repository for sync log-related database operations."""

    def __init__(self, db_path: str | None = None):
        """
        Initialize sync log repository.

        Args:
            db_path: Optional path to database file
        """
        self.db_path = db_path or get_default_db_path()

    def start_sync_log(self, sync_type: str = 'full') -> int:
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


    def complete_sync_log(self, sync_id: int, stats: dict, status: str, error_message: str | None = None):
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
                stats.get('wines_processed', 0) + stats.get('bottles_processed', 0),
                stats.get('wines_imported', 0) + stats.get('bottles_imported', 0),
                stats.get('wines_updated', 0) + stats.get('bottles_updated', 0),
                stats.get('wines_skipped', 0) + stats.get('bottles_skipped', 0),
                len(stats['errors']),
                error_message,
                sync_id
            ))
            conn.commit()
