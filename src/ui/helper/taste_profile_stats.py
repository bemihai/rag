"""Helper functions for Taste Profile page statistics and visualizations."""
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from src.database import get_db_connection
from src.database.repository import StatsRepository
from src.etl.utils import denormalize_rating


def show_taste_profile_overview():
    """Display overview metrics for taste profile."""
    stats_repo = StatsRepository()

    # Get statistics
    rating_stats = stats_repo.get_rating_statistics()
    overall = rating_stats['overall']
    distribution = rating_stats.get('distribution', [])
    wine_type_stats = stats_repo.get_wine_type_stats()

    # Calculate metrics
    avg_rating = overall.get('avg_rating', 0)
    wines_rated = overall.get('wines_rated', 0)

    # Find favorite type (most consumed)
    favorite_type = "N/A"
    if wine_type_stats:
        favorite_type = wine_type_stats[0].get('wine_type', 'N/A')

    # Calculate percentage of highly-rated wines (90+)
    highly_rated_count = 0
    for d in distribution:
        if d.get('rating_range') == '90-100':
            highly_rated_count = d.get('count', 0)
            break

    highly_rated_pct = (highly_rated_count / wines_rated * 100) if wines_rated > 0 else 0

    # Display metrics in columns
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="Average Rating",
            value=f"{avg_rating:.1f}/100" if avg_rating else "N/A",
            delta=None
        )

    with col2:
        st.metric(
            label="Wines Tasted",
            value=wines_rated,
            delta=None
        )

    with col3:
        st.metric(
            label="Favorite Type",
            value=favorite_type,
            delta=None
        )

    with col4:
        st.metric(
            label="Highly Rated",
            value=f"{highly_rated_pct:.0f}%",
            delta=None,
            help=f"{highly_rated_count} wines rated 90+ out of {wines_rated} total"
        )


