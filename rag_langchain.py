import chromadb
from langchain_chroma import Chroma
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.prompts import PromptTemplate
from langchain.chains import RetrievalQA

from env import CHROMA_HOST, CHROMA_PORT, GOOGLE_API_KEY


if __name__ == "__main__":

    # load the embedding model
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )

    # load the LLM for generation
    # llm = GeminiModel(model_name="gemini-2.0-flash", max_tokens=1024, google_api_key=GOOGLE_API_KEY)
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        max_retries=2,
        max_tokens=1024,
        google_api_key=GOOGLE_API_KEY,
    )

    # create a local vector store from ChromaDB
    chroma_client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
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


