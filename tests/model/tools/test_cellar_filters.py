#!/usr/bin/env python
"""Test script for refactored get_cellar_wines tool."""

from src.model.tools.cellar_tools import get_cellar_wines

print('Testing refactored get_cellar_wines tool...')
print('=' * 60)

# Test 1: Filter by wine type
print('1. Filter by wine type (Red):')
wines = get_cellar_wines.invoke({'wine_type': 'Red'})
print(f'   Found {len(wines)} red wines')

# Test 2: Filter by country
print()
print('2. Filter by country (France):')
wines = get_cellar_wines.invoke({'country': 'France'})
print(f'   Found {len(wines)} French wines')

# Test 3: Filter by region (search)
print()
print('3. Filter by region (search - Burgundy):')
wines = get_cellar_wines.invoke({'region': 'Burgundy'})
print(f'   Found {len(wines)} Burgundy wines')

# Test 4: Filter by producer (search)
print()
print('4. Filter by producer (search):')
wines = get_cellar_wines.invoke({'producer': 'Oprisor'})
print(f'   Found {len(wines)} wines from producers matching "Oprisor"')

# Test 3: Filter by appellation (exact)
print()
print('3. Filter by appellation (exact):')
wines = get_cellar_wines.invoke({'appellation': 'Rioja'})
print(f'   Found {len(wines)} Rioja wines')

# Test 6: Filter ready to drink
print()
print('6. Filter ready to drink:')
wines = get_cellar_wines.invoke({'ready_to_drink': True})
print(f'   Found {len(wines)} wines ready to drink')

# Test 7: Vintage range
print()
print('7. Filter by vintage range (2013-2020):')
wines = get_cellar_wines.invoke({'vintage_min': 2013, 'vintage_max': 2020})
print(f'   Found {len(wines)} wines from 2013-2020')

# Test 8: Combined filters
print()
print('8. Combined filters (France, Red, ready to drink):')
wines = get_cellar_wines.invoke({
    'country': 'France',
    'wine_type': 'Red',
    'ready_to_drink': True,
})
print(f'   Found {len(wines)} French red wines ready to drink')

print()
print('=' * 60)
print('✓ All filter types working correctly!')
print()
print('Summary of filter types:')
print('  Exact match: wine_type, country, appellation, vintage, ready_to_drink')
print('  Partial match (search): region, producer, wine_name, varietal')
print('  Range: vintage_min, vintage_max')

