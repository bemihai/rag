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
.sources-container {
    margin-top: 12px;
    padding: 8px 0;
    font-size: 0.65em;
}
.sources-title {
    font-weight: 600;
    color: #7b1fa2;
    margin-bottom: 4px;
    font-size: 0.85em;
}
.source-item {
    padding: 2px 0;
    color: #555;
    line-height: 1.2;
}
.source-name {
    font-weight: 500;
    color: #333;
}
.source-details {
    color: #666;
    font-size: 0.85em;
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


def get_relevance_indicator(score: float) -> str:
    """
    Get a visual indicator for source relevance quality.

    Args:
        score: Relevance score (0.0 to 1.0)

    Returns:
        Emoji indicator for quality level
    """
    if score >= 0.8:
        return "🟢"  # Green circle - Excellent
    elif score >= 0.6:
        return "🟡"  # Yellow circle - Good
    elif score >= 0.4:
        return "🟠"  # Orange circle - Fair
    else:
        return "🔴"  # Red circle - Low


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


def format_assistant_message(message: dict, sources: list = None) -> str:
    """Format an assistant message with improved style and emoji avatar.

    Args:
        message: Dictionary containing the answer text.
        sources: Optional list of tuples (source_name, page_number, relevance_score).

    Returns:
        HTML string with formatted message and sources.
    """
    message_text = html.escape(message["answer"])
    avatar_emoji = "🍇" # grapes

    # Build sources HTML if provided
    sources_html = ""
    if sources:
        # Group sources by name and keep track of indexes, pages and highest relevance
        grouped_sources = {}
        for idx, (source_name, page_number, relevance_score) in enumerate(sources, 1):
            if source_name not in grouped_sources:
                grouped_sources[source_name] = {
                    'indexes': [],
                    'pages': [],
                    'max_relevance': relevance_score
                }

            # Add original index
            grouped_sources[source_name]['indexes'].append(idx)

            # Add page if valid
            if page_number is not None and page_number >= 0:
                if page_number not in grouped_sources[source_name]['pages']:
                    grouped_sources[source_name]['pages'].append(page_number)

            # Update max relevance
            if relevance_score is not None:
                current_max = grouped_sources[source_name]['max_relevance']
                if current_max is None or relevance_score > current_max:
                    grouped_sources[source_name]['max_relevance'] = relevance_score

        # Build HTML for grouped sources
        sources_items = []
        for source_name, data in grouped_sources.items():
            indexes = data['indexes']
            pages = sorted(data['pages'])
            relevance_score = data['max_relevance']

            # Format indexes
            if len(indexes) == 1:
                indexes_text = f"{indexes[0]}."
            else:
                indexes_text = f"{', '.join(map(str, indexes))}."

            # Format pages
            if pages:
                if len(pages) == 1:
                    page_text = f", Page {pages[0]}"
                elif len(pages) <= 3:
                    page_text = f", Pages {', '.join(map(str, pages))}"
                else:
                    page_text = f", Pages {pages[0]}-{pages[-1]}"
            else:
                page_text = ""

            # Add visual indicator at the front
            if relevance_score is not None:
                indicator = get_relevance_indicator(relevance_score)
            else:
                indicator = "⚪"  # White circle for unknown relevance

            sources_items.append(
                f'<div class="source-item">'
                f'{indicator} <span class="source-name">{indexes_text} {html.escape(str(source_name))}</span>'
                f'<span class="source-details">{page_text}</span>'
                f'</div>'
            )

        sources_html = f"""
<div class="sources-container">
    <div class="sources-title">📚 Sources:</div>
    {''.join(sources_items)}
</div>"""

    return f"""
<div style="display:flex; align-items:flex-start; justify-content:flex-start; margin-bottom:18px;">
    <span class="bot-avatar" style="display:flex; align-items:center; justify-content:center; font-size:2em; background:#ede7f6;">{avatar_emoji}</span>
    <div class="bot-bubble">
        {message_text}{sources_html}
    </div>
</div>"""


def display_message(message: dict):
    """Display a message in the UI.

    Args:
        message: Dictionary containing role, question/answer, and optionally sources.
                 For AI messages, may include 'sources' as a list of tuples
                 (source_name, page_number, relevance_score).
    """
    if message["role"] == "human":
        container_html = format_user_message(message)
        st.markdown(container_html, unsafe_allow_html=True)

    if message["role"] == "ai":
        sources = message.get("sources", [])
        container_html = format_assistant_message(message, sources)
        st.markdown(container_html, unsafe_allow_html=True)
