# CellarTracker Import Guide

**Date:** October 28, 2025  
**Purpose:** Import wine data from CellarTracker API into unified wine database

---

## Overview

The CellarTracker importer fetches data from your CellarTracker account and imports it into the local SQLite database. It handles:

- Wine catalog (from wine list)
- Current inventory (bottles in cellar)
- Consumed bottles (drinking history)
- Tasting notes and ratings
- Purchase history

---

## Prerequisites

### 1. Install Dependencies

The cellartracker package needs to be installed:

```bash
pip install cellartracker
```

Or if using the project's pyproject.toml:

```bash
pip install -e .
```

### 2. CellarTracker Credentials

You need a CellarTracker account with API access. Set up credentials:

**Option A: Environment Variables (Recommended)**

Create or edit `.env` file in project root:

```env
CELLARTRACKER_USERNAME=your_username
CELLARTRACKER_PASSWORD=your_password
```

**Option B: Command Line Arguments**

Pass credentials directly when running the import:

```bash
python -m src.etl.import_cellartracker --username your_username --password your_password
```

---

## Usage

### Full Import

Import all data (wines, inventory, consumed, notes, purchases):

```bash
python -m src.etl.import_cellartracker
```

### Inventory Only

Import only current inventory (faster, skips history):

```bash
python -m src.etl.import_cellartracker --inventory-only
```

### Initialize Database First

If this is your first import, initialize the database schema:

```bash
python -m src.etl.import_cellartracker --init-db
```

### Custom Database Path

Use a different database location:

```bash
python -m src.etl.import_cellartracker --db-path /path/to/custom.db
```

---

## What Gets Imported

### Wines Table

From CellarTracker wine list:
- Wine name, producer, vintage
- Wine type, color, varietal, designation
- Region and appellation
- Bottle size
- Drinking window (BeginConsume/EndConsume)

### Bottles Table

From inventory and consumed data:
- Individual bottle tracking
- Storage location and bin
- Purchase information (date, price, store)
- Status (in_cellar, consumed, gifted, lost)
- Consumption details (date, type)

### Tasting Notes

From CellarTracker notes:
- Personal ratings (0-100 scale)
- Tasting notes text
- Tasting dates
- Multiple notes combined chronologically

### Producers & Regions

Automatically created from wine data:
- Producer name and sorting name
- Country information
- Region hierarchy

---

## Data Mapping

### CellarTracker → Database

| CellarTracker Field | Database Field | Notes |
|---------------------|----------------|-------|
| `iWine` | `wines.external_id` | Unique wine identifier |
| `Wine` | `wines.wine_name` | Full wine name |
| `Producer` | `producers.name` | Auto-created if new |
| `SortProducer` | `producers.sort_name` | For alphabetical sorting |
| `Vintage` | `wines.vintage` | Integer, NULL for NV |
| `Type` | `wines.wine_type` | Normalized (Red, White, etc.) |
| `Varietal` | `wines.varietal` | Primary grape variety |
| `Designation` | `wines.designation` | Cuvée name, reserve level |
| `Region` | `regions.name` | Auto-created if new |
| `Appellation` | `wines.appellation` | Specific AOC/DOC |
| `BeginConsume` | `wines.drink_from_year` | Drinking window start |
| `EndConsume` | `wines.drink_to_year` | Drinking window end |
| `Barcode` | `bottles.external_bottle_id` | Unique bottle identifier |
| `Location` | `bottles.location` | Cellar location |
| `Bin` | `bottles.bin` | Specific bin/rack |
| `PurchaseDate` | `bottles.purchase_date` | ISO format |
| `BottleCost`/`Price` | `bottles.purchase_price` | Decimal |
| `Currency` | `bottles.currency` | Currency code |
| `Store`/`StoreName` | `bottles.store_name` | Purchase location |
| `Rating` | `wines.personal_rating` | 0-100 scale |
| `Note` | `wines.tasting_notes` | Tasting note text |
| `TastingDate` | `wines.last_tasted_date` | Most recent tasting |

