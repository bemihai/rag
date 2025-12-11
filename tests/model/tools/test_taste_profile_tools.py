"""Test script for get_user_taste_profile tool."""

from src.agents.tools.taste_profile_tools import get_user_taste_profile

print('Testing get_user_taste_profile tool...')
print('=' * 60)

# Run the tool
profile = get_user_taste_profile.invoke({})

# Print key profile info
print(f"Total wines rated: {profile.get('total_wines_rated', 'N/A')}")
print(f"Favorite regions: {[r.get('region') for r in profile.get('favorite_regions', [])]}")
print(f"Favorite varietals: {[v.get('varietal') for v in profile.get('favorite_varietals', [])]}")
print(f"Average rating: {profile.get('average_rating', 'N/A')}")
print(f"Top producers: {[p.get('producer') for p in profile.get('favorite_producers', [])]}")

print('\n' + '=' * 60)
print('✓ get_user_taste_profile tool tested!')

