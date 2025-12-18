"""Sidebar component for the Streamlit app."""
import streamlit as st

from src.utils import get_config, get_initial_message


def render_sidebar(retriever=None, chroma_client=None):
    """
    Render the sidebar with app information and RAG settings.

    Args:
        retriever: ChromaRetriever instance (optional)
        chroma_client: ChromaDB client instance (optional)
    """
    cfg = get_config()

    with st.sidebar:
        st.write(
            """
            Pour Decisions uses Retrieval-Augmented Generation (RAG) and LLMs 
            to answer your wine-related questions using both curated knowledge and external pour-decisions. 🍇
            """
        )
        st.markdown("---")

        # Agent Mode Selection
        st.subheader("🤖 Agent Mode")

        # Initialize session state for agent mode if not exists
        if "agent_mode" not in st.session_state:
            st.session_state.agent_mode = "Intelligent Agent"

        agent_mode = st.selectbox(
            "Select Agent Type",
            options=["Intelligent Agent", "Keyword Agent", "No Agent (RAG Only)"],
            index=["Intelligent Agent", "Keyword Agent", "No Agent (RAG Only)"].index(st.session_state.agent_mode),
            help="""
            - **Intelligent Agent**: Uses LLM to intelligently select and chain tools. Best for complex queries.
            - **Keyword Agent**: Uses pattern matching for routing. Faster, uses fewer LLM calls, ideal for testing.
            - **No Agent (RAG Only)**: Traditional RAG without agents. Uses only wine knowledge retrieval.
            """
        )
        st.session_state.agent_mode = agent_mode

        # RAG Settings Section (only for No Agent mode)
        if agent_mode == "No Agent (RAG Only)":
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
                help="When enabled, answers are based on your wine book collection. "
                     "When disabled, uses only the LLM's general knowledge.",
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

        # Debug Section
        with st.expander("Tracking", expanded=False):
            st.caption("**Agent Debug Information**")

            # Show current agent mode
            current_mode = st.session_state.get("agent_mode", "Not set")
            st.text(f"Active Mode: {current_mode}")

            # Show last query info (if available)
            if "last_query_info" in st.session_state:
                query_info = st.session_state.last_query_info

                st.markdown("**Last Query:**")
                st.code(query_info.get("query", "N/A"), language=None)

                # Show query type (for keyword agent)
                if "query_type" in query_info:
                    st.text(f"Query Type: {query_info['query_type']}")

                # Show tools used
                if "tools_used" in query_info and query_info["tools_used"]:
                    st.markdown("**Tools Used:**")
                    for tool in query_info["tools_used"]:
                        st.text(f"  • {tool}")
                elif current_mode != "No Agent (RAG Only)":
                    st.text("Tools Used: None detected")

                # Show tool results summary (if available)
                if "tool_results" in query_info and query_info["tool_results"]:
                    st.markdown("**Tool Results:**")
                    tool_results = query_info["tool_results"]
                    for key, value in tool_results.items():
                        if isinstance(value, list):
                            st.text(f"  • {key}: {len(value)} items")
                        elif isinstance(value, dict):
                            st.text(f"  • {key}: {len(value)} keys")
                        else:
                            st.text(f"  • {key}: {str(value)[:50]}")

                # Show response length
                if "response_length" in query_info:
                    st.text(f"Response Length: {query_info['response_length']} chars")

                # Show processing time (if available)
                if "processing_time" in query_info:
                    st.text(f"Processing Time: {query_info['processing_time']:.2f}s")
            else:
                st.info("No query information available yet. Ask a question to see debug info.")

            # Show RAG status (for RAG-only mode)
            if current_mode == "No Agent (RAG Only)":
                st.markdown("**RAG Status:**")
                rag_enabled = st.session_state.get("enable_rag", False)
                st.text(f"RAG Enabled: {rag_enabled}")

                if "last_retrieved_docs" in st.session_state:
                    docs = st.session_state.last_retrieved_docs
                    st.text(f"Documents Retrieved: {len(docs)}")

        if st.button("🔄 Reset Chat"):
            st.session_state.messages = get_initial_message()
            if "last_sources" in st.session_state:
                del st.session_state.last_sources
            if "last_retrieved_docs" in st.session_state:
                del st.session_state.last_retrieved_docs
            if "last_query_info" in st.session_state:
                del st.session_state.last_query_info
            st.rerun()

