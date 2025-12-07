"""
Wine agent tools for taste profile analysis.

This module provides tools for analyzing user's wine preferences based on
tasting history from CellarTracker and Vivino imports stored in local database.
"""

from typing import Dict, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict
import statistics
from langchain_core.tools import tool

from src.database.repository import TastingRepository, WineRepository, BottleRepository
from src.utils import get_default_db_path, logger


@tool
def get_user_taste_profile() -> Dict:
    """Get comprehensive user wine taste profile based on tasting history.

    Analyzes all consumed wines and ratings to build a detailed preference model.
    Uses data from both CellarTracker and Vivino imports stored in local database.

    Returns:
        Dictionary containing taste profile information with summary stats,
        favorite regions/countries/varietals/producers, wine type preferences,
        rating patterns, and more.

    Example:
        >>> profile = get_user_taste_profile()
        >>> print(f"Favorite region: {profile['favorite_regions'][0]['region']}")
        >>> print(f"Average rating: {profile['average_rating']:.1f}/100")

    Notes:
        - Returns empty/default values if no tasting history exists
        - Only includes wines with personal ratings
        - Completely free operation (local database aggregation)
    """
    try:
        tasting_repo = TastingRepository(get_default_db_path())

        # Get all tastings with wine info
        tastings = tasting_repo.get_all_with_wine_info(has_rating=True)

        if not tastings:
            return {
                "total_wines_rated": 0,
                "total_wines_consumed": 0,
                "message": "No tasting history available"
            }

        # Calculate basic stats
        ratings = [t['personal_rating'] for t in tastings if t.get('personal_rating')]
        total_rated = len(ratings)
        avg_rating = sum(ratings) / total_rated if total_rated > 0 else 0
        std_dev = statistics.stdev(ratings) if len(ratings) > 1 else 0

        # Aggregate by region
        region_stats = defaultdict(lambda: {'ratings': [], 'count': 0})
        for t in tastings:
            if t.get('region_name'):
                region_stats[t['region_name']]['ratings'].append(t.get('personal_rating', 0))
                region_stats[t['region_name']]['count'] += 1

        favorite_regions = [
            {
                'region': region,
                'avg_rating': sum(stats['ratings']) / len(stats['ratings']),
                'count': stats['count'],
                'percentage': round((stats['count'] / total_rated) * 100, 1)
            }
            for region, stats in region_stats.items()
        ]
        favorite_regions.sort(key=lambda x: (x['avg_rating'], x['count']), reverse=True)

        # Aggregate by country
        country_stats = defaultdict(lambda: {'ratings': [], 'count': 0})
        for t in tastings:
            if t.get('country'):
                country_stats[t['country']]['ratings'].append(t.get('personal_rating', 0))
                country_stats[t['country']]['count'] += 1

        favorite_countries = [
            {
                'country': country,
                'avg_rating': sum(stats['ratings']) / len(stats['ratings']),
                'count': stats['count']
            }
            for country, stats in country_stats.items()
        ]
        favorite_countries.sort(key=lambda x: (x['avg_rating'], x['count']), reverse=True)

        # Aggregate by varietal
        varietal_stats = defaultdict(lambda: {'ratings': [], 'count': 0})
        for t in tastings:
            if t.get('varietal'):
                varietal_stats[t['varietal']]['ratings'].append(t.get('personal_rating', 0))
                varietal_stats[t['varietal']]['count'] += 1

        favorite_varietals = [
            {
                'varietal': varietal,
                'avg_rating': sum(stats['ratings']) / len(stats['ratings']),
                'count': stats['count'],
                'preference_strength': min(100, int((sum(stats['ratings']) / len(stats['ratings'])) * (stats['count'] / total_rated) * 10))
            }
            for varietal, stats in varietal_stats.items()
        ]
        favorite_varietals.sort(key=lambda x: x['preference_strength'], reverse=True)

        # Aggregate by producer
        producer_stats = defaultdict(lambda: {'ratings': [], 'count': 0})
        for t in tastings:
            if t.get('producer_name'):
                producer_stats[t['producer_name']]['ratings'].append(t.get('personal_rating', 0))
                producer_stats[t['producer_name']]['count'] += 1

        favorite_producers = [
            {
                'producer': producer,
                'avg_rating': sum(stats['ratings']) / len(stats['ratings']),
                'count': stats['count']
            }
            for producer, stats in producer_stats.items()
        ]
        favorite_producers.sort(key=lambda x: (x['avg_rating'], x['count']), reverse=True)

        # Wine type distribution
        type_stats = defaultdict(lambda: {'ratings': [], 'count': 0})
        for t in tastings:
            wine_type = t.get('wine_type', 'Unknown')
            type_stats[wine_type]['ratings'].append(t.get('personal_rating', 0))
            type_stats[wine_type]['count'] += 1

        type_distribution = {wt: round((stats['count'] / total_rated) * 100, 1)
                           for wt, stats in type_stats.items()}
        type_ratings = {wt: sum(stats['ratings']) / len(stats['ratings'])
                       for wt, stats in type_stats.items()}
        preferred_type = max(type_stats.items(), key=lambda x: x[1]['count'])[0]

        # Rating patterns
        high_rated = sum(1 for r in ratings if r >= 85)
        low_rated = sum(1 for r in ratings if r < 70)
        rating_dist = {
            '90-100': sum(1 for r in ratings if r >= 90),
            '80-89': sum(1 for r in ratings if 80 <= r < 90),
            '70-79': sum(1 for r in ratings if 70 <= r < 80),
            'below 70': sum(1 for r in ratings if r < 70)
        }

        return {
            # Summary
            'total_wines_rated': total_rated,
            'total_wines_consumed': len(tastings),
            'average_rating': round(avg_rating, 1),
            'rating_standard_deviation': round(std_dev, 1),

            # Favorites
            'favorite_regions': favorite_regions[:5],
            'favorite_countries': favorite_countries[:5],
            'favorite_varietals': favorite_varietals[:5],
            'favorite_producers': favorite_producers[:10],

            # Wine type preferences
            'type_distribution': type_distribution,
            'type_ratings': type_ratings,
            'preferred_type': preferred_type,

            # Rating patterns
            'high_rated_count': high_rated,
            'low_rated_count': low_rated,
            'rating_distribution': rating_dist
        }

    except Exception as e:
        logger.error(f"Error getting taste profile: {e}")
        return {"error": str(e)}


