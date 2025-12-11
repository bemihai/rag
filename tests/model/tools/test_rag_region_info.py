"""Test script for search_wine_region_info tool."""

from src.model.tools.rag_tools import search_wine_region_info

print('Testing search_wine_region_info tool...')
print('=' * 60)

# Test 1: Classic region
print('1. Burgundy region:')
result = search_wine_region_info.invoke({'region': 'Burgundy'})
print(result[:500] + ('...' if len(result) > 500 else ''))

# Test 2: Modern region
print('\n2. Napa Valley region:')
result = search_wine_region_info.invoke({'region': 'Napa Valley'})
print(result[:500] + ('...' if len(result) > 500 else ''))

# Test 3: Appellation
print('\n3. Barolo region:')
result = search_wine_region_info.invoke({'region': 'Barolo'})
print(result[:500] + ('...' if len(result) > 500 else ''))

print('\n' + '=' * 60)
print('✓ search_wine_region_info tool tested!')

