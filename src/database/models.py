"""Data models for wine cellar database."""
from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional


@dataclass
class Producer:
    """Wine producer/winery model."""
    id: Optional[int] = None
    name: str = ""
    sort_name: Optional[str] = None
    country: Optional[str] = None
    region: Optional[str] = None
    website: Optional[str] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class Region:
    """Geographic wine region model."""
    id: Optional[int] = None
    name: str = ""
    country: str = ""
    parent_region_id: Optional[int] = None
    level: Optional[str] = None
    regional_style: Optional[str] = None
    created_at: Optional[datetime] = None


@dataclass
class Wine:
    """Wine catalog model."""
    id: Optional[int] = None
    source: str = "manual"  # 'cellar_tracker', 'vivino', 'manual'
    external_id: Optional[str] = None
    wine_name: str = ""
    producer_id: Optional[int] = None
    vintage: Optional[int] = None
    wine_type: str = "Red"  # 'Red', 'White', 'Rosé', 'Sparkling', 'Dessert', 'Fortified'
    color: Optional[str] = None
    varietal: Optional[str] = None
    designation: Optional[str] = None
    region_id: Optional[int] = None
    appellation: Optional[str] = None
    alcohol_content: Optional[float] = None
    bottle_size: str = "750ml"
    personal_rating: Optional[int] = None  # 0-100 scale
    community_rating: Optional[float] = None  # 0-5 scale
    community_rating_count: Optional[int] = None
    tasting_notes: Optional[str] = None
    last_tasted_date: Optional[date] = None
    drink_from_year: Optional[int] = None
    drink_to_year: Optional[int] = None
    label_image_url: Optional[str] = None
    vivino_url: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    # Related objects (not in DB, populated via joins)
    producer_name: Optional[str] = None
    region_name: Optional[str] = None
    country: Optional[str] = None


@dataclass
class Bottle:
    """Individual bottle inventory model."""
    id: Optional[int] = None
    wine_id: int = 0
    source: str = "manual"  # 'cellar_tracker', 'vivino', 'manual'
    external_bottle_id: Optional[str] = None
    quantity: int = 1
    status: str = "in_cellar"  # 'in_cellar', 'consumed', 'gifted', 'lost'
    location: Optional[str] = None
    bin: Optional[str] = None
    purchase_date: Optional[date] = None
    purchase_price: Optional[float] = None
    currency: str = "RON"
    store_name: Optional[str] = None
    consumed_date: Optional[date] = None
    consumption_type: Optional[str] = None
    bottle_note: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    # Related objects (not in DB, populated via joins)
    wine_name: Optional[str] = None
    producer_name: Optional[str] = None
    vintage: Optional[int] = None


@dataclass
class SyncLog:
    """Sync operation log model."""
    id: Optional[int] = None
    source: str = ""  # 'cellar_tracker', 'vivino'
    sync_type: str = ""  # 'initial', 'incremental', 'manual'
    sync_started_at: datetime = None
    sync_completed_at: Optional[datetime] = None
    status: str = ""  # 'success', 'failed', 'partial'
    records_processed: int = 0
    records_imported: int = 0
    records_updated: int = 0
    records_skipped: int = 0
    records_failed: int = 0
    error_message: Optional[str] = None
    error_details: Optional[str] = None
    created_at: Optional[datetime] = None


@dataclass
class DataSource:
    """Data source configuration model."""
    id: Optional[int] = None
    source_name: str = ""  # 'cellar_tracker', 'vivino'
    source_type: str = ""  # 'api', 'csv', 'json'
    is_enabled: bool = True
    last_sync_at: Optional[datetime] = None
    last_sync_status: Optional[str] = None
    next_sync_at: Optional[datetime] = None
    config: Optional[str] = None  # JSON config
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

