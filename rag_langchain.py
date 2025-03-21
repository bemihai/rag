from langchain_community.vectorstores import FAISS
from langchain_community.llms import LlamaCpp
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.prompts import PromptTemplate
from langchain.chains import RetrievalQA


if __name__ == "__main__":

    # read text
    with open("data/interstellar.txt") as f:
        text = f.read()

    # split text into sentences
    chunks = text.split(".")
    chunks = [c.strip(" \n") for c in chunks]

    # load embedding model
    embedding_model = HuggingFaceEmbeddings(model_name="thenlper/gte-small")

    # load a local llm with langchain
    # model can be downloaded from: https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf
    llm = LlamaCpp(
        model_path="/Users/lu80mf/models/Phi-3-mini-4k-instruct-fp16.gguf",
        n_gpu_layers=-1,
        max_tokens=500,
        n_ctx=2048,
        seed=42,
        verbose=False,
    )

    # create a local vector database
    vdb = FAISS.from_texts(chunks, embedding_model)

    # build the prompt template
    template = """<|user|>
    Relevant information:
    {context}
    Provide a concise answer the following question using the
    relevant information provided above:
    {question}<|end|>
    <|assistant|>"""
    prompt = PromptTemplate(
        template=template,
        input_variables=["context", "question"]
    )

    # build the RAG pipeline
    rag = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=vdb.as_retriever(),
        chain_type_kwargs={"prompt": prompt},
        verbose=True,
    )

    answer = rag.invoke("How precise was the science")
    print(answer)


