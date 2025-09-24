"""Main agent page."""
import streamlit as st
from dotenv import load_dotenv

from helper import APP_TITLE, INITIAL_MESSAGE, CONTENT_STYLE
from display import display_message, process_user_prompt

from src.model.llm import load_google_ai_model
from src.utils import get_config

load_dotenv()

# App title
st.set_page_config(page_title="Wine RAG")
st.markdown(APP_TITLE, unsafe_allow_html=True)
st.caption("Talk to your cellar!")

# Load the LLM model
@st.cache_resource
def load_llm():
    """Load model wrapper to allow caching."""
    cfg = get_config()
    model_name = cfg.model.name
    return load_google_ai_model(model_name)


model = load_llm()

# App sidebar
with st.sidebar:
    st.header("Wine RAG")
    st.write(
        "Ask questions about wine. "
    )
    st.subheader("Example questions")
    st.markdown("#")
    if st.button("Reset Chat"):
        st.session_state.messages = INITIAL_MESSAGE.copy()
        st.rerun()

# App main page
# Initialize the chat messages history
if "messages" not in st.session_state.keys():
    st.session_state.messages = INITIAL_MESSAGE.copy()

st.write(CONTENT_STYLE, unsafe_allow_html=True)

# Display past messages
if "messages" in st.session_state:
    for message in st.session_state.messages:
        display_message(message)

# Process user prompt
if prompt := st.chat_input("Type your question here"):
    user_message = {"role": "human", "question": prompt}
    display_message(user_message)
    
    # Get only messages from the human for the ChatPromptTemplate
    human_messages = [("human", msg['question']) for msg in st.session_state.messages if msg["role"] == "human"]

    st.session_state.messages.append(user_message)
    with st.spinner("Thinking...", show_time=True):
        try:
            content = process_user_prompt(model, prompt, human_messages)
        except TimeoutError as _:
            pass
        sys_message = {"role": "ai", **content}
    display_message(sys_message)
    st.session_state.messages.append(sys_message)

