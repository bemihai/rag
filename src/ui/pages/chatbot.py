"""Chatbot page"""
import streamlit as st

from src.ui.helper.display import CONTENT_STYLE, display_message, make_page_title
from src.ui.resources import load_llm, load_chroma_client, load_retriever
from src.ui.sidebar import render_sidebar
from src.agents.llm import process_user_prompt
from src.utils import get_config, get_initial_message, build_semantic_context, format_sources_for_display, \
    build_context_from_chunks, logger


def main():
    """Chatbot page - main entry point."""
    # Load cached resources
    model = load_llm()
    chroma_client = load_chroma_client()
    retriever = load_retriever()

    # Page title and description
    st.set_page_config(page_title="Pour Decisions", page_icon="🍷")
    st.markdown(make_page_title(
        "Pour Decisions",
        "Let the bot choose your bottle 🍷"
    ), unsafe_allow_html=True)

    # Render sidebar
    render_sidebar(retriever=retriever, chroma_client=chroma_client)

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


if __name__ == "__main__":
    main()