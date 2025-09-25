import streamlit as st
from langfuse import Langfuse
from langfuse.langchain import CallbackHandler


def get_langfuse_callback():
    """Returns a Langfuse callback handler."""
    public_key = st.secrets["LANGFUSE_PUBLIC_KEY"] if "LANGFUSE_PUBLIC_KEY" in st.secrets else None
    secret_key = st.secrets["LANGFUSE_SECRET_KEY"] if "LANGFUSE_SECRET_KEY" in st.secrets else None

    if public_key and secret_key:
        langfuse = Langfuse(
            public_key=public_key,
            secret_key=secret_key,
            host="https://cloud.langfuse.com"
        )

        langfuse_handler = CallbackHandler()
    else:
        langfuse_handler = None
        logger.error("Langfuse keys not found in Streamlit secrets. Langfuse logging is disabled.")

    return langfuse_handler
