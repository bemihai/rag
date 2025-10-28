# CellarTracker Import - Quick Start

## 🚀 Quick Setup (5 minutes)

### 1. Install Dependencies

```bash
pip install cellartracker python-dateutil
```

### 2. Set Credentials

Create or edit `.env` file:

```env
CELLARTRACKER_USERNAME=your_username
CELLARTRACKER_PASSWORD=your_password
```

### 3. Run Import

```bash
# First time - initialize database
python -m src.etl.import_cellartracker --init-db

# Subsequent imports
python -m src.etl.import_cellartracker
```

## 📊 What You Get

- ✅ All your wines from CellarTracker
- ✅ Current inventory with locations
- ✅ Drinking history (consumed bottles)
- ✅ Your tasting notes and ratings
- ✅ Purchase information
- ✅ Unified database ready for queries

## 🔄 Regular Updates

Run weekly to keep data fresh:

```bash
python -m src.etl.import_cellartracker
```

## 🧪 Test with Sample Data

Test the importer without API credentials:

```bash
python -m src.etl.test_cellartracker_import
```

This uses the JSON files in `data/cellar-tracker/` directory.

## 📚 Full Documentation

See [cellartracker-import.md](cellartracker-import.md) for:
- Detailed field mappings
- Programmatic usage
- Troubleshooting
- Advanced options

## 🆘 Need Help?

Common issues:

**Authentication failed**
- Check username/password in `.env`
- Verify CellarTracker account is active

**Database errors**
- Run with `--init-db` flag first time
- Check file permissions on database

**Import is slow**
- Use `--inventory-only` for faster sync
- CellarTracker API may be rate-limited