@tool
def get_top_rated_wines(
    min_rating: int = 85,
    wine_type: Optional[str] = None,
    limit: int = 10
) -> List[Dict]:
    """Get user's top-rated wines based on personal ratings.

    Retrieve wines that the user rated highly, optionally filtered by wine type.

    Args:
        min_rating: Minimum rating threshold (0-100 scale). Default 85.
        wine_type: Filter by wine type (Red, White, Rosé, Sparkling, etc.).
        limit: Maximum number of wines to return. Default 10, max 50.

    Returns:
        List of dictionaries with wine details, ratings, and cellar status.

    Example:
        >>> top_wines = get_top_rated_wines(min_rating=90)
        >>> top_reds = get_top_rated_wines(min_rating=85, wine_type="Red")

    Notes:
        - Results ordered by rating (descending), then by tasting date
        - Includes wines no longer in cellar (consumed)
    """
    try:
        tasting_repo = TastingRepository(get_default_db_path())
        bottle_repo = BottleRepository(get_default_db_path())

        top_wines = tasting_repo.get_top_rated(
            min_rating=min_rating,
            wine_type=wine_type,
            limit=min(limit, 50)
        )

        results = []
        for wine in top_wines:
            bottles = bottle_repo.get_by_wine(wine['wine_id'], status='in_cellar')
            in_cellar = len(bottles) > 0
            quantity = sum(b.quantity for b in bottles) if bottles else 0

            results.append({
                'wine_id': wine['wine_id'],
                'name': wine.get('wine_name'),
                'producer': wine.get('producer_name'),
                'vintage': wine.get('vintage'),
                'wine_type': wine.get('wine_type'),
                'varietal': wine.get('varietal'),
                'region': wine.get('region_name'),
                'country': wine.get('country'),
                'personal_rating': wine.get('personal_rating'),
                'tasting_notes': wine.get('tasting_notes'),
                'last_tasted_date': str(wine.get('last_tasted_date')) if wine.get('last_tasted_date') else None,
                'in_cellar': in_cellar,
                'quantity_owned': quantity
            })

        logger.info(f"Found {len(results)} top-rated wines")
        return results

    except Exception as e:
        logger.error(f"Error getting top rated wines: {e}")
        return []


