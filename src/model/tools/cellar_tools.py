"""
Wine agent tools for cellar management.

This module provides tools for querying and managing the user's wine cellar inventory.
All tools operate on local SQLite database - completely free.
"""

from typing import List, Dict, Optional
from datetime import datetime
from langchain_core.tools import tool

from src.database.repository import WineRepository, BottleRepository, StatsRepository
from src.utils import get_default_db_path, logger


@tool
def get_cellar_wines(
    region: Optional[str] = None,
    country: Optional[str] = None,
    wine_type: Optional[str] = None,
    varietal: Optional[str] = None,
    vintage_min: Optional[int] = None,
    vintage_max: Optional[int] = None,
    ready_to_drink: bool = False,
    producer: Optional[str] = None,
    limit: int = 50
) -> List[Dict]:
    """Get wines from user's cellar with optional filters.

    Query the local wine cellar database to find wines matching specified criteria.
    All filters are optional and can be combined for precise searching.

    Args:
        region: Filter by wine region/appellation (e.g., "Burgundy", "Piedmont", "Rioja").
                Supports partial matching (e.g., "Burg" matches "Burgundy").
        country: Filter by country (e.g., "France", "Italy", "Spain", "USA").
                Supports partial matching (e.g., "Fran" matches "France").
        wine_type: Filter by wine type. Must be one of: "Red", "White", "Rosé",
                  "Sparkling", "Dessert", "Fortified".
        varietal: Filter by grape variety (e.g., "Pinot Noir", "Cabernet Sauvignon").
                 Supports partial matching.
        vintage_min: Minimum vintage year (inclusive). Example: 2015
        vintage_max: Maximum vintage year (inclusive). Example: 2020
        ready_to_drink: If True, only return wines currently in their drinking window
                       (current year is between drink_from_year and drink_to_year).
        producer: Filter by producer/winery name. Supports partial matching.
        limit: Maximum number of wines to return. Default 50, max 200.

    Returns:
        List of dictionaries, each containing:
        - wine_id: Unique identifier
        - name: Full wine name
        - producer: Producer/winery name
        - vintage: Vintage year (None for non-vintage wines)
        - wine_type: Type of wine (Red, White, etc.)
        - varietal: Grape variety/varieties
        - appellation: Specific appellation
        - region: Wine region
        - country: Country of origin
        - quantity: Number of bottles owned
        - location: Cellar location (e.g., "Rack A3")
        - drinking_window: String representation of optimal drinking period
        - drink_status: One of "ready", "aging", "past_peak", "unknown"
        - personal_rating: User's rating (0-100 scale) if tasted
        - purchase_price: Purchase price per bottle if available

    Example:
        >>> wines = get_cellar_wines(region="Burgundy", ready_to_drink=True)
        >>> wines = get_cellar_wines(wine_type="Red", vintage_min=2015, vintage_max=2020)
        >>> wines = get_cellar_wines(producer="Domaine Leflaive")
        >>> wines = get_cellar_wines(country="France", wine_type="White")

    Notes:
        - Completely free operation (local SQLite query)
        - Returns empty list if no wines match criteria
        - Results ordered by region, then vintage (descending)
    """
    print(f"get_cellar_wines called with region={region}, country={country}, wine_type={wine_type}, varietal={varietal}, "
          f"vintage_min={vintage_min}, vintage_max={vintage_max}, ready_to_drink={ready_to_drink}, producer={producer}, "
          f"limit={limit}")
    try:
        wine_repo = WineRepository(get_default_db_path())
        bottle_repo = BottleRepository(get_default_db_path())

        # Get all wines with filters
        wines = wine_repo.get_all(
            wine_type=wine_type,
            country=country,
            # search=region,
            limit=min(limit, 100)
        )

        results = []
        current_year = datetime.now().year

        for wine in wines:
            # Apply additional filters
            if region and region.lower() not in (wine.region_name or "").lower():
                continue

            if varietal and varietal.lower() not in (wine.varietal or "").lower():
                continue

            if vintage_min and wine.vintage and wine.vintage < vintage_min:
                continue

            if vintage_max and wine.vintage and wine.vintage > vintage_max:
                continue

            # Check drinking window
            if ready_to_drink:
                if not wine.drink_from_year or not wine.drink_to_year:
                    continue
                if not (wine.drink_from_year <= current_year <= wine.drink_to_year):
                    continue

            # Get bottle information
            bottles = bottle_repo.get_by_wine(wine.id, status='in_cellar')
            if not bottles:
                continue  # Skip wines with no bottles in cellar

            # Determine drink status
            if wine.drink_from_year and wine.drink_to_year:
                if current_year < wine.drink_from_year:
                    drink_status = "aging"
                elif current_year > wine.drink_to_year:
                    drink_status = "past_peak"
                else:
                    drink_status = "ready"
            else:
                drink_status = "unknown"

            # Get location from first bottle
            location = bottles[0].location if bottles else None

            # Calculate total quantity
            total_quantity = sum(b.quantity for b in bottles)

            results.append({
                "wine_id": wine.id,
                "name": wine.wine_name,
                "producer": wine.producer_name,
                "vintage": wine.vintage,
                "wine_type": wine.wine_type,
                "varietal": wine.varietal,
                "appellation": wine.appellation,
                "region": wine.region_name,
                "country": wine.country,
                "quantity": total_quantity,
                "location": location,
                "drinking_window": f"{wine.drink_from_year}-{wine.drink_to_year}" if wine.drink_from_year else None,
                "drink_status": drink_status,
                "personal_rating": wine.personal_rating,
                "purchase_price": bottles[0].purchase_price if bottles else None
            })

        # Sort by region, then vintage
        results.sort(key=lambda x: (x["region"] or "", -(x["vintage"] or 0)))

        logger.info(f"Found {len(results)} wines matching criteria")
        return results

    except Exception as e:
        logger.error(f"Error getting cellar wines: {e}")
        return []


