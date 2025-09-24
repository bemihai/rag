import chromadb
from langchain_chroma import Chroma
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.prompts import PromptTemplate
from langchain.chains import RetrievalQA

from src.model.llm import load_google_ai_model
from src.utils import get_config

if __name__ == "__main__":

    config = get_config()

    # load the embedding model
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )

    # load the LLM for generation
    llm = load_google_ai_model(config.model.name)

    # create a local vector store from ChromaDB
    chroma_client = chromadb.HttpClient(host=config.chroma.host, port=config.chroma.port)
    vector_store = Chroma(
        client=chroma_client,
        collection_name="wine_books",
        embedding_function=embeddings,
    )

    # build the prompt template
    template = """<|user|>
    Relevant information:
    {context}
    You are assisting users with information about wines. 
    Answer the following question using the relevant information provided above:
    {question}
    If the information provided above is not sufficient to answer the question, 
    answer it based on your general knowledge.
    <|end|>
    <|assistant|>"""
    prompt = PromptTemplate(
        template=template,
        input_variables=["context", "question"]
    )

    # build the RAG pipeline
    rag = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=vector_store.as_retriever(search_type="mmr", search_kwargs={"k": 7, "fetch_k": 10}),
        chain_type_kwargs={"prompt": prompt},
        verbose=True,
    )

    answer = rag.invoke("What are the best wine producers in Pauillac?")
    print(answer["result"])


