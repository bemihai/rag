import pandas as pd
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.core import Settings, VectorStoreIndex, Document, PromptTemplate
from llama_index.llms.llama_cpp import LlamaCPP


if __name__ == "__main__":

    # read text
    with open("data/interstellar.txt", "r", encoding="utf-8") as f:
        text = f.read()

    # split text into sentences
    chunks = text.split(".")
    chunks = [c.strip(" \n") for c in chunks]
    docs = [Document(text=t) for t in chunks]

    # load a local llm using llama cpp
    llm=LlamaCPP(
        model_path="/Users/lu80mf/models/Phi-3-mini-4k-instruct-fp16.gguf",
        max_new_tokens=500,
        context_window=2048,
        model_kwargs={"n_gpu_layers": -1},
        verbose=False,
    )
    Settings.llm = llm

    # load embedding model
    embed_model = HuggingFaceEmbedding(model_name="thenlper/gte-small")

    # create an index from chunks
    Settings.embed_model = embed_model
    index = VectorStoreIndex.from_documents(docs, show_progress=True)

    # create the retriever
    retriever = index.as_retriever(similarity_top_k=3)

    # build the query engine for this index
    query_engine = RetrieverQueryEngine.from_args(retriever=retriever, llm=llm, response_mode="tree_summarize")

    # query the engine
    result = query_engine.query("How precise was the science")
    print(str(result))

    # print sorted context chunks
    df = pd.DataFrame({
        "texts": [node.get_content() for node in result.source_nodes],
        "scores": [node.get_score() for node in result.source_nodes]
    })
    print("-------------------------------------------------------------")
    print(df)

    # display engine's prompt templates
    print("-------------------------------------------------------------")
    for k, p in query_engine.get_prompts().items():
        print(f"Prompt key: {k} \nPrompt template:")
        print(p.get_template())

    # update the prompt template
    new_tmpl_str = (
        "Context information is below.\n"
        "---------------------\n"
        "{context_str}\n"
        "---------------------\n"
        "Provide a concise answer the following question using the "
        "relevant information provided above:\n"
        "Question: {query_str}\n"
        "Answer: "
    )
    query_engine.update_prompts(
        {"response_synthesizer:summary_template": PromptTemplate(new_tmpl_str)}
    )

    # query the engine
    result = query_engine.query("How precise was the science")
    print(str(result))