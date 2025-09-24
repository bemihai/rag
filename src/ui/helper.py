"""Custom CSS/HTML code used in the UI."""
from src.utils import get_config

def get_initial_message():
    cfg = get_config()
    msg = cfg.initial_message
    return [
        {
            "role": msg["role"] if "role" in msg else "ai",
            "answer": msg["answer"] if "answer" in msg else "Welcome! Ask me anything about wine."
        }
    ]

APP_TITLE = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@700;900&display=swap');

.rag-title {
  font-family: 'Poppins', sans-serif;
  font-weight: 700;
  font-size: 4em;
  background: linear-gradient(90deg, #ee6109);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  margin: 0;
  padding: 20px 0;
  text-align: center;
}
</style>
<div class="rag-title">Wine RAG</div>
"""

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
 
.user-avatar { 
    float: right; 
    width: 40px; 
    height: 40px; 
    margin-left: 5px; 
    margin-bottom: -10px; 
    border-radius: 50%; 
    object-fit: cover; 
} 

.bot-avatar { 
    float: left; 
    width: 40px; 
    height: 40px; 
    margin-right: 5px; 
    border-radius: 50%; 
    object-fit: cover; 
} 
</style>
"""