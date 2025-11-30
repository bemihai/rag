"""Taste Profile page"""
import streamlit as st

from src.ui.helper.display import make_compact_page_title, TABS_DISPLAY
from src.ui.helper import show_top_rated_consumed_wines, show_latest_consumed_wines
from src.ui.helper.taste_profile_stats import (
    show_taste_profile_overview,
    show_rating_distribution,
    show_wine_type_distribution,
    show_wine_type_performance,
    show_top_varietals,
    show_varietal_analysis,
    show_producer_loyalty,
    show_favorite_regions,
    show_rating_trends
)


def main():
    """Taste Profile page - main entry point."""
    st.set_page_config(page_title="Taste Profile", page_icon="👅", layout="wide")
    st.markdown(TABS_DISPLAY, unsafe_allow_html=True)

    st.markdown(make_compact_page_title(
        "Taste Profile",
        "Discover your wine preferences 🍇"
    ), unsafe_allow_html=True)
    st.markdown("")

    # Key Insights at the top
    with st.container(border=True):
        st.markdown("### <i class='fa-solid fa-lightbulb fa-icon'></i>Key Insights", unsafe_allow_html=True)
        st.markdown("")
        show_taste_profile_overview()

    st.markdown("")

    # Tabs for different views
    tab1, tab2 = st.tabs(["📊 Analytics & Trends", "📝 Tasting History"])

    with tab1:
        # Rating Distribution and Rating Trends (side by side)
        col1, col2 = st.columns(2)

        with col1:
            with st.container(border=True):
                st.markdown("### <i class='fa-solid fa-chart-pie fa-icon'></i>Rating Distribution", unsafe_allow_html=True)
                st.markdown("")
                show_rating_distribution()

        with col2:
            with st.container(border=True):
                st.markdown("### <i class='fa-solid fa-chart-line fa-icon'></i>Rating Trends Over Time", unsafe_allow_html=True)
                st.markdown("")
                show_rating_trends()

        st.markdown("")

        # Wine Type Distribution and Performance (side by side)
        col1, col2 = st.columns(2)

        with col1:
            with st.container(border=True):
                show_wine_type_distribution()

        with col2:
            with st.container(border=True):
                show_wine_type_performance()

        st.markdown("")

        # Top Varietals and Varietal Analysis (side by side)
        col1, col2 = st.columns(2)

        with col1:
            with st.container(border=True):
                show_top_varietals()

        with col2:
            with st.container(border=True):
                show_varietal_analysis()

    with tab2:
        # Consumed wines section
        with st.container(border=True):
            col1, col2 = st.columns(2)

            with col1:
                show_latest_consumed_wines(limit=5)

            with col2:
                show_top_rated_consumed_wines()

        st.markdown("")

        # Favorite Producers and Regions
        col1, col2 = st.columns(2)

        with col1:
            with st.container(border=True):
                show_producer_loyalty()

        with col2:
            with st.container(border=True):
                show_favorite_regions()


if __name__ == "__main__":
    main()