def show_rating_distribution():
    """Display rating distribution as donut chart with 5-point intervals."""
    stats_repo = StatsRepository()

    # Get consumed wines with ratings
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT t.personal_rating
            FROM bottles b
            JOIN wines w ON b.wine_id = w.id
            LEFT JOIN tastings t ON w.id = t.wine_id
            WHERE b.status = 'consumed' AND t.personal_rating IS NOT NULL
        """)
        ratings = [row['personal_rating'] for row in cursor.fetchall()]

    if not ratings:
        st.info("No rating data available yet.")
        return

    # Create 5-point intervals: 0-49, 50-54, 55-59, ..., 95-100
    ranges = []
    counts = []

    # 0-49 (poor wines)
    poor_count = sum(1 for r in ratings if r < 50)
    if poor_count > 0:
        ranges.append('0-49')
        counts.append(poor_count)

    # 50-94 in 5-point intervals
    for i in range(50, 95, 5):
        count = sum(1 for r in ratings if i <= r < i + 5)
        if count > 0:
            ranges.append(f'{i}-{i+4}')
            counts.append(count)

    # 95-100 (exceptional wines)
    excellent_count = sum(1 for r in ratings if r >= 95)
    if excellent_count > 0:
        ranges.append('95-100')
        counts.append(excellent_count)

    # Create color gradient from red to green
    num_ranges = len(ranges)
    if num_ranges <= 3:
        colors = ['#F44336', '#FFC107', '#4CAF50'][:num_ranges]
    else:
        # Create gradient for more ranges
        colors = []
        for i in range(num_ranges):
            ratio = i / (num_ranges - 1) if num_ranges > 1 else 0
            if ratio < 0.33:
                # Red to yellow
                colors.append(f'rgb({244}, {int(67 + (193 - 67) * (ratio / 0.33))}, {int(54 + (7 - 54) * (ratio / 0.33))})')
            elif ratio < 0.67:
                # Yellow to light green
                colors.append(f'rgb({int(255 - (255 - 139) * ((ratio - 0.33) / 0.34))}, {int(193 + (195 - 193) * ((ratio - 0.33) / 0.34))}, {int(7 + (74 - 7) * ((ratio - 0.33) / 0.34))})')
            else:
                # Light green to dark green
                colors.append(f'rgb({int(139 - (139 - 76) * ((ratio - 0.67) / 0.33))}, {int(195 + (175 - 195) * ((ratio - 0.67) / 0.33))}, {int(74 + (80 - 74) * ((ratio - 0.67) / 0.33))})')

    # Create donut chart
    fig = go.Figure(data=[go.Pie(
        labels=ranges,
        values=counts,
        hole=0.4,
        marker=dict(colors=colors)
    )])

    fig.update_layout(
        height=400,
        margin=dict(l=20, r=20, t=30, b=20),
        showlegend=True,
        legend=dict(orientation="v", yanchor="middle", y=0.5)
    )

    st.plotly_chart(fig, use_container_width=True)


def show_wine_type_distribution():
    """Display wine type distribution as donut chart."""
    stats_repo = StatsRepository()
    wine_type_stats = stats_repo.get_wine_type_stats()

    if not wine_type_stats:
        st.info("No wine type data available yet.")
        return

    st.markdown("### <i class='fa-solid fa-wine-glass fa-icon'></i>Wine Type Distribution", unsafe_allow_html=True)

    # Donut chart
    types = [w['wine_type'] for w in wine_type_stats]
    counts = [w['wines_tasted'] for w in wine_type_stats]

    fig = go.Figure(data=[go.Pie(
        labels=types,
        values=counts,
        hole=0.4,
        marker=dict(colors=px.colors.qualitative.Set3)
    )])

    fig.update_layout(
        height=400,
        margin=dict(l=20, r=20, t=30, b=20),
        showlegend=True,
        legend=dict(orientation="v", yanchor="middle", y=0.5)
    )

    st.plotly_chart(fig, use_container_width=True)


def show_wine_type_performance():
    """Display wine type performance table."""
    stats_repo = StatsRepository()
    wine_type_stats = stats_repo.get_wine_type_stats()

    if not wine_type_stats:
        st.info("No wine type data available yet.")
        return

    st.markdown("### <i class='fa-solid fa-star fa-icon'></i>Performance by Type", unsafe_allow_html=True)

    for wine_type_data in wine_type_stats:
        wine_type = wine_type_data.get('wine_type', 'Unknown')
        wines_tasted = wine_type_data.get('wines_tasted', 0)
        avg_rating = wine_type_data.get('avg_rating')
        highest = wine_type_data.get('highest_rating')

        with st.expander(f"{wine_type} ({wines_tasted} wine{'s' if wines_tasted != 1 else ''})"):
            if avg_rating:
                st.write(f"**Average Rating:** {avg_rating:.1f}/100")
                st.write(f"**Highest Rating:** {highest:.0f}/100")
            else:
                st.write("**Average Rating:** Not rated")


def show_top_varietals():
    """Display top 3 varietal preferences as cards."""
    stats_repo = StatsRepository()
    varietals = stats_repo.get_varietal_preferences(limit=10)

    if not varietals:
        st.info("No varietal data available yet.")
        return

    st.markdown("### <i class='fa-solid fa-seedling fa-icon'></i>Top 3 Varietals", unsafe_allow_html=True)

    # Show top 3 as cards
    top_3 = varietals[:3]
    if top_3:
        cols = st.columns(3)
        for idx, (col, varietal_data) in enumerate(zip(cols, top_3), 1):
            with col:
                varietal = varietal_data.get('varietal', 'Unknown')
                count = varietal_data.get('wines_tasted', 0)
                avg_rating = varietal_data.get('avg_rating')

                st.markdown(f"**#{idx} {varietal}**")
                st.write(f"🍷 {count} wine{'s' if count != 1 else ''}")
                if avg_rating:
                    # Create star display
                    denorm = denormalize_rating(avg_rating)
                    stars = "⭐" * int(denorm) if denorm else ""
                    st.write(f"⭐ {avg_rating:.1f}/100")
                st.markdown("---")
    else:
        st.info("Not enough varietal data to display top 3.")


def show_varietal_analysis():
    """Display varietal analysis chart with all top varietals."""
    stats_repo = StatsRepository()
    varietals = stats_repo.get_varietal_preferences(limit=10)

    if not varietals:
        st.info("No varietal data available yet.")
        return

    st.markdown("### <i class='fa-solid fa-chart-line fa-icon'></i>Varietal Analysis", unsafe_allow_html=True)

    names = [v['varietal'] for v in varietals]
    counts = [v['wines_tasted'] for v in varietals]
    ratings = [v.get('avg_rating', 0) for v in varietals]

    fig = go.Figure()

    # Add bar for count
    fig.add_trace(go.Bar(
        name='Wines Tasted',
        x=names,
        y=counts,
        marker_color='rgba(123, 31, 162, 0.7)',
        yaxis='y',
        offsetgroup=1
    ))

    # Add line for average rating
    fig.add_trace(go.Scatter(
        name='Avg Rating',
        x=names,
        y=ratings,
        mode='lines+markers',
        marker=dict(color='#FFC107', size=8),
        line=dict(color='#FFC107', width=2),
        yaxis='y2'
    ))

    fig.update_layout(
        height=400,
        margin=dict(l=20, r=20, t=20, b=80),
        xaxis=dict(tickangle=-45),
        yaxis=dict(title="Wines Tasted", side='left'),
        yaxis2=dict(title="Average Rating", side='right', overlaying='y', range=[0, 100]),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode='x unified'
    )

    st.plotly_chart(fig, use_container_width=True)


def show_producer_loyalty():
    """Display favorite producers."""
    stats_repo = StatsRepository()
    producers = stats_repo.get_producer_preferences(limit=5)

    if not producers:
        st.info("No producer data available yet.")
        return

    st.markdown("### <i class='fa-solid fa-building fa-icon'></i>Favorite Producers", unsafe_allow_html=True)

    for idx, producer_data in enumerate(producers, 1):
        producer = producer_data.get('producer_name', 'Unknown')
        country = producer_data.get('country', 'Unknown')
        wines_tasted = producer_data.get('wines_tasted', 0)
        avg_rating = producer_data.get('avg_rating')
        highest = producer_data.get('highest_rating')

        with st.expander(f"#{idx} {producer} ({country}) - {wines_tasted} wine{'s' if wines_tasted != 1 else ''}"):
            col1, col2 = st.columns(2)

            with col1:
                st.write(f"**Producer:** {producer}")
                st.write(f"**Country:** {country}")
                st.write(f"**Wines Tasted:** {wines_tasted}")

            with col2:
                if avg_rating:
                    st.write(f"**Average Rating:** {avg_rating:.1f}/100")
                    st.write(f"**Highest Rating:** {highest:.0f}/100")

                    # Show stars for average
                    denorm = denormalize_rating(avg_rating)
                    if denorm:
                        stars_html = "⭐" * int(denorm)
                        st.markdown(f"{stars_html}")


def show_favorite_regions():
    """Display favorite regions."""
    stats_repo = StatsRepository()
    regions = stats_repo.get_region_preferences(limit=5)

    if not regions:
        st.info("No region data available yet.")
        return

    st.markdown("### <i class='fa-solid fa-map-location-dot fa-icon'></i>Favorite Regions", unsafe_allow_html=True)

    for idx, region_data in enumerate(regions, 1):
        region = region_data.get('region_name', 'Unknown')
        country = region_data.get('country', 'Unknown')
        wines_tasted = region_data.get('wines_tasted', 0)
        avg_rating = region_data.get('avg_rating')
        highest = region_data.get('highest_rating')

        with st.expander(f"#{idx} {region} ({country}) - {wines_tasted} wine{'s' if wines_tasted != 1 else ''}"):
            col1, col2 = st.columns(2)

            with col1:
                st.write(f"**Region:** {region}")
                st.write(f"**Country:** {country}")
                st.write(f"**Wines Tasted:** {wines_tasted}")

            with col2:
                if avg_rating:
                    st.write(f"**Average Rating:** {avg_rating:.1f}/100")
                    st.write(f"**Highest Rating:** {highest:.0f}/100")

                    # Show stars for average
                    denorm = denormalize_rating(avg_rating)
                    if denorm:
                        stars_html = "⭐" * int(denorm)
                        st.markdown(f"{stars_html}")


def show_rating_trends():
    """Display rating trends over time."""
    stats_repo = StatsRepository()
    timeline = stats_repo.get_rating_timeline()

    if not timeline or len(timeline) < 2:
        st.info("Not enough data to show rating trends. Keep tasting wines!")
        return


    # Prepare data
    months = [t['month'] for t in timeline]
    ratings = [t['avg_rating'] for t in timeline]
    counts = [t['wines_count'] for t in timeline]

    # Create figure with secondary y-axis
    fig = go.Figure()

    # Add rating line
    fig.add_trace(go.Scatter(
        name='Average Rating',
        x=months,
        y=ratings,
        mode='lines+markers',
        marker=dict(color='#7b1fa2', size=8),
        line=dict(color='#7b1fa2', width=3),
        yaxis='y'
    ))

    # Add count bars
    fig.add_trace(go.Bar(
        name='Wines Tasted',
        x=months,
        y=counts,
        marker_color='rgba(123, 31, 162, 0.3)',
        yaxis='y2'
    ))

    fig.update_layout(
        height=400,
        margin=dict(l=20, r=20, t=20, b=20),
        xaxis=dict(title="Month"),
        yaxis=dict(title="Average Rating", side='left', range=[0, 100]),
        yaxis2=dict(title="Wines Tasted", side='right', overlaying='y'),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode='x unified'
    )

    st.plotly_chart(fig, use_container_width=True)

    # Show trend insight
    if len(ratings) >= 2:
        trend = "improving" if ratings[-1] > ratings[0] else "declining" if ratings[-1] < ratings[0] else "stable"
        trend_color = "🟢" if trend == "improving" else "🔴" if trend == "declining" else "🟡"
        st.caption(f"{trend_color} Your ratings are {trend} over time (from {ratings[0]:.1f} to {ratings[-1]:.1f})")