@tool
def get_wine_details(
    wine_id: Optional[int] = None,
    wine_name: Optional[str] = None,
    vintage: Optional[int] = None
) -> Dict:
    """Get detailed information about a specific wine in the cellar.

    Retrieve comprehensive details for a single wine, including inventory,
    tasting notes, ratings, and purchase information.

    Args:
        wine_id: Unique wine identifier. Use this if you know the exact ID.
        wine_name: Wine name to search for. Supports partial matching.
                  Example: "Gevrey" will match "Gevrey-Chambertin"
        vintage: Vintage year to filter by (optional, use with wine_name).
                Example: 2019

    Returns:
        Dictionary containing detailed wine information:
        - wine_id: Unique identifier
        - name: Full wine name
        - producer: Producer/winery name with country
        - vintage: Vintage year
        - wine_type: Type (Red, White, Rosé, Sparkling, Dessert, Fortified)
        - varietal: Grape variety or blend
        - designation: Special designation (e.g., "Reserve", "Grand Cru")
        - appellation: Specific appellation (e.g., "Pouilly-Fumé")
        - vineyard: Specific vineyard name if applicable
        - region: Full region (primary + secondary)
        - country: Country of origin
        - bottle_size: Bottle size (e.g., "750ml", "1.5L")
        - alcohol_content: ABV percentage

        Inventory details:
        - quantity_owned: Current number of bottles owned
        - quantity_consumed: Total bottles consumed
        - quantity_purchased: Total bottles ever purchased
        - location: Cellar location (e.g., "Rack A3, Shelf 2")
        - purchase_date: When purchased
        - purchase_price: Price paid per bottle

        Drinking window:
        - drink_from_year: Start of optimal drinking period
        - drink_to_year: End of optimal drinking period
        - drink_status: Current status ("ready", "aging", "past_peak", "unknown")
        - drink_index: Drinkability score (0-10)

        Tasting information:
        - personal_rating: User's rating (0-100 scale)
        - community_rating: Average community rating (0-100 scale)
        - tasting_notes: User's personal tasting notes
        - last_tasted_date: Date of most recent tasting
        - is_defective: Whether bottle was defective
        - do_like: Simple like/dislike indicator

    Raises:
        ValueError: If neither wine_id nor wine_name is provided

    Example:
        >>> wine = get_wine_details(wine_id=42)
        >>> wine = get_wine_details(wine_name="Gevrey-Chambertin", vintage=2019)

    Notes:
        - Returns most recent match if multiple wines found with same name
        - Returns None values for missing data (e.g., not yet tasted)
        - Completely free operation (local SQLite query)
    """
    try:
        if not wine_id and not wine_name:
            return {"error": "Must provide either wine_id or wine_name"}

        wine_repo = WineRepository(get_default_db_path())
        bottle_repo = BottleRepository(get_default_db_path())

        # Get wine
        if wine_id:
            wine = wine_repo.get_by_id(wine_id)
        else:
            # Search by name
            wines = wine_repo.get_all(search=wine_name, limit=10)
            if vintage:
                wines = [w for w in wines if w.vintage == vintage]
            wine = wines[0] if wines else None

        if not wine:
            return {"error": "Wine not found"}

        # Get bottles
        bottles = bottle_repo.get_by_wine(wine.id)
        in_cellar_bottles = [b for b in bottles if b.status == 'in_cellar']
        consumed_bottles = [b for b in bottles if b.status == 'consumed']

        # Determine drink status
        current_year = datetime.now().year
        if wine.drink_from_year and wine.drink_to_year:
            if current_year < wine.drink_from_year:
                drink_status = "aging"
            elif current_year > wine.drink_to_year:
                drink_status = "past_peak"
            else:
                drink_status = "ready"
        else:
            drink_status = "unknown"

        # Get locations (unique)
        locations = list(set(b.location for b in in_cellar_bottles if b.location))

        return {
            # Basic info
            "wine_id": wine.id,
            "name": wine.wine_name,
            "producer": wine.producer_name,
            "vintage": wine.vintage,
            "wine_type": wine.wine_type,
            "varietal": wine.varietal,
            "designation": wine.designation,
            "appellation": wine.appellation,
            "vineyard": wine.vineyard,
            "region": wine.region_name,
            "country": wine.country,
            "bottle_size": wine.bottle_size,

            # Inventory
            "quantity_owned": sum(b.quantity for b in in_cellar_bottles),
            "quantity_consumed": wine.q_consumed,
            "quantity_purchased": wine.q_purchased,
            "location": ", ".join(locations) if locations else None,
            "purchase_date": in_cellar_bottles[0].purchase_date if in_cellar_bottles else None,
            "purchase_price": in_cellar_bottles[0].purchase_price if in_cellar_bottles else None,

            # Drinking window
            "drink_from_year": wine.drink_from_year,
            "drink_to_year": wine.drink_to_year,
            "drink_status": drink_status,
            "drink_index": wine.drink_index,

            # Tasting
            "personal_rating": wine.personal_rating,
            "community_rating": wine.community_rating,
            "tasting_notes": wine.tasting_notes,
            "last_tasted_date": str(wine.last_tasted_date) if wine.last_tasted_date else None,
        }

    except Exception as e:
        logger.error(f"Error getting wine details: {e}")
        return {"error": str(e)}


