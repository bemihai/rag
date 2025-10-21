"""Main agent page."""
import streamlit as st

from display import display_message, make_app_title, CONTENT_STYLE
from src.model.llm import load_base_model, process_user_prompt
from src.data import ChromaRetriever
from src.utils import get_config, get_initial_message, build_semantic_context, format_sources_for_display
from src.utils.chroma import initialize_chroma_client


# App title and description
st.set_page_config(page_title="Pour Decisions: Let the bot choose your bottle 🍷🤖", page_icon="🍷")
st.markdown(make_app_title(
    "Pour Decisions",
    "Let the bot choose your bottle 🍷"
), unsafe_allow_html=True)

# Load the LLM model
@st.cache_resource
def load_llm():
    """Load model wrapper to allow caching."""
    cfg = get_config()
    return load_base_model(cfg.model.provider, cfg.model.name)


# Initialize ChromaDB client
@st.cache_resource
def load_chroma_client():
    """Initialize ChromaDB client with caching to avoid reconnection."""
    cfg = get_config()
    chroma_cfg = cfg.chroma
    return initialize_chroma_client(
        host=chroma_cfg.client.host,
        port=chroma_cfg.client.port
    )


# Initialize retriever
@st.cache_resource
def load_retriever():
    """Initialize ChromaRetriever with caching."""
    cfg = get_config()
    chroma_cfg = cfg.chroma
    client = load_chroma_client()
    collection_name = chroma_cfg.collections[0].name

    return ChromaRetriever(
        client=client,
        collection_name=collection_name,
        embedding_model=chroma_cfg.settings.embedder,
        n_results=chroma_cfg.retrieval.n_results,
        similarity_threshold=chroma_cfg.retrieval.similarity_threshold,
    )

cfg = get_config()
model = load_llm()
chroma_client = load_chroma_client()
retriever = load_retriever()

# App sidebar
with st.sidebar:
    st.header("About Pour Decisions")
    st.write(
        """
        Pour Decisions uses Retrieval-Augmented Generation (RAG) and LLMs 
        to answer your wine-related questions using both curated knowledge and external data. 🍇
        
        **Try asking questions like:**
        """
    )
    st.markdown("""
    - What is the difference between Merlot and Cabernet Sauvignon?
    - Suggest a wine pairing for spicy Thai food.
    - What are the main wine regions in France?
    - How should I store an opened bottle of wine?
    - What does 'terroir' mean in winemaking?
    """)

    # Display sources from last query if available
    if "last_sources" in st.session_state and st.session_state.last_sources:
        st.markdown("---")
        st.subheader("📚 Sources Used")
        for source in st.session_state.last_sources:
            st.text(source)

    st.markdown("#")
    if st.button("Reset Chat"):
        st.session_state.messages = get_initial_message()
        st.rerun()

# App main page
# Initialize the chat messages history
if "messages" not in st.session_state.keys():
    st.session_state.messages = get_initial_message()

st.write(CONTENT_STYLE, unsafe_allow_html=True)

# Display past messages
if "messages" in st.session_state:
    for message in st.session_state.messages:
        display_message(message)

# Process user prompt
if prompt := st.chat_input("Type your question here"):
    user_message = {"role": "human", "question": prompt}
    display_message(user_message)
    st.session_state.messages.append(user_message)

    # Pass the full message history (including both human and ai turns)
    message_history = st.session_state.messages.copy()

    with st.spinner("Thinking...", show_time=True):
        try:
            # Retrieve relevant documents from ChromaDB and build context
            retrieved_docs = retriever.retrieve(prompt)
            context = build_semantic_context(
                retrieved_docs,
                similarity_threshold=0.9,
                include_metadata=True,
                embedding_model=cfg.chroma.settings.embedder
            )

            # Store retrieved docs in session state for potential display
            if retrieved_docs:
                st.session_state.last_sources = format_sources_for_display(retrieved_docs)
            else:
                st.session_state.last_sources = []

            answer = process_user_prompt(model, prompt, context, message_history)
        except TimeoutError as _:
            answer = ""
        sys_message = {"role": "ai", "answer": answer}
    display_message(sys_message)
    st.session_state.messages.append(sys_message)
