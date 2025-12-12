#!/usr/bin/env python
"""Test script for get_cellar_statistics tool."""

from src.agents.tools.cellar_tools import get_cellar_statistics

print('Testing get_cellar_statistics tool...')
print('=' * 60)

# Run the tool
stats = get_cellar_statistics.invoke({})

# Print key statistics
print(f"Total bottles: {stats.get('total_bottles', 'N/A')}")
print(f"Unique wines: {stats.get('unique_wines', 'N/A')}")
print(f"Ready to drink: {stats.get('ready_to_drink', 'N/A')}")
print(f"Still aging: {stats.get('still_aging', 'N/A')}")
print(f"Past peak: {stats.get('past_peak', 'N/A')}")
print(f"Unknown window: {stats.get('unknown_window', 'N/A')}")

print('\nWine type breakdown:')
for t in stats.get('by_type', []):
    print(f"  {t['wine_type']}: {t['bottles']} bottles")

print('\nCountry breakdown:')
for c in stats.get('by_country', []):
    print(f"  {c['country']}: {c['bottles']} bottles")

print('\nType percentages:')
for k, v in stats.get('type_percentages', {}).items():
    print(f"  {k}: {v}%")

print('\n' + '=' * 60)
print('✓ get_cellar_statistics tool tested!')

