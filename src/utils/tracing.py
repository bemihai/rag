from langfuse import Langfuse
from langfuse.langchain import CallbackHandler

from src.utils import logger
from src.utils.env import LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY


def get_langfuse_callback():
    """Returns a Langfuse callback handler."""
    try:
        langfuse = Langfuse(
            public_key=LANGFUSE_PUBLIC_KEY,
            secret_key=LANGFUSE_SECRET_KEY,
            host="https://cloud.langfuse.com"
        )

        langfuse_handler = CallbackHandler()
    except Exception as err:
        langfuse_handler = None
        logger.error(f"Cannot instantiate the Langfuse handler. Langfuse logging is disabled: {err}")

    return langfuse_handler
