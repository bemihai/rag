"""Taste Profile page"""
import streamlit as st

from src.ui.helper.display import make_compact_page_title, TABS_DISPLAY
from src.ui.helper import show_top_rated_consumed_wines, show_latest_consumed_wines
from src.ui.helper.taste_profile_stats import (
    show_taste_profile_overview,
    show_rating_distribution,
    show_wine_type_preferences,
    show_varietal_preferences,
    show_producer_loyalty,
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

    # Top section split into two columns
    with st.container(border=True):
        col1, col2 = st.columns(2)

        with col1:
            show_latest_consumed_wines(limit=5)

        with col2:
            show_top_rated_consumed_wines()

    st.markdown("")

    # Taste Profile Overview - Key Metrics
    with st.container(border=True):
        st.markdown("### <i class='fa-solid fa-chart-pie fa-icon'></i>Your Taste Profile Overview", unsafe_allow_html=True)
        st.markdown("")
        show_taste_profile_overview()
        st.markdown("")
        show_rating_distribution()

    st.markdown("")

    # Wine Type Preferences
    with st.container(border=True):
        show_wine_type_preferences()

    st.markdown("")

    # Rating Trends Over Time
    with st.container(border=True):
        show_rating_trends()

    st.markdown("")

    # Varietal and Producer Preferences (side by side)
    col1, col2 = st.columns(2)

    with col1:
        with st.container(border=True):
            show_varietal_preferences()

    with col2:
        with st.container(border=True):
            show_producer_loyalty()


if __name__ == "__main__":
    main()


