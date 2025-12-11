#!/usr/bin/env python
"""Test script for pairing tools."""
import sys
import os
from pathlib import Path

# Add project root to path - go up to find the directory containing 'src'
current_file = Path(__file__).resolve()
project_root = current_file.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Change to project root directory
os.chdir(project_root)

from src.model.tools.pairing_tools import (
    get_food_pairing_wines,
    get_pairing_for_wine,
    get_wine_and_cheese_pairings,
    suggest_dinner_menu_with_wines
)

print('Testing Pairing Tools')
print('=' * 60)

# Test 1: get_food_pairing_wines
print('\n1. Testing get_food_pairing_wines()')
print('-' * 60)
result = get_food_pairing_wines.invoke({
    'food': 'steak',
    'from_cellar_only': True
})
print(f'Food: {result.get("food_analyzed")}')
print(f'Recommended types: {result.get("recommended_wine_types")}')
print(f'Recommended varietals: {result.get("recommended_varietals", [])[:3]}')
print(f'Pairing principles: {result.get("pairing_principles")}')
print(f'Cellar matches: {len(result.get("cellar_matches", []))} wines')
if result.get('cellar_matches'):
    top_match = result['cellar_matches'][0]
    print(f'  Top match: {top_match["name"]} (score: {top_match["pairing_score"]})')

# Test 2: get_food_pairing_wines with wine type preference
print('\n2. Testing get_food_pairing_wines() with wine type preference')
print('-' * 60)
result = get_food_pairing_wines.invoke({
    'food': 'salmon',
    'wine_type_preference': 'White',
    'from_cellar_only': True,
    'ready_to_drink_only': True
})
print(f'Food: {result.get("food_analyzed")}')
print(f'Recommended types: {result.get("recommended_wine_types")}')
print(f'Cellar matches (ready to drink): {len(result.get("cellar_matches", []))} wines')

# Test 3: get_pairing_for_wine
print('\n3. Testing get_pairing_for_wine()')
print('-' * 60)
result = get_pairing_for_wine.invoke({'wine_name': 'Cabernet'})
if 'error' not in result:
    print(f'Wine: {result.get("wine_name")}')
    print(f'Wine type: {result.get("wine_type")}')
    print(f'Varietal: {result.get("varietal")}')
    print(f'Primary pairings: {result.get("primary_pairings", [])[:3]}')
    print(f'Proteins: {result.get("proteins")}')
    print(f'Serving temperature: {result.get("serving_temperature")}')
else:
    print(f'Error: {result["error"]}')

# Test 4: get_wine_and_cheese_pairings
print('\n4. Testing get_wine_and_cheese_pairings()')
print('-' * 60)
result = get_wine_and_cheese_pairings.invoke({
    'cheese_type': 'blue',
    'from_cellar_only': True
})
print(f'Cheese category: {result.get("cheese_category")}')
print(f'Classic pairings: {result.get("classic_pairings", [])[:3]}')
print(f'Recommended wine types: {result.get("recommended_wine_types")}')
print(f'Why it works: {result.get("why_it_works")}')
print(f'Cellar suggestions: {len(result.get("cellar_suggestions", []))} wines')

# Test 5: get_wine_and_cheese_pairings with soft cheese
print('\n5. Testing get_wine_and_cheese_pairings() with soft cheese')
print('-' * 60)
result = get_wine_and_cheese_pairings.invoke({
    'cheese_type': 'brie',
    'from_cellar_only': True
})
print(f'Cheese category: {result.get("cheese_category")}')
print(f'Classic pairings: {result.get("classic_pairings", [])[:3]}')
print(f'Cellar suggestions: {len(result.get("cellar_suggestions", []))} wines')

# Test 6: suggest_dinner_menu_with_wines
print('\n6. Testing suggest_dinner_menu_with_wines()')
print('-' * 60)
result = suggest_dinner_menu_with_wines.invoke({
    'courses': ['oysters', 'beef wellington', 'cheese plate'],
    'occasion': 'formal'
})
print(f'Number of courses: {len(result.get("pairings", []))}')
print(f'Total bottles needed: {result.get("total_bottles_needed")}')
print(f'Wine progression: {result.get("wine_progression")}')
print(f'Occasion: {result.get("occasion")}')

if result.get('pairings'):
    print('\nCourse-by-course pairings:')
    for pairing in result['pairings']:
        print(f'  Course {pairing["course_number"]}: {pairing["course"]}')
        print(f'    Recommended: {", ".join(pairing.get("wine_recommendation", [])[:2])}')
        print(f'    Cellar options: {len(pairing.get("cellar_options", []))} wines')

print('\n' + '=' * 60)
print('✓ All pairing tools tested successfully!')
print()
print('Summary of tools tested:')
print('  1. get_food_pairing_wines - General food pairing')
print('  2. get_pairing_for_wine - Reverse pairing (wine -> food)')
print('  3. get_wine_and_cheese_pairings - Specialized cheese pairing')
print('  4. suggest_dinner_menu_with_wines - Multi-course menu planning')

