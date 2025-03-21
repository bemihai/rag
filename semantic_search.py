from sentence_transformers import SentenceTransformer
import faiss
import pandas as pd
import numpy as np


if __name__ == "__main__":

    # read text
    with open("data/interstellar.txt") as f:
        text = f.read()

    # split text into sentences
    chunks = text.split(".")
    chunks = [c.strip(" \n") for c in chunks]

    # use SentenceTransformer to embedd chunks
    model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    embeddings = model.encode(chunks)

    # build the search index
    dim = embeddings.shape[1]
    index = faiss.IndexFlatL2(dim)
    index.add(embeddings)

    # embedd the query
    query = "How precise was the science"
    query_embedding = model.encode([query])

    # get the nearest neighbors
    distances, indices = index.search(query_embedding, 3)
    results = pd.DataFrame({
        "texts": np.array(chunks)[indices[0]],
        "distance": distances[0],
    })

    print(results)