@tool
def get_wine_recommendations_from_profile(
    occasion: Optional[str] = None,
    food_pairing: Optional[str] = None,
    price_max: Optional[float] = None,
    from_cellar_only: bool = True
) -> List[Dict]:
    """Get personalized wine recommendations based on user's taste profile.

    Uses taste profile to recommend wines the user is likely to enjoy.

    Args:
        occasion: "everyday", "special", "gift", or None
        food_pairing: Type of food (e.g., "red meat", "fish")
        price_max: Maximum price per bottle
        from_cellar_only: If True, only recommend wines from cellar

    Returns:
        List of recommended wines with predicted ratings and reasons.

    Example:
        >>> recs = get_wine_recommendations_from_profile(food_pairing="steak")

    Notes:
        - Uses collaborative filtering based on rating patterns
        - Returns empty list if insufficient tasting history
    """
    try:
        profile = get_user_taste_profile.invoke({})

        if profile.get('total_wines_rated', 0) < 3:
            return []

        wine_repo = WineRepository(get_default_db_path())
        bottle_repo = BottleRepository(get_default_db_path())

        cellar_wines = wine_repo.get_all()
        recommendations = []
        current_year = datetime.now().year

        fav_regions = {r['region'] for r in profile.get('favorite_regions', [])[:3]}
        fav_varietals = {v['varietal'] for v in profile.get('favorite_varietals', [])[:3]}

        for wine in cellar_wines:
            if wine.q_quantity == 0:
                continue

            similarity = 0
            reasons = []

            if wine.region_name in fav_regions:
                similarity += 0.4
                reasons.append(f"From your favorite region: {wine.region_name}")

            if wine.varietal in fav_varietals:
                similarity += 0.3
                reasons.append(f"Your preferred varietal: {wine.varietal}")

            if wine.wine_type == profile.get('preferred_type'):
                similarity += 0.2
                reasons.append(f"Your preferred wine type: {wine.wine_type}")

            if similarity < 0.3:
                continue

            if price_max:
                bottles = bottle_repo.get_by_wine(wine.id, status='in_cellar')
                if bottles and bottles[0].purchase_price and bottles[0].purchase_price > price_max:
                    continue

            predicted_rating = int(profile['average_rating'] * (0.5 + similarity * 0.5))

            if wine.drink_from_year and wine.drink_to_year:
                if current_year < wine.drink_from_year:
                    drink_status = "aging"
                elif current_year > wine.drink_to_year:
                    drink_status = "past_peak"
                else:
                    drink_status = "ready"
            else:
                drink_status = "unknown"

            bottles = bottle_repo.get_by_wine(wine.id, status='in_cellar')
            location = bottles[0].location if bottles else None

            recommendations.append({
                'wine_id': wine.id,
                'name': wine.wine_name,
                'producer': wine.producer_name,
                'vintage': wine.vintage,
                'wine_type': wine.wine_type,
                'varietal': wine.varietal,
                'region': wine.region_name,
                'predicted_rating': predicted_rating,
                'recommendation_reason': '; '.join(reasons),
                'similarity_score': round(similarity, 2),
                'in_cellar': True,
                'quantity': wine.q_quantity,
                'location': location,
                'drinking_status': drink_status
            })

        recommendations.sort(key=lambda x: (x['predicted_rating'], x['similarity_score']), reverse=True)

        logger.info(f"Generated {len(recommendations)} recommendations")
        return recommendations[:10]

    except Exception as e:
        logger.error(f"Error generating recommendations: {e}")
        return []


