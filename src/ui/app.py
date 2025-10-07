"""Main agent page."""
import streamlit as st


from display import display_message, make_app_title, CONTENT_STYLE

from src.model.llm import load_base_model, process_user_prompt
from src.utils import get_config, get_initial_message

load_dotenv()

# App title and description
st.set_page_config(page_title="Pour Decisions: Let the bot choose your bottle 🍷🤖", page_icon="🍷")
st.markdown(make_app_title(
    "Pour Decisions",
    "Let the bot choose your bottle 🍷"
), unsafe_allow_html=True)
# st.caption("""
# Sip, chat, and never whine alone! Pour Decisions is your AI-powered wine sidekick—ready to uncork facts,
# pairings, and grape wisdom.
# """, unsafe_allow_html=True)

# Load the LLM model
@st.cache_resource
def load_llm():
    """Load model wrapper to allow caching."""
    cfg = get_config()
    return load_base_model(cfg.model.provider, cfg.model.name)


model = load_llm()

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
            context = ""  # No external context retrieval in this version
            answer = process_user_prompt(model, prompt, context, message_history)
        except TimeoutError as _:
            answer = ""
        sys_message = {"role": "ai", "answer": answer}
    display_message(sys_message)
    st.session_state.messages.append(sys_message)
