"""Helper functions to display cellar statistics and inventory in Streamlit UI."""
import streamlit as st
from src.database.repository import StatsRepository, BottleRepository


def show_cellar_metrics():
    """Display key cellar metrics in a row of streamlit metrics."""
    stats_repo = StatsRepository()

    overview = stats_repo.get_cellar_overview()
    drinking_stats = stats_repo.get_drinking_window_stats()
    value_stats = stats_repo.get_cellar_value()

    # Add a title for the metrics section
    st.markdown("### 📊 Cellar Overview")
    st.markdown("")  # Add spacing

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric(
            label="🍾 Total Bottles",
            value=f"{overview["total_bottles"]:,}",
            delta=f"{overview["unique_wines"]} unique wines"
        )

    with col2:
        top_type = overview["by_type"][0]
        percentage = (top_type["bottles"] / overview["total_bottles"] * 100) if overview["total_bottles"] > 0 else 0
        st.metric(
            label=f"🍷 {top_type["wine_type"]}",
            value=f"{percentage:.1f}%",
            delta=f"{top_type["bottles"]} bottles"
        )

    with col3:
        st.metric(label="✅ Ready to Drink", value=f"{drinking_stats["ready_to_drink"]:,}")

    with col4:
        st.metric(label="⏳ To Hold", value=f"{drinking_stats["to_hold"]:,}")

    with col5:
        primary = value_stats["by_currency"][0]
        st.metric(
            label="💰 Cellar Value",
            value=f"{ primary["currency"]} {primary["total_value"]:,.0f}"
        )


