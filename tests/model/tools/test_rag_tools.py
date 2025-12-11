"""Test script for search_wine_knowledge tool."""

from src.agents.tools.rag_tools import search_wine_knowledge

print('Testing search_wine_knowledge tool...')
print('=' * 60)

# Test 1: General wine knowledge query
print('1. What is malolactic fermentation?')
result = search_wine_knowledge.invoke({'query': 'What is malolactic fermentation?'})
print(result[:500] + ('...' if len(result) > 500 else ''))

# Test 2: Region comparison
print('\n2. Difference between Burgundy and Bordeaux')
result = search_wine_knowledge.invoke({'query': 'Difference between Burgundy and Bordeaux', 'max_results': 3})
print(result[:500] + ('...' if len(result) > 500 else ''))

# Test 3: Grape variety
print('\n3. Characteristics of Nebbiolo grape')
result = search_wine_knowledge.invoke({'query': 'Characteristics of Nebbiolo grape', 'max_results': 2})
print(result[:500] + ('...' if len(result) > 500 else ''))

print('\n' + '=' * 60)
print('✓ search_wine_knowledge tool tested!')

