"""Helper functions for Taste Profile page statistics and visualizations."""
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from src.database.repository import StatsRepository
from src.etl.utils import denormalize_rating


def show_taste_profile_overview():
    """Display overview metrics for taste profile."""
    stats_repo = StatsRepository()

    # Get statistics
    rating_stats = stats_repo.get_rating_statistics()
    overall = rating_stats['overall']
    wine_type_stats = stats_repo.get_wine_type_stats()
    streak = stats_repo.get_tasting_streak_days()

    # Calculate metrics
    avg_rating = overall.get('avg_rating', 0)
    wines_rated = overall.get('wines_rated', 0)

    # Find favorite type (most consumed)
    favorite_type = "N/A"
    if wine_type_stats:
        favorite_type = wine_type_stats[0].get('wine_type', 'N/A')

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
            label="Tasting Streak",
            value=f"{streak} month{'s' if streak != 1 else ''}",
            delta=None
        )


def show_rating_distribution():
    """Display rating distribution chart."""
    stats_repo = StatsRepository()
    rating_stats = stats_repo.get_rating_statistics()
    distribution = rating_stats.get('distribution', [])

    if not distribution:
        st.info("No rating data available yet.")
        return

    st.markdown("#### Rating Distribution")

    # Prepare data for chart
    ranges = [d['rating_range'] for d in distribution]
    counts = [d['count'] for d in distribution]

    # Define colors for ranges
    colors = ['#F44336', '#FF9800', '#FFC107', '#8BC34A', '#4CAF50']
    color_map = {
        '0-49': colors[0],
        '50-69': colors[1],
        '70-79': colors[2],
        '80-89': colors[3],
        '90-100': colors[4]
    }
    bar_colors = [color_map.get(r, '#999') for r in ranges]

    # Create bar chart
    fig = go.Figure(data=[
        go.Bar(
            x=ranges,
            y=counts,
            marker_color=bar_colors,
            text=counts,
            textposition='auto',
        )
    ])

    fig.update_layout(
        xaxis_title="Rating Range",
        yaxis_title="Number of Wines",
        height=300,
        margin=dict(l=20, r=20, t=20, b=20),
        showlegend=False
    )

    st.plotly_chart(fig, use_container_width=True)


def show_wine_type_preferences():
    """Display wine type preferences with chart and table."""
    stats_repo = StatsRepository()
    wine_type_stats = stats_repo.get_wine_type_stats()

    if not wine_type_stats:
        st.info("No wine type data available yet.")
        return

    st.markdown("### <i class='fa-solid fa-wine-glass fa-icon'></i>Wine Type Preferences", unsafe_allow_html=True)

    # Create two columns: chart on left, table on right
    col1, col2 = st.columns([1, 1])

    with col1:
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
            height=350,
            margin=dict(l=20, r=20, t=30, b=20),
            showlegend=True,
            legend=dict(orientation="v", yanchor="middle", y=0.5)
        )

        st.plotly_chart(fig, use_container_width=True)

    with col2:
        # Performance table
        st.markdown("#### Performance by Type")

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


def show_varietal_preferences():
    """Display top varietal preferences."""
    stats_repo = StatsRepository()
    varietals = stats_repo.get_varietal_preferences(limit=10)

    if not varietals:
        st.info("No varietal data available yet.")
        return

    st.markdown("### <i class='fa-solid fa-seedling fa-icon'></i>Top Varietals", unsafe_allow_html=True)

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

    # Show all as bar chart
    if len(varietals) > 3:
        st.markdown("#### All Top Varietals")

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
    producers = stats_repo.get_producer_preferences(limit=10)

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


def show_rating_trends():
    """Display rating trends over time."""
    stats_repo = StatsRepository()
    timeline = stats_repo.get_rating_timeline()

    if not timeline or len(timeline) < 2:
        st.info("Not enough data to show rating trends. Keep tasting wines!")
        return

    st.markdown("### <i class='fa-solid fa-chart-line fa-icon'></i>Rating Trends Over Time", unsafe_allow_html=True)

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