@tool
def get_cellar_statistics() -> Dict:
    """Get comprehensive statistics about the wine cellar collection.

    Retrieve overview statistics, composition breakdown, and collection insights.

    Returns:
        Dictionary containing cellar statistics:

        Overview:
        - total_bottles: Total number of bottles in cellar
        - unique_wines: Number of unique wine entries
        - total_value: Estimated total collection value
        - average_bottle_price: Average price per bottle

        By wine type:
        - by_type: Dict with counts for Red, White, Rosé, Sparkling, etc.
        - type_percentages: Dict with percentage breakdown by type

        By region:
        - by_region: Dict with top 10 regions and bottle counts
        - by_country: Dict with country distribution

        By vintage:
        - oldest_vintage: Oldest vintage in collection
        - newest_vintage: Newest vintage in collection
        - average_vintage: Average vintage year
        - vintage_distribution: Dict of vintages and counts

        Drinking windows:
        - ready_to_drink: Number of bottles in drinking window
        - still_aging: Number of bottles not yet ready
        - past_peak: Number of bottles past optimal window
        - unknown_window: Bottles without drinking window data

        Value insights:
        - most_expensive: Details of most expensive bottle
        - total_invested: Total amount spent on collection
        - appreciation_estimate: Estimated value increase

        Top producers:
        - top_producers: List of top 5 producers by bottle count

    Example:
        >>> stats = get_cellar_statistics()
        >>> print(f"Total bottles: {stats['total_bottles']}")
        >>> print(f"Ready to drink: {stats['ready_to_drink']}")

    Notes:
        - Completely free operation (local SQLite aggregations)
        - Updates in real-time based on current database state
        - Useful for collection overview and analysis
    """
    try:
        stats_repo = StatsRepository(get_default_db_path())
        wine_repo = WineRepository(get_default_db_path())

        # Get basic overview
        overview = stats_repo.get_cellar_overview()

        # Calculate drinking window stats
        wines = wine_repo.get_all()
        current_year = datetime.now().year

        ready = sum(1 for w in wines if w.drink_from_year and w.drink_to_year
                   and w.drink_from_year <= current_year <= w.drink_to_year and w.q_quantity > 0)
        aging = sum(1 for w in wines if w.drink_from_year and current_year < w.drink_from_year
                   and w.q_quantity > 0)
        past_peak = sum(1 for w in wines if w.drink_to_year and current_year > w.drink_to_year
                       and w.q_quantity > 0)
        unknown = sum(1 for w in wines if (not w.drink_from_year or not w.drink_to_year)
                     and w.q_quantity > 0)

        # Calculate type percentages
        total = overview['total_bottles']
        type_percentages = {}
        if total > 0:
            for type_info in overview['by_type']:
                type_percentages[type_info['wine_type']] = round(
                    (type_info['bottles'] / total) * 100, 1
                )

        return {
            # Overview
            "total_bottles": overview['total_bottles'],
            "unique_wines": overview['unique_wines'],

            # By type
            "by_type": overview['by_type'],
            "type_percentages": type_percentages,

            # By country
            "by_country": overview['by_country'],

            # Drinking windows
            "ready_to_drink": ready,
            "still_aging": aging,
            "past_peak": past_peak,
            "unknown_window": unknown,
        }

    except Exception as e:
        logger.error(f"Error getting cellar statistics: {e}")
        return {"error": str(e)}


