"""Wine Cellar page UI."""
import streamlit as st

from src.ui.helper import (show_cellar_metrics, make_page_title, show_cellar_inventory,
                           show_top_rated_consumed_wines, TABS_DISPLAY)


def main():
    """Wine Cellar page - main entry point."""
    st.set_page_config(page_title="Wine Cellar", page_icon="🍷", layout="wide")
    st.markdown(TABS_DISPLAY, unsafe_allow_html=True)

    st.markdown(make_page_title(
        "Cellar",
        "Your personal wine collection 🍾"
    ), unsafe_allow_html=True)
    st.markdown("")

    # Cellar Metrics in a container with border
    with st.container(border=True):
        show_cellar_metrics()

    # Tabs with content in containers
    tab_1, tab_2 = st.tabs(["📦 Cellar Inventory", "🌟 Top Rated Consumed"])

    with tab_1:
        with st.container():
            show_cellar_inventory()

    with tab_2:
        with st.container():
            show_top_rated_consumed_wines()


if __name__ == "__main__":
    main()


