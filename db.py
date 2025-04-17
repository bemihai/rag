from datetime import datetime
from pathlib import Path

import chromadb
from chromadb.utils import embedding_functions as ef

from chunks import split_pdfs
from env import CHROMA_HOST, CHROMA_PORT, DATA_PATH
from utils import hash8


# create the chroma client
client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)

# define the embedding function (default is all-MiniLM-L6-v2 from sentence transformers)
default_ef = ef.DefaultEmbeddingFunction()

# create a new collection of embeddings
# chroma uses Hierarchical Navigable Small Worlds for indexing
collection = client.get_or_create_collection(
    name="rag_tutorial",
    embedding_function=default_ef,
    metadata={
        "description": "Rag tutorial embeddings collections",
        "created": str(datetime.now()),
        "hnsw:space": "cosine",  # similarity measure
        "hnsw:search_ef": 100,  # num candidates for searching
        "hnsw:construction_ef": 100,  # num candidates for indexing
        "hnsw:num_threads": 8,  # num of threads for indexing
    }
)

files = Path(DATA_PATH).glob("**/*.pdf")
documents = split_pdfs(list(files), chunk_size=512, overlap_size=128)

docs = [d[0] for d in documents]
metadata = [{"pdf_file": d[1]} for d in documents]
ids = [str(hash8(doc)) for doc in docs]

collection.add(
    documents=docs,
    metadatas=metadata,
    ids=ids,
)