### Bottle Status Mapping

| CellarTracker | Database Status | Consumption Type |
|---------------|-----------------|------------------|
| In inventory | `in_cellar` | NULL |
| Drank | `consumed` | `drank` |
| Gifted | `gifted` | `gifted` |
| Spoiled/Dumped | `lost` | `spoiled` |

---

## Import Statistics

After import, you'll see a summary like:

```
============================================================
IMPORT SUMMARY
============================================================
Wines processed:      150
  - Imported:         120
  - Updated:          30
  - Skipped:          0

Bottles processed:    200
  - Imported:         175
  - Updated:          25

Producers created:    45
Regions created:      18
Notes processed:      35

Errors:               0
============================================================
```

---

## Programmatic Usage

You can also use the importer in your own Python scripts:

```python
from src.etl.cellartracker_importer import CellarTrackerImporter

# Create importer
importer = CellarTrackerImporter(
    username='your_username',
    password='your_password',
    db_path='data/wine_cellar.db'
)

# Full import
stats = importer.import_all()

# Or inventory only
stats = importer.import_inventory_only()

# Check results
print(f"Imported {stats['wines_imported']} wines")
print(f"Imported {stats['bottles_imported']} bottles")
```

---

## Data Synchronization

### Initial Import

First time importing from CellarTracker:

```bash
python -m src.etl.import_cellartracker --init-db
```

This creates the database schema and imports all data.

### Incremental Updates

To update with new data:

```bash
python -m src.etl.import_cellartracker
```

The importer uses `source` and `external_id` to match existing records:
- Existing wines/bottles are **updated** with latest data
- New wines/bottles are **inserted**
- Tasting notes are **appended** chronologically

### Sync Log

All imports are logged in the `sync_log` table:

```sql
SELECT * FROM sync_log ORDER BY sync_started_at DESC LIMIT 5;
```

This tracks:
- Import start/end times
- Records processed/imported/updated
- Success/failure status
- Error messages

---

## API Endpoints Used

The importer calls these CellarTracker API methods:

| Method | Purpose | Used For |
|--------|---------|----------|
| `get_list()` | Wine catalog | Wine details |
| `get_inventory()` | Current inventory | In-cellar bottles |
| `get_consumed()` | Drinking history | Consumed bottles |
| `get_notes()` | Tasting notes | Ratings and notes |
| `get_purchase()` | Purchase history | Supplementary data |

---

## Troubleshooting

### Authentication Errors

```
Error: Invalid credentials
```

**Solution:** Check username/password in `.env` or command line arguments.

### Missing Wine Data

Some bottles imported but wine details missing.

**Solution:** Run full import (not `--inventory-only`) to fetch wine catalog first.

### Duplicate Bottles

Same bottle appearing multiple times.

**Solution:** This shouldn't happen as barcodes are unique. Check for data inconsistencies in CellarTracker.

### Slow Import

Import taking too long.

**Solution:** 
- Use `--inventory-only` for faster sync
- CellarTracker API may be slow, be patient
- Check network connection

### Database Locked

```
Error: database is locked
```

**Solution:** Close any other applications accessing the database (including DB browsers).

---

## Best Practices

1. **Regular Syncs**: Run import weekly to keep data fresh
2. **Backup First**: Backup database before major imports
3. **Check Logs**: Review sync_log table for issues
4. **Test Inventory-Only**: Use faster inventory-only mode for quick updates
5. **Monitor Errors**: Check error count in import summary

---

## Next Steps

After importing CellarTracker data:

1. **View Data**: Use the Streamlit UI to browse your cellar
2. **Combine Sources**: Import Vivino data for community ratings and images
3. **Query**: Run SQL queries on the unified database
4. **RAG Pipeline**: Use imported data for wine recommendations

---

## Related Documentation

- [Unified Schema Design](unified-schema-design.md)
- [Database Models](../src/database/models.py)
- [Vivino Import Guide](vivino-import.md) *(to be created)*

