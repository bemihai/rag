#!/usr/bin/env python
"""Test script for get_owned_quantity method in BottleRepository."""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.database.repository import BottleRepository
from src.utils import get_default_db_path

print('Testing get_owned_quantity method...')
print('=' * 60)

bottle_repo = BottleRepository(get_default_db_path())

# Test with a few wine IDs
test_wine_ids = [1, 2, 3, 4, 5]

for wine_id in test_wine_ids:
    quantity = bottle_repo.get_owned_quantity(wine_id)
    print(f'Wine ID {wine_id}: {quantity} bottles owned')

print()
print('=' * 60)
print('✓ get_owned_quantity method tested!')

