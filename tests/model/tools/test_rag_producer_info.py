"""Test script for search_wine_producer_info tool."""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from src.model.tools.rag_tools import search_wine_producer_info

print('Testing search_wine_producer_info tool...')
print('=' * 60)

# Test 1: Famous Burgundy producer
print('1. Domaine de la Romanée-Conti:')
result = search_wine_producer_info.invoke({'producer': 'Domaine de la Romanée-Conti'})
print(result[:500] + ('...' if len(result) > 500 else ''))

# Test 2: Italian producer
print('\n2. Gaja:')
result = search_wine_producer_info.invoke({'producer': 'Gaja'})
print(result[:500] + ('...' if len(result) > 500 else ''))

# Test 3: Bordeaux château
print('\n3. Château Margaux:')
result = search_wine_producer_info.invoke({'producer': 'Château Margaux'})
print(result[:500] + ('...' if len(result) > 500 else ''))

print('\n' + '=' * 60)
print('✓ search_wine_producer_info tool tested!')

