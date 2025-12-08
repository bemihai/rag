"""
Database access layer for wine cellar.

Provides high-level interface for database operations without exposing SQL queries.
Follows repository pattern for clean separation of concerns.
"""
from .bottle import BottleRepository
from .producer import ProducerRepository
from .region import RegionRepository
from .stats import StatsRepository
from .tasting import TastingRepository
from .wine import WineRepository
from .sync_logs import SyncLogRepository
from .food_pairing import FoodPairingRepository

__all__ = [
    "BottleRepository",
    "ProducerRepository",
    "RegionRepository",
    "StatsRepository",
    "TastingRepository",
    "WineRepository",
    "SyncLogRepository",
    "FoodPairingRepository",
]