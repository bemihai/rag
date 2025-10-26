"""Main agent page."""
import streamlit as st

from resources import load_chroma_client, load_retriever
from src.utils import get_config


# Load cached resources
cfg = get_config()
chroma_client = load_chroma_client()
retriever = load_retriever()


def main():

    chatbot = st.Page("pages/chatbot.py", title="Chatbot", icon="💬", default=True)
    cellar = st.Page("pages/cellar.py", title="Cellar", icon="🍾")
    taste_profile = st.Page("pages/taste_profile.py", title="Taste Profile", icon="🎨")

    pg = st.navigation(
        {
            "": [chatbot, cellar, taste_profile]
        },
    )

    pg.run()


if __name__ == "__main__":
    main()