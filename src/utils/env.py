import os
from dotenv import load_dotenv


def load_env():
    """Load environment variables from .env file."""
    load_dotenv()


load_env()

GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

LANGFUSE_PUBLIC_KEY = os.environ.get("LANGFUSE_PUBLIC_KEY", "")
LANGFUSE_SECRET_KEY = os.environ.get("LANGFUSE_SECRET_KEY", "")

# CellarTracker credentials
CELLARTRACKER_USERNAME = os.environ.get("CELLARTRACKER_USERNAME", "")
CELLARTRACKER_PASSWORD = os.environ.get("CELLARTRACKER_PASSWORD", "")