def show_top_rated_consumed_wines():
    """Display the top 5 rated wines consumed by the user."""
    state_repo = StatsRepository()

    # Get top 5 consumed bottles with ratings
    top_wines = state_repo.get_consumed_with_ratings(limit=5)

    if not top_wines:
        st.warning("🍷 No consumed wines with ratings found yet.")
        return

    st.markdown("### 🌟 Your Top 5 Rated Consumed Wines")
    st.markdown("*These are the highest-rated wines you've enjoyed*")
    st.markdown("")  # Add spacing

    for idx, wine_data in enumerate(top_wines, 1):
        rating = wine_data.get("personal_rating", 0)
        wine_name = wine_data.get("wine_name", "Unknown")
        producer_name = wine_data.get("producer_name", "Unknown Producer")
        vintage = wine_data.get("vintage")
        wine_type = wine_data.get("wine_type", "Unknown")
        country = wine_data.get("country", "Unknown")
        region_name = wine_data.get("region_name", "")
        consumed_date = wine_data.get("consumed_date", "Unknown date")
        bottle_note = wine_data.get("bottle_note", "")
        tasting_notes = wine_data.get("tasting_notes", "")

        # Create star rating display (convert 0-100 to 5-star scale)
        stars = "⭐" * (rating // 20) if rating else ""

        with st.expander(f"#{idx} - {producer_name} {wine_name} ({vintage or "NV"}) - {rating}/100 {stars}"):
            col1, col2 = st.columns(2)

            with col1:
                st.write(f"**Producer:** {producer_name}")
                st.write(f"**Wine:** {wine_name}")
                st.write(f"**Vintage:** {vintage or "Non-Vintage"}")
                st.write(f"**Type:** {wine_type}")

            with col2:
                st.write(f"**Rating:** {rating}/100 {stars}")
                st.write(f"**Country:** {country}")
                if region_name:
                    st.write(f"**Region:** {region_name}")
                st.write(f"**Consumed:** {consumed_date}")

            # Show tasting notes from wine or bottle
            if tasting_notes:
                st.markdown(f"**Tasting Notes:** {tasting_notes}")
            elif bottle_note:
                st.markdown(f"**Bottle Notes:** {bottle_note}")


def show_cellar_inventory():
    """Display all wines currently in the cellar."""
    bottle_repo = BottleRepository()

    # Get all inventory for filter options
    raw_inventory = bottle_repo.get_inventory()

    # Group bottles by wine_id and aggregate quantities
    wine_groups = {}
    for bottle in raw_inventory:
        wine_id = bottle.get('wine_id')
        if wine_id not in wine_groups:
            # First occurrence - store all wine data
            wine_groups[wine_id] = bottle.copy()
        else:
            # Add quantity to existing group
            wine_groups[wine_id]['quantity'] = wine_groups[wine_id].get('quantity', 0) + bottle.get('quantity', 0)

    # Convert back to list
    all_inventory = list(wine_groups.values())

    # Extract unique values for filters
    wine_types = sorted(set(w.get('wine_type') for w in all_inventory if w.get('wine_type')))
    countries = sorted(set(w.get('country') for w in all_inventory if w.get('country')))
    locations = sorted(set(w.get('location') for w in all_inventory if w.get('location')))
    producers = sorted(set(w.get('producer_name') for w in all_inventory if w.get('producer_name')))

    # Get vintage range
    vintages = [w.get('vintage') for w in all_inventory if w.get('vintage')]
    min_vintage = min(vintages) if vintages else 2000
    max_vintage = max(vintages) if vintages else 2024

    # Create filter UI with bordered container
    with st.container(border=True):
        st.markdown("### 🔍 Filter Your Collection")
        st.markdown("")

        filter_col1, filter_col2, filter_col3, filter_col4 = st.columns(4)

        with filter_col1:
            wine_types_with_all = ["All Types"] + wine_types
            selected_type = st.selectbox("Wine Type", wine_types_with_all)

        with filter_col2:
            countries_with_all = ["All Countries"] + countries
            selected_country = st.selectbox("Country", countries_with_all)

        with filter_col3:
            locations_with_all = ["All Locations"] + locations
            selected_location = st.selectbox("Location", locations_with_all)

        with filter_col4:
            producers_with_all = ["All Producers"] + producers
            selected_producer = st.selectbox("Producer", producers_with_all)

        # Additional filters row
        filter_col5, filter_col6, filter_col7, filter_col8 = st.columns(4)

        with filter_col5:
            vintage_range = st.slider(
                "Vintage Range",
                min_value=int(min_vintage),
                max_value=int(max_vintage),
                value=(int(min_vintage), int(max_vintage))
            )

        with filter_col6:
            rating_filter = st.selectbox("Rating", ["All Ratings", "Rated Only", "Unrated", "90+", "80+", "70+"])

        with filter_col7:
            search_term = st.text_input("Search", placeholder="Wine name, varietal...")

        with filter_col8:
            sort_by = st.selectbox("Sort By", ["Producer", "Wine Name", "Vintage (New→Old)", "Vintage (Old→New)", "Rating (High→Low)", "Rating (Low→High)"])

    # Apply filters
    filtered_inventory = all_inventory

    # Filter by wine type
    if selected_type != "All Types":
        filtered_inventory = [w for w in filtered_inventory if w.get('wine_type') == selected_type]

    # Filter by country
    if selected_country != "All Countries":
        filtered_inventory = [w for w in filtered_inventory if w.get('country') == selected_country]

    # Filter by location
    if selected_location != "All Locations":
        filtered_inventory = [w for w in filtered_inventory if w.get('location') == selected_location]

    # Filter by producer
    if selected_producer != "All Producers":
        filtered_inventory = [w for w in filtered_inventory if w.get('producer_name') == selected_producer]

    # Filter by vintage range
    filtered_inventory = [
        w for w in filtered_inventory
        if w.get('vintage') is None or (vintage_range[0] <= w.get('vintage') <= vintage_range[1])
    ]

    # Filter by rating
    if rating_filter == "Rated Only":
        filtered_inventory = [w for w in filtered_inventory if w.get('personal_rating') is not None]
    elif rating_filter == "Unrated":
        filtered_inventory = [w for w in filtered_inventory if w.get('personal_rating') is None]
    elif rating_filter == "90+":
        filtered_inventory = [w for w in filtered_inventory if w.get('personal_rating', 0) >= 90]
    elif rating_filter == "80+":
        filtered_inventory = [w for w in filtered_inventory if w.get('personal_rating', 0) >= 80]
    elif rating_filter == "70+":
        filtered_inventory = [w for w in filtered_inventory if w.get('personal_rating', 0) >= 70]

    # Filter by search term
    if search_term:
        search_lower = search_term.lower()
        filtered_inventory = [
            w for w in filtered_inventory
            if search_lower in w.get('wine_name', '').lower()
            or search_lower in w.get('producer_name', '').lower()
        ]

    # Sort
    if sort_by == "Producer":
        filtered_inventory.sort(key=lambda w: (w.get('producer_name', ''), w.get('vintage') or 0), reverse=True)
    elif sort_by == "Wine Name":
        filtered_inventory.sort(key=lambda w: w.get('wine_name', ''))
    elif sort_by == "Vintage (New→Old)":
        filtered_inventory.sort(key=lambda w: w.get('vintage') or 0, reverse=True)
    elif sort_by == "Vintage (Old→New)":
        filtered_inventory.sort(key=lambda w: w.get('vintage') or 9999)
    elif sort_by == "Rating (High→Low)":
        filtered_inventory.sort(key=lambda w: w.get('personal_rating') or 0, reverse=True)
    elif sort_by == "Rating (Low→High)":
        filtered_inventory.sort(key=lambda w: w.get('personal_rating') or 9999)

    if not filtered_inventory:
        st.warning("🍷 No wines found matching the selected filters.")
        return

    # Results header
    total_bottles = sum(w.get('quantity', 0) for w in filtered_inventory)
    st.markdown(f"### 🍾 Your Collection ({len(filtered_inventory)} wines, {total_bottles} bottles)")
    st.markdown("")

    # Display wines in expandable sections
    for wine_data in filtered_inventory:
        wine_name = wine_data.get('wine_name', 'Unknown')
        producer_name = wine_data.get('producer_name', 'Unknown Producer')
        vintage = wine_data.get('vintage')
        wine_type = wine_data.get('wine_type', 'Unknown')
        country = wine_data.get('country', 'Unknown')
        region_name = wine_data.get('region_name', '')
        quantity = wine_data.get('quantity', 0)
        location = wine_data.get('location', 'Unknown')
        bin_location = wine_data.get('bin', '')
        purchase_date = wine_data.get('purchase_date', '')
        purchase_price = wine_data.get('purchase_price')
        currency = wine_data.get('currency', 'RON')
        rating = wine_data.get('personal_rating')
        bottle_note = wine_data.get('bottle_note', '')

        # Create title with rating if available
        title_parts = [f"{producer_name} {wine_name} ({vintage or 'NV'})",
                       f"- {quantity} bottle{'s' if quantity > 1 else ''}"]
        if rating:
            # TODO: convert following scale
            stars = '⭐' * (rating // 20) if rating else ''
            title_parts.append(f" {stars}")


        with st.expander(" ".join(title_parts)):
            col1, col2, col3 = st.columns(3)

            with col1:
                st.write("**Wine Details**")
                st.write(f"Producer: {producer_name}")
                st.write(f"Wine: {wine_name}")
                st.write(f"Vintage: {vintage or 'Non-Vintage'}")
                st.write(f"Type: {wine_type}")
                st.write(f"Country: {country}")
                if region_name:
                    st.write(f"Region: {region_name}")

            with col2:
                st.write("**Cellar Info**")
                st.write(f"Quantity: {quantity} bottle{'s' if quantity > 1 else ''}")
                st.write(f"Location: {location}")
                if bin_location:
                    st.write(f"Bin: {bin_location}")
                if purchase_date:
                    st.write(f"Purchased: {purchase_date}")
                if purchase_price:
                    st.write(f"Price: {purchase_price} {currency}")

            with col3:
                st.write("**Rating & Notes**")
                if rating:
                    stars = '⭐' * (rating // 20) if rating else ''
                    st.write(f"Rating: {rating}/100 {stars}")
                else:
                    st.write("Rating: Not rated")

                if bottle_note:
                    st.write(f"Notes: {bottle_note}")