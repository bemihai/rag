import os
from dotenv import load_dotenv

load_dotenv()

DATA_PATH = os.getenv("DATA_PATH")

CHROMA_HOST=os.getenv("CHROMA_HOST")
CHROMA_PORT=os.getenv("CHROMA_PORT")

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