@tool
def analyze_rating_trends() -> Dict:
    """Analyze user's wine rating trends over time.

    Provides insights into how preferences and rating patterns evolved.

    Returns:
        Dictionary with temporal trends, recent activity, and exploration patterns.

    Example:
        >>> trends = analyze_rating_trends()
        >>> print(f"Last tasting: {trends['last_tasting_date']}")

    Notes:
        - Requires at least 10 tastings for meaningful analysis
    """
    try:
        tasting_repo = TastingRepository(get_default_db_path())

        tastings = tasting_repo.get_all_with_wine_info(has_rating=True)

        if len(tastings) < 10:
            return {
                'message': 'Insufficient tasting history for trend analysis (minimum 10 required)',
                'total_tastings': len(tastings)
            }

        tastings.sort(key=lambda x: x.get('last_tasted_date') or datetime.min.date())

        last_tasting = tastings[-1].get('last_tasted_date') if tastings else None
        cutoff_date = datetime.now().date() - timedelta(days=30)
        recent = [t for t in tastings if t.get('last_tasted_date') and t.get('last_tasted_date') >= cutoff_date]
        recent_count = len(recent)
        recent_avg = sum(t.get('personal_rating', 0) for t in recent) / recent_count if recent_count > 0 else 0

        first_half = tastings[:len(tastings)//2]
        second_half = tastings[len(tastings)//2:]

        first_avg = sum(t.get('personal_rating', 0) for t in first_half) / len(first_half)
        second_avg = sum(t.get('personal_rating', 0) for t in second_half) / len(second_half)

        if second_avg > first_avg + 3:
            trajectory = "trending up - you're enjoying wines more"
        elif second_avg < first_avg - 3:
            trajectory = "trending down - you're becoming more critical"
        else:
            trajectory = "stable - consistent rating patterns"

        regions = set(t.get('region_name') for t in tastings if t.get('region_name'))
        diversity_score = min(100, int((len(regions) / len(tastings)) * 100 * 2))

        return {
            'last_tasting_date': str(last_tasting) if last_tasting else None,
            'recent_wines_count': recent_count,
            'recent_average_rating': round(recent_avg, 1),
            'rating_trajectory': trajectory,
            'variety_seeking': diversity_score,
            'total_regions_explored': len(regions),
            'rating_calibration': f"{'More generous' if second_avg > first_avg else 'More critical'} over time"
        }

    except Exception as e:
        logger.error(f"Error analyzing rating trends: {e}")
        return {"error": str(e)}


@tool
def compare_wine_to_profile(wine_id: int) -> Dict:
    """Compare a specific wine to user's taste profile.

    Analyzes how well a wine matches user's preferences.

    Args:
        wine_id: Unique identifier of wine to analyze

    Returns:
        Dictionary with match scores, predicted rating, and recommendation.

    Example:
        >>> comparison = compare_wine_to_profile(wine_id=42)
        >>> print(f"Match score: {comparison['overall_match_score']}/100")

    Notes:
        - Useful for deciding whether to open a bottle
        - Requires some tasting history for accurate predictions
    """
    try:
        wine_repo = WineRepository(get_default_db_path())
        profile = get_user_taste_profile.invoke({})

        if profile.get('total_wines_rated', 0) < 3:
            return {'error': 'Insufficient tasting history for comparison'}

        wine = wine_repo.get_by_id(wine_id)
        if not wine:
            return {'error': 'Wine not found'}

        region_match = 0
        varietal_match = 0
        type_match = 0

        fav_regions = profile.get('favorite_regions', [])
        for i, fav in enumerate(fav_regions[:5]):
            if wine.region_name and fav['region'] in wine.region_name:
                region_match = max(region_match, 100 - (i * 15))

        fav_varietals = profile.get('favorite_varietals', [])
        for i, fav in enumerate(fav_varietals[:5]):
            if wine.varietal and fav['varietal'] in wine.varietal:
                varietal_match = max(varietal_match, 100 - (i * 15))

        type_ratings = profile.get('type_ratings', {})
        if wine.wine_type in type_ratings:
            type_match = int((type_ratings[wine.wine_type] / profile['average_rating']) * 100)

        overall_match = int((region_match * 0.4 + varietal_match * 0.3 + type_match * 0.3))
        predicted_rating = int(profile['average_rating'] * (0.7 + (overall_match / 100) * 0.3))

        if overall_match >= 80:
            recommendation = "Highly Recommended"
            confidence = "high"
        elif overall_match >= 60:
            recommendation = "Recommended"
            confidence = "medium"
        elif overall_match >= 40:
            recommendation = "Try"
            confidence = "medium"
        else:
            recommendation = "Not Recommended"
            confidence = "low"

        reasons = []
        if region_match > 50:
            reasons.append(f"Matches your favorite regions")
        if varietal_match > 50:
            reasons.append(f"Your preferred varietal")
        if type_match > 80:
            reasons.append(f"Wine type you highly rate")

        return {
            'wine_name': wine.wine_name,
            'overall_match_score': overall_match,
            'predicted_rating': predicted_rating,
            'confidence_level': confidence,
            'region_match': region_match,
            'varietal_match': varietal_match,
            'type_match': type_match,
            'recommendation': recommendation,
            'reasons': reasons
        }

    except Exception as e:
        logger.error(f"Error comparing wine to profile: {e}")
        return {"error": str(e)}

