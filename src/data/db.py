from datetime import datetime
from pathlib import Path

import chromadb
from langchain_huggingface import HuggingFaceEmbeddings

from chunks import split_file
from src.utils.env import CHROMA_HOST, CHROMA_PORT, DATA_PATH
from src.utils import create_chroma_batches


# create the chroma client
client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)

# define the embedding function (default is all-MiniLM-L6-v2 from sentence transformers)
embedder = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)

# create a new collection of embeddings
# chroma uses Hierarchical Navigable Small Worlds for indexing
collection = client.get_or_create_collection(
    name="wine_books",
    metadata={
        "description": "Wine books collection",
        "created": str(datetime.now()),
        "hnsw:space": "cosine",  # similarity measure
        "hnsw:search_ef": 100,  # num candidates for searching
        "hnsw:construction_ef": 100,  # num candidates for indexing
        "hnsw:num_threads": 8,  # num of threads for indexing
    }
)

epub_files = Path(DATA_PATH).glob("**/*.epub")
pdf_files = Path(DATA_PATH).glob("**/*.pdf")
files = list(epub_files) + list(pdf_files)

for file in files:
    print(f"Processing file: {file.name}")
    documents = split_file(file, chunk_size=512, overlap_size=128)

    docs = [d.text for d in documents]
    embeddings = embedder.embed_documents(docs)
    metadata = [
        {
            "filename": d.metadata.filename,
            "language": d.metadata.languages[0] if d.metadata.languages else "unknown",
        } for d in documents]
    ids = [d.id for d in documents]

    if docs:
        # Create batches to avoid FastAPI errors with large collections
        batches = create_chroma_batches(
            batch_size=2500,
            documents=docs,
            embeddings=embeddings,
            metadata=metadata,
            ids=ids,
        )

        for batch in batches:
            collection.add(
                ids=batch[0],
                embeddings=batch[1],
                metadatas=batch[2],
                documents=batch[3],
            )

        print(f"Added {len(docs)} chunks from {file.name} to the collection.")





