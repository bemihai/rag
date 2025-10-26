import os
from dotenv import load_dotenv


load_dotenv()

GOOGLE_API_KEY = os.environ["GOOGLE_API_KEY"]
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]

LANGFUSE_PUBLIC_KEY = os.environ["LANGFUSE_PUBLIC_KEY"]
LANGFUSE_SECRET_KEY = os.environ["LANGFUSE_SECRET_KEY"]

# Cellar Tracker credentials
CELLAR_TRACKER_USERNAME = os.environ.get("CELLAR_TRACKER_USERNAME", "")
CELLAR_TRACKER_PASSWORD = os.environ.get("CELLAR_TRACKER_PASSWORD", "")
