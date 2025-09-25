"""Custom CSS/HTML code used in the UI."""
import streamlit as st
import html


CONTENT_STYLE = """
<style> 
#input-container { 
    position: fixed; 
    bottom: 0; 
    width: 100%; 
    padding: 10px; 
    background-color: white; 
    z-index: 100; 
}

.user-avatar, .bot-avatar {
    width: 40px;
    height: 40px;
    border-radius: 50%;
    object-fit: cover;
    margin-bottom: -10px;
}
.user-avatar {
    float: right;
    margin-left: 5px;
}
.bot-avatar {
    float: left;
    margin-right: 5px;
}
.user-bubble {
    background: #e6f4ea;
    color: #222;
    border-radius: 20px 20px 4px 20px;
    padding: 14px 18px;
    margin-right: 8px;
    max-width: 70%;
    font-size: 0.98em;
    box-shadow: 0 2px 8px rgba(91,140,42,0.08);
    line-height: 1.5;
    word-break: break-word;
}
.bot-bubble {
    background: #ede7f6;
    color: #222;
    border-radius: 20px 20px 20px 4px;
    padding: 14px 18px;
    max-width: 70%;
    font-size: 0.98em;
    box-shadow: 0 2px 8px rgba(123,31,162,0.08);
    line-height: 1.5;
    word-break: break-word;
}
</style>
"""


def make_app_title(title: str, subtitle: str) -> str:
    """
    Returns a styled HTML/CSS string for a custom app title and subtitle.
    Args:
        title (str): The main title text.
        subtitle (str): The subtitle text (smaller font).
    Returns:
        str: HTML/CSS for the styled title and subtitle.
    """
    return f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@700;900&display=swap');
    .rag-title {{
      font-family: 'Poppins', sans-serif;
      font-weight: 700;
      font-size: 4em;
      background: linear-gradient(90deg, #7b1fa2 0%, #a4508b 50%, #5e3370 100%);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      background-clip: text;
      color: transparent;
      margin: 0;
      padding: 20px 0 0 0;
      text-align: center;
    }}
    .rag-subtitle {{
      font-family: 'Poppins', sans-serif;
      font-weight: 400;
      font-size: 1.5em;
      color: #5b8c2a;
      margin: 0;
      padding: 0 0 20px 0;
      text-align: center;
    }}
    </style>
    <div class="rag-title">{title}</div>
    <div class="rag-subtitle">{subtitle}</div>
    """


def format_user_message(message: dict) -> str:
    """Format a user message with improved style and emoji avatar"""
    message_text = html.escape(message["question"])
    avatar_emoji = "🧑‍💼"  # person in suit
    return f"""
    <div style="display:flex; align-items:flex-end; justify-content:flex-end; margin-bottom:18px;">
        <div class="user-bubble">{message_text}</div>
        <span class="user-avatar" style="display:flex; align-items:center; justify-content:center; font-size:2em; background:#e6f4ea;">{avatar_emoji}</span>
    </div>
    """


def format_assistant_message(message: dict) -> str:
    """Format an assistant message with improved style and emoji avatar"""
    message_text = html.escape(message["answer"])
    avatar_emoji = "🍇" # grapes
    return f"""
    <div style="display:flex; align-items:flex-end; justify-content:flex-start; margin-bottom:18px;">
        <span class="bot-avatar" style="display:flex; align-items:center; justify-content:center; font-size:2em; background:#ede7f6;">{avatar_emoji}</span>
        <div class="bot-bubble">{message_text}</div>
    </div>
    """


def display_message(message: dict):
    """Display a message in the UI."""
    if message["role"] == "human":
        container_html = format_user_message(message)
        st.markdown(container_html, unsafe_allow_html=True)

    if message["role"] == "ai":
        container_html = format_assistant_message(message)
        st.write(container_html, unsafe_allow_html=True)
