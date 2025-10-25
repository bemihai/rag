"""Main agent page."""
import streamlit as st

from display import display_message, make_app_title, CONTENT_STYLE
from src.model.llm import load_base_model, process_user_prompt
from src.data import ChromaRetriever
from src.utils import get_config, get_initial_message, build_semantic_context, format_sources_for_display, \
    build_context_from_chunks, logger
from src.utils.chroma import initialize_chroma_client


# App title and description
st.set_page_config(page_title="Pour Decisions", page_icon="🍷")
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

    try:
        client = initialize_chroma_client(
            host=chroma_cfg.client.host,
            port=chroma_cfg.client.port
        )
        return client
    except Exception as e:
        logger.error(f"Failed to initialize ChromaDB client: {e}")
        st.error(
            f"⚠️ Unable to connect to ChromaDB at {chroma_cfg.client.host}:{chroma_cfg.client.port}. "
            "RAG features will be disabled. Using LLM general knowledge only."
        )
        return None


# Initialize retriever
@st.cache_resource
def load_retriever():
    """Initialize ChromaRetriever with caching."""
    try:
        cfg = get_config()
        chroma_cfg = cfg.chroma
        client = load_chroma_client()

        if client is None:
            logger.warning("ChromaDB client is unavailable. Retriever not initialized.")
            return None

        collection_name = chroma_cfg.collections[0].name

        return ChromaRetriever(
            client=client,
            collection_name=collection_name,
            embedding_model=chroma_cfg.settings.embedder,
            n_results=chroma_cfg.retrieval.n_results,
            similarity_threshold=chroma_cfg.retrieval.similarity_threshold,
        )
    except Exception as e:
        logger.error(f"Failed to initialize retriever: {e}")
        st.warning(
            "⚠️ Could not initialize the retrieval system. "
            "RAG features are unavailable. Answers will be based on general knowledge only."
        )
        return None


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
    - What does 'terroir' mean in winemaking?
    """)

    st.markdown("---")

    # RAG Settings Section
    st.subheader("⚙️ RAG Settings")

    # Show system status
    if retriever is not None and chroma_client is not None:
        st.success("✅ RAG System: Connected")
    else:
        st.error("❌ RAG System: Unavailable")
        st.caption("Using LLM general knowledge only")

    # Initialize session state for RAG toggle if not exists
    if "enable_rag" not in st.session_state:
        st.session_state.enable_rag = True

    # Toggle to enable/disable RAG retrieval (disabled if retriever unavailable)
    enable_rag = st.toggle(
        "Enable RAG Retrieval",
        value=st.session_state.enable_rag if retriever is not None else False,
        help="When enabled, answers are based on your wine book collection. When disabled, uses only the LLM's general knowledge.",
        disabled=(retriever is None)
    )
    st.session_state.enable_rag = enable_rag

    if enable_rag and retriever is not None:
        # Show number of chunks to retrieve
        n_results = st.slider(
            "Number of sources to retrieve",
            min_value=1,
            max_value=10,
            value=cfg.chroma.retrieval.n_results,
            help="How many document chunks to retrieve from the knowledge base"
        )
        st.session_state.n_results = n_results

    if st.button("🔄 Reset Chat"):
        st.session_state.messages = get_initial_message()
        if "last_sources" in st.session_state:
            del st.session_state.last_sources
        if "last_retrieved_docs" in st.session_state:
            del st.session_state.last_retrieved_docs
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
        context = ""
        retrieval_error = False

        try:
            cfg = get_config()

            # Check if RAG is enabled and retriever is available
            if st.session_state.get("enable_rag", True) and retriever is not None:
                try:
                    # Get user-selected number of results or use default
                    n_results = st.session_state.get("n_results", cfg.chroma.retrieval.n_results)

                    # Retrieve relevant documents from ChromaDB
                    retrieved_docs = retriever.retrieve(prompt, n_results=n_results)

                    # Build context from retrieved chunks with optional deduplication
                    if cfg.chroma.retrieval.use_deduplication:
                        context = build_semantic_context(
                            retrieved_docs,
                            similarity_threshold=cfg.chroma.retrieval.deduplication_threshold,
                            include_metadata=True,
                            embedding_model=cfg.chroma.settings.embedder
                        )
                    else:
                        context = build_context_from_chunks(
                            retrieved_docs,
                            include_metadata=True,
                            include_similarity=False,
                            max_chunks=None
                        )

                    # Store retrieved docs in session state for sidebar display
                    if retrieved_docs:
                        st.session_state.last_sources = format_sources_for_display(retrieved_docs)
                        st.session_state.last_retrieved_docs = retrieved_docs
                    else:
                        st.session_state.last_sources = []
                        st.session_state.last_retrieved_docs = []

                except Exception as e:
                    # Handle retrieval errors gracefully
                    logger.error(f"Error during document retrieval: {e}")
                    retrieval_error = True
                    context = ""
                    st.session_state.last_sources = []
                    st.session_state.last_retrieved_docs = []

                    # Show user-friendly error message
                    st.warning(
                        "⚠️ Unable to retrieve documents from the knowledge base. "
                        "Answering based on general knowledge instead."
                    )
            else:
                # RAG is disabled or retriever unavailable - use empty context
                context = ""
                st.session_state.last_sources = []
                st.session_state.last_retrieved_docs = []

            # Generate answer with available context
            try:
                answer = process_user_prompt(model, prompt, context, message_history)
            except Exception as e:
                logger.error(f"Error generating answer: {e}")
                answer = "I apologize, but I encountered an error while generating a response. Please try again."
                st.error("❌ Failed to generate response. Please try asking your question again.")

        except TimeoutError:
            answer = "I apologize, but the request timed out. Please try again."
            st.error("⏱️ Request timed out. Please try again.")
        except Exception as e:
            logger.error(f"Unexpected error in processing: {e}")
            answer = "I apologize, but an unexpected error occurred. Please try again."
            st.error(f"❌ An unexpected error occurred: {str(e)}")

        sys_message = {"role": "ai", "answer": answer, "sources": st.session_state.last_sources}
    display_message(sys_message)
    st.session_state.messages.append(sys_message)
