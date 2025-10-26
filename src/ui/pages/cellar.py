import streamlit as st

from src.ui.display import make_page_title


def main():
    """Wine Cellar page - main entry point."""
    st.set_page_config(page_title="Wine Cellar", page_icon="🍷")
    st.markdown(make_page_title(
        "Cellar",
        "Your personal wine collection 🍾"
    ), unsafe_allow_html=True)

    # Placeholder content
    st.info("👷 This section is under construction")

    st.markdown("""
    ### Coming Soon

    This section will allow you to:
    - 📦 Track your wine inventory
    - 📊 View cellar statistics
    - 🏷️ Organize wines by region, type, and vintage
    - 📝 Add tasting notes
    - 💰 Monitor collection value
    """)


if __name__ == "__main__":
    main()


