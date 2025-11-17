"""
Database access layer for wine cellar.

Provides high-level interface for database operations without exposing SQL queries.
Follows repository pattern for clean separation of concerns.
"""
from .bottle import BottleRepository
from .producer import ProducerRepository
from .region import RegionRepository
from .stats import StatsRepository
from .wine import WineRepository
from .sync_logs import SyncLogRepository

__all__ = [
    "BottleRepository",
    "ProducerRepository",
    "RegionRepository",
    "StatsRepository",
    "WineRepository",
    "SyncLogRepository",
]