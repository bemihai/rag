#!/usr/bin/env python
"""Test script for get_wine_details tool."""

from src.agents.tools.cellar_tools import get_wine_details

print('Testing get_wine_details tool...')
print('=' * 60)

print('1. Get wine details by wine name and vintage:')
wine = get_wine_details.invoke({'wine_name': "Smerenie", 'vintage': 2019})
print(f'   Wine: {wine.get("name", "Not found")}, Producer: {wine.get("producer", "N/A")}, Vintage: {wine.get("vintage", "N/A")}')

print('\n2. Get wine details by wine_name (partial match):')
wine = get_wine_details.invoke({'wine_name': 'Barolo'})
print(f'   Wine: {wine.get("name", "Not found")}, Producer: {wine.get("producer", "N/A")}, Vintage: {wine.get("vintage", "N/A")}')

print('\n3. Get wine details by wine_name and vintage:')
wine = get_wine_details.invoke({'wine_name': 'Barolo', 'vintage': 2018})
print(f'   Wine: {wine.get("name", "Not found")}, Producer: {wine.get("producer", "N/A")}, Vintage: {wine.get("vintage", "N/A")}')

print('\n' + '=' * 60)
print('✓ get_wine_details tool tested!')
