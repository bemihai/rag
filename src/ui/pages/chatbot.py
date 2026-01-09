"""Chatbot page"""
import streamlit as st

from src.ui.helper.display import CONTENT_STYLE, display_message, make_page_title
from src.ui.resources import load_llm, load_chroma_client, load_retriever, load_intelligent_agent, load_keyword_agent, load_reranker
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
    reranker = load_reranker()

    # Load agents (cached)
    intelligent_agent = load_intelligent_agent()
    keyword_agent = load_keyword_agent()

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

        # Get selected agent mode
        agent_mode = st.session_state.get("agent_mode", "No Agent (RAG Only)")

        with st.spinner("Thinking...", show_time=True):
            try:
                # Use agents if selected
                if agent_mode == "Intelligent Agent" and intelligent_agent:
                    try:
                        import time
                        start_time = time.time()

                        result = intelligent_agent.invoke(prompt)
                        answer = result.get("final_answer", "")

                        processing_time = time.time() - start_time

                        # Store debug information
                        st.session_state.last_query_info = {
                            "query": prompt,
                            "tools_used": result.get("tools_used", []),
                            "response_length": len(answer),
                            "processing_time": processing_time
                        }

                        # Store tool results for display
                        st.session_state.last_sources = []
                        st.session_state.last_retrieved_docs = []

                    except Exception as e:
                        error_type = type(e).__name__
                        error_msg = str(e)
                        logger.error(f"Error using intelligent agent ({error_type}): {error_msg}", exc_info=True)

                        # Provide more specific error message based on error type
                        if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg or "quota" in error_msg.lower():
                            answer = "The AI service quota has been exceeded. The free tier allows 20 requests per day. Please try again later or switch to 'No Agent (RAG Only)' mode."
                        elif "ChatGoogleGenerativeAI" in error_type or "APIError" in error_type:
                            answer = f"There was an issue with the AI service. Please try again later or switch to 'No Agent (RAG Only)' mode. (Error: {error_type})"
                        elif "AttributeError" in error_type:
                            answer = f"I encountered a data formatting error. Please try rephrasing your question or switch to a different agent mode. (Error: {error_type})"
                        elif "KeyError" in error_type:
                            answer = f"I encountered a missing data error. Please try rephrasing your question or switch to a different agent mode. (Error: {error_type})"
                        else:
                            answer = f"I apologize, but I encountered an error processing your request with the intelligent agent. Please try again or switch to a different agent mode. (Error: {error_type})"

                        # Clear sources
                        st.session_state.last_sources = []
                        st.session_state.last_retrieved_docs = []

                elif agent_mode == "Keyword Agent" and keyword_agent:
                    try:
                        import time
                        start_time = time.time()

                        result = keyword_agent.invoke(prompt)
                        answer = result.get("final_answer", "")

                        processing_time = time.time() - start_time

                        # Store debug information
                        st.session_state.last_query_info = {
                            "query": prompt,
                            "query_type": result.get("query_type", "unknown"),
                            "tool_results": result.get("tool_results", {}),
                            "response_length": len(answer),
                            "processing_time": processing_time
                        }

                        # Store tool results for display
                        st.session_state.last_sources = []
                        st.session_state.last_retrieved_docs = []

                    except Exception as e:
                        error_type = type(e).__name__
                        error_msg = str(e)
                        logger.error(f"Error using keyword agent ({error_type}): {error_msg}", exc_info=True)

                        # Provide more specific error message based on error type
                        if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg or "quota" in error_msg.lower():
                            answer = "The AI service quota has been exceeded. The free tier allows 20 requests per day. Please try again later or switch to 'No Agent (RAG Only)' mode."
                        elif "ChatGoogleGenerativeAI" in error_type or "APIError" in error_type:
                            answer = f"There was an issue with the AI service. Please try again later or switch to 'No Agent (RAG Only)' mode. (Error: {error_type})"
                        else:
                            answer = f"I apologize, but I encountered an error processing your request with the keyword agent. Please try again or switch to a different agent mode. (Error: {error_type})"

                        # Clear sources
                        st.session_state.last_sources = []
                        st.session_state.last_retrieved_docs = []

                else:
                    # No Agent mode - use traditional RAG
                    message_history = st.session_state.messages.copy()
                    context = ""
                    retrieval_error = False

                    cfg = get_config()

                    # Check if RAG is enabled and retriever is available
                    if st.session_state.get("enable_rag", True) and retriever is not None:
                        try:
                            # Get user-selected number of results or use default
                            n_results = st.session_state.get("n_results", cfg.chroma.retrieval.n_results)

                            # Retrieve more docs if reranking is enabled (reranker will filter down)
                            retrieve_count = n_results * 2 if reranker else n_results

                            # Analyze query for metadata-based filtering/boosting
                            from src.rag.query.query_analyzer import analyze_query, boost_by_metadata_match
                            query_analysis = analyze_query(prompt)

                            # Retrieve relevant documents from ChromaDB (or hybrid search)
                            retrieved_docs = retriever.retrieve(prompt, n_results=retrieve_count)

                            # Boost results that match query entities in metadata
                            enable_metadata_boost = getattr(cfg.chroma.retrieval, 'enable_metadata_boost', True)
                            if enable_metadata_boost and query_analysis.has_filters and retrieved_docs:
                                boost_factor = getattr(cfg.chroma.retrieval, 'metadata_boost_factor', 0.1)
                                retrieved_docs = boost_by_metadata_match(
                                    retrieved_docs, query_analysis, boost_factor=boost_factor
                                )
                                logger.debug(f"Applied metadata boosting for: {query_analysis.get_boost_terms()}")

                            # Apply reranking if enabled
                            if reranker and retrieved_docs:
                                rerank_top_k = getattr(cfg.chroma.retrieval, 'rerank_top_k', n_results)
                                retrieved_docs = reranker.rerank(prompt, retrieved_docs, top_k=rerank_top_k)
                                logger.debug(f"Reranked to top {rerank_top_k} documents")

                            # Expand to parent context if small-to-big is enabled
                            enable_small_to_big = getattr(cfg.chroma.chunking, 'enable_small_to_big', False)
                            if enable_small_to_big and retrieved_docs:
                                from src.chroma.hierarchical_chunks import expand_to_parent_context
                                retrieved_docs = expand_to_parent_context(retrieved_docs)
                                logger.debug("Expanded to parent context (small-to-big)")

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

                            # Apply context compression if enabled
                            enable_compression = getattr(cfg.chroma.retrieval, 'enable_compression', False)
                            if enable_compression and context:
                                from src.rag.query.compression import compress_context
                                max_chars = getattr(cfg.chroma.retrieval, 'compression_max_chars', 8000)
                                context = compress_context(context, max_chars=max_chars)

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

                    # Generate answer with available context (RAG-only mode)
                    try:
                        import time
                        import re
                        start_time = time.time()

                        answer = process_user_prompt(model, prompt, context, message_history)

                        processing_time = time.time() - start_time

                        # Filter sources to only those cited in the answer
                        if st.session_state.last_sources and st.session_state.last_retrieved_docs:

                            # Find all citation numbers in the answer (e.g., [1], [2, 3], [1, 4, 5])
                            citation_pattern = r'\[(\d+(?:\s*,\s*\d+)*)\]'
                            matches = re.findall(citation_pattern, answer)

                            # Extract all unique cited numbers
                            cited_numbers = set()
                            for match in matches:
                                numbers = [int(n.strip()) for n in match.split(',')]
                                cited_numbers.update(numbers)

                            if cited_numbers:
                                # Get sources that were actually cited (1-indexed)
                                all_sources = st.session_state.last_sources
                                cited_sources = []
                                missing_citations = []

                                for num in sorted(cited_numbers):
                                    if 1 <= num <= len(all_sources):
                                        cited_sources.append(all_sources[num - 1])
                                    else:
                                        missing_citations.append(num)

                                if missing_citations:
                                    logger.warning(
                                        f"LLM cited sources {missing_citations} but only {len(all_sources)} sources available"
                                    )

                                # Update last_sources to only include cited sources
                                # Keep all sources if filtering would result in empty list
                                if cited_sources:
                                    st.session_state.last_sources = cited_sources
                                else:
                                    logger.warning("No valid cited sources found, keeping all sources")

                        # Store debug information for RAG-only mode
                        st.session_state.last_query_info = {
                            "query": prompt,
                            "response_length": len(answer),
                            "processing_time": processing_time,
                            "rag_enabled": st.session_state.get("enable_rag", False),
                            "docs_retrieved": len(st.session_state.get("last_retrieved_docs", []))
                        }

                    except Exception as e:
                        logger.error(f"Error generating answer: {e}")
                        answer = "I apologize, but I encountered an error while generating a response. Please try again."
                        st.error("❌ Failed to generate response. Please try asking your question again.")
                        # Clear sources on error
                        st.session_state.last_sources = []

            except TimeoutError:
                logger.warning("Request timed out")
                answer = "I apologize, but the request timed out. Please try again."
                st.session_state.last_sources = []
            except Exception as e:
                logger.error(f"Unexpected error in processing: {e}", exc_info=True)
                answer = "I apologize, but an unexpected error occurred. Please try again or contact support if the issue persists."
                st.session_state.last_sources = []

            sys_message = {"role": "ai", "answer": answer, "sources": st.session_state.last_sources}
        display_message(sys_message)
        st.session_state.messages.append(sys_message)


if __name__ == "__main__":
    main()