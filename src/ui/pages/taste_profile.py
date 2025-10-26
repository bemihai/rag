"""Taste Profile page"""
import streamlit as st

from src.ui.display import make_page_title


def main():
    """Taste Profile page - main entry point."""
    st.set_page_config(page_title="Taste Profile", page_icon="👅")

    st.markdown(make_page_title(
        "Taste Profile",
        "Discover your wine preferences 🍇"
    ), unsafe_allow_html=True)

    # Placeholder content
    st.info("👷 This section is under construction")

    st.markdown("""
    ### Coming Soon

    This section will help you:
    - 🎯 Define your wine taste preferences
    - 📊 Track your tasting history
    - 🔍 Discover wines that match your profile
    - 📈 See how your preferences evolve over time
    - 🎨 Visualize your flavor preference map
    - 💡 Get personalized wine recommendations

    ### Wine Taste Dimensions

    Your profile will include preferences for:
    - **Body**: Light, Medium, Full
    - **Sweetness**: Dry, Off-Dry, Sweet
    - **Acidity**: Low, Medium, High
    - **Tannins**: Soft, Medium, Bold
    - **Fruit Profile**: Red fruits, Dark fruits, Citrus, Tropical
    - **Oak Influence**: None, Light, Medium, Heavy
    """)

    # Placeholder interactive element
    st.markdown("---")
    st.subheader("Quick Preference Survey (Preview)")

    col1, col2 = st.columns(2)

    with col1:
        st.slider("Body Preference", 1, 5, 3, help="1 = Light, 5 = Full-bodied", disabled=True)
        st.slider("Sweetness Preference", 1, 5, 2, help="1 = Bone Dry, 5 = Sweet", disabled=True)
        st.slider("Acidity Preference", 1, 5, 3, help="1 = Low, 5 = High", disabled=True)

    with col2:
        st.slider("Tannin Preference", 1, 5, 3, help="1 = Soft, 5 = Bold", disabled=True)
        st.slider("Oak Influence", 1, 5, 2, help="1 = None, 5 = Heavy", disabled=True)
        st.slider("Alcohol Level", 1, 5, 3, help="1 = Low (<12%), 5 = High (>14%)", disabled=True)

    st.button("Save Profile", disabled=True, help="Feature coming soon!")

    st.markdown("---")
    st.caption("🔜 This feature is currently in development and will be available soon.")


if __name__ == "__main__":
    main()


