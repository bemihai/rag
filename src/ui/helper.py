"""Custom CSS/HTML code used in the UI."""

NO_DATA_ANSWERS = [
    "No results found.",
    "An error occurred while executing the query",
    "I can't generate a query for your question",
    "I can't extract the relevant columns to your question",
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

INITIAL_MESSAGE = [
    {
        "role": "ai",
        "initial": True,
        "answer": "Hey there! How can I help you today?",
        "data": None,
        "query": None,
        "schema": None,
    },
]

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