@tool
def find_wines_by_location(location: str) -> List[Dict]:
    """Find all wines stored at a specific cellar location.

    Useful for physical cellar management and inventory checks.

    Args:
        location: Cellar location identifier. Examples:
                 - "Rack A3" (specific rack)
                 - "A" (all locations starting with A)
                 - "Shelf 2" (specific shelf)
                 Supports partial matching.

    Returns:
        List of dictionaries containing:
        - wine_id: Unique identifier
        - name: Wine name
        - producer: Producer name
        - vintage: Vintage year
        - wine_type: Type of wine
        - quantity: Number of bottles at this location
        - exact_location: Full location string
        - drinking_window: Optimal drinking period
        - drink_status: Current drinking status

    Example:
        >>> wines = find_wines_by_location("Rack A3")
        >>> wines = find_wines_by_location("A")  # All A racks

    Notes:
        - Returns empty list if location not found
        - Results ordered by wine name
        - Completely free operation (local SQLite query)
    """
    try:
        bottle_repo = BottleRepository(get_default_db_path())
        wine_repo = WineRepository(get_default_db_path())

        # Get inventory filtered by location
        inventory = bottle_repo.get_inventory(location=location)

        results = []
        current_year = datetime.now().year

        for item in inventory:
            wine = wine_repo.get_by_id(item['wine_id'])
            if not wine:
                continue

            # Determine drink status
            if wine.drink_from_year and wine.drink_to_year:
                if current_year < wine.drink_from_year:
                    drink_status = "aging"
                elif current_year > wine.drink_to_year:
                    drink_status = "past_peak"
                else:
                    drink_status = "ready"
            else:
                drink_status = "unknown"

            results.append({
                "wine_id": wine.id,
                "name": wine.wine_name,
                "producer": wine.producer_name,
                "vintage": wine.vintage,
                "wine_type": wine.wine_type,
                "quantity": item.get('quantity', 0),
                "exact_location": item.get('location'),
                "drinking_window": f"{wine.drink_from_year}-{wine.drink_to_year}" if wine.drink_from_year else None,
                "drink_status": drink_status
            })

        # Sort by wine name
        results.sort(key=lambda x: x["name"])

        logger.info(f"Found {len(results)} wines at location '{location}'")
        return results

    except Exception as e:
        logger.error(f"Error finding wines by location: {e}")
        return []

