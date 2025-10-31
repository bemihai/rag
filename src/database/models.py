"""Data models for wine cellar database."""
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class Producer(BaseModel):
    """Wine producer/winery model."""
    model_config = ConfigDict(from_attributes=True)

    id: Optional[int] = Field(None, description="Unique identifier")
    name: str = Field("", description="Producer/winery name")
    country: Optional[str] = Field(None, description="Country of origin")
    region: Optional[str] = Field(None, description="Primary wine region")
    notes: Optional[str] = Field(None, description="Additional notes about the producer")
    created_at: Optional[datetime] = Field(None, description="Record creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Record last update timestamp")


class Region(BaseModel):
    """Geographic wine region model."""
    model_config = ConfigDict(from_attributes=True)

    id: Optional[int] = Field(None, description="Unique identifier")
    name: str = Field("", description="Region name (e.g., Loire Valley, Bordeaux)")
    country: str = Field("", description="Country where region is located")
    parent_region_id: Optional[int] = Field(None, description="Parent region ID for hierarchical regions")
    created_at: Optional[datetime] = Field(None, description="Record creation timestamp")


class Wine(BaseModel):
    """Wine catalog model."""
    model_config = ConfigDict(from_attributes=True)

    id: Optional[int] = Field(None, description="Unique identifier")
    source: str = Field("manual", description="Data source: 'cellar_tracker', 'vivino', or 'manual'")
    external_id: Optional[str] = Field(None, description="External ID from source system (e.g., CellarTracker iWine)")
    wine_name: str = Field("", description="Full wine name")
    producer_id: Optional[int] = Field(None, description="Foreign key to producer table")
    vintage: Optional[int] = Field(None, description="Vintage year (empty for non-vintage wines)")
    wine_type: str = Field("Red", description="Wine type: Red, White, Rosé, Sparkling, Dessert, Fortified")
    varietal: Optional[str] = Field(None, description="Grape variety/varietal (e.g., Sauvignon Blanc, Merlot)")
    designation: Optional[str] = Field(None, description="Special designation or cuvée name (e.g., Reserve, Grand Cru)")
    region_id: Optional[int] = Field(None, description="Foreign key to region table")
    appellation: Optional[str] = Field(None, description="Specific appellation (e.g., Pouilly-Fumé)")
    bottle_size: str = Field("750ml", description="Bottle size (e.g., 750ml, 1.5L)")
    personal_rating: Optional[int] = Field(None, description="Personal rating on 0-100 scale")
    community_rating: Optional[float] = Field(None, description="Community average rating on 0-5 scale")
    tasting_notes: Optional[str] = Field(None, description="Personal tasting notes and review")
    last_tasted_date: Optional[date] = Field(None, description="Date of most recent tasting")
    drink_from_year: Optional[int] = Field(None, description="Start of optimal drinking window")
    drink_to_year: Optional[int] = Field(None, description="End of optimal drinking window")
    created_at: Optional[datetime] = Field(None, description="Record creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Record last update timestamp")

    # Related objects (not in DB, populated via joins)
    producer_name: Optional[str] = Field(None, description="Producer name (populated via join)")
    region_name: Optional[str] = Field(None, description="Region name (populated via join)")
    country: Optional[str] = Field(None, description="Country (populated via join)")



class Bottle(BaseModel):
    """Individual bottle inventory model."""
    model_config = ConfigDict(from_attributes=True)

    id: Optional[int] = Field(None, description="Unique identifier")
    wine_id: int = Field(0, description="Foreign key to wine table")
    source: str = Field("manual", description="Data source: 'cellar_tracker', 'vivino', or 'manual'")
    external_bottle_id: Optional[str] = Field(None, description="External bottle ID (e.g., CellarTracker barcode)")
    quantity: int = Field(1, description="Number of bottles in this record")
    status: str = Field("in_cellar", description="Status: 'in_cellar', 'consumed', 'gifted', 'lost'")
    location: Optional[str] = Field(None, description="Storage location (e.g., Cellar, Wine rack)")
    bin: Optional[str] = Field(None, description="Specific bin/rack position")
    purchase_date: Optional[date] = Field(None, description="Date of purchase")
    purchase_price: Optional[float] = Field(None, description="Purchase price per bottle")
    currency: str = Field("RON", description="Currency code (e.g., RON, EUR, USD)")
    store_name: Optional[str] = Field(None, description="Retailer/store name where purchased")
    consumed_date: Optional[date] = Field(None, description="Date consumed (if status is 'consumed')")
    bottle_note: Optional[str] = Field(None, description="Notes specific to this bottle")
    created_at: Optional[datetime] = Field(None, description="Record creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Record last update timestamp")

    # Related objects (not in DB, populated via joins)
    wine_name: Optional[str] = Field(None, description="Wine name (populated via join)")
    producer_name: Optional[str] = Field(None, description="Producer name (populated via join)")
    vintage: Optional[int] = Field(None, description="Vintage year (populated via join)")



class SyncLog(BaseModel):
    """Sync operation log model."""
    model_config = ConfigDict(from_attributes=True)

    id: Optional[int] = Field(None, description="Unique identifier")
    source: str = Field("", description="Data source: 'cellar_tracker' or 'vivino'")
    sync_type: str = Field("", description="Sync type: 'initial', 'incremental', or 'manual'")
    sync_started_at: Optional[datetime] = Field(None, description="Timestamp when sync operation started")
    sync_completed_at: Optional[datetime] = Field(None, description="Timestamp when sync operation completed")
    status: str = Field("", description="Sync status: 'success', 'failed', or 'partial'")
    records_processed: int = Field(0, description="Total number of records processed")
    records_imported: int = Field(0, description="Number of new records imported")
    records_updated: int = Field(0, description="Number of existing records updated")
    records_skipped: int = Field(0, description="Number of records skipped")
    records_failed: int = Field(0, description="Number of records that failed to import")
    error_message: Optional[str] = Field(None, description="Error message if sync failed")
    error_details: Optional[str] = Field(None, description="Detailed error information")
    created_at: Optional[datetime] = Field(None, description="Record creation timestamp")



