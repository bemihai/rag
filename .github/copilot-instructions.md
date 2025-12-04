# GitHub Copilot Instructions for Pour Decisions Wine RAG Project

## Project Overview
**Pour Decisions** - A RAG-powered wine chatbot for personal wine knowledge and cellar management. Zero-cost hobby project using free-tier services only.

## Tech Stack
- **RAG**: ChromaDB vector store + LangChain + Google Gemini LLM (free tier)
- **Embeddings**: sentence-transformers/all-MiniLM-L6-v2 (local)
- **UI**: Streamlit
- **Backend**: Python 3.11+, SQLite, Pydantic
- **IDE**: PyCharm Professional

## Project Structure
```
src/
├── database/       # SQLite models for wine cellar data
├── etl/           # Import from Vivino, CellarTracker
├── model/         # RAG pipeline, LLM integration, prompts
├── rag/           # Vector store, retrieval, document chunking
├── ui/            # Streamlit pages and components
└── utils/         # Config, logging, helpers
```

## Code Style Standards

### Python Requirements
- **Type hints**: REQUIRED for all function parameters and returns
- **Docstrings**: Google-style for all public functions
- **Formatting**: Black (120 chars), isort for imports
- **Naming**: Use wine domain terms (vintage, appellation, not year, location)

### Example Pattern
```python
def calculate_drinking_window(
    vintage: int,
    appellation: str,
    grape_varieties: List[str]
) -> DrinkingWindow:
    """Calculate optimal drinking period for wine.
    
    Args:
        vintage: Year grapes were harvested (1800-present)
        appellation: Wine region (e.g., "Barolo DOCG")
        grape_varieties: Primary grapes (e.g., ["Nebbiolo"])
        
    Returns:
        DrinkingWindow with peak years and current status
    """
```

## Free-Tier Optimization Rules

### Critical Constraints
1. **Minimize LLM calls** - Use keyword routing, not LLM classification
2. **Local-first** - Prefer database queries and calculations over external APIs
3. **No paid services** - All tools must be free or have a generous free tier to minimize cost (DuckDuckGo, not SerpAPI)
4. **Cache results** - Avoid repeated expensive operations

### Pattern: One LLM Call Per Query
```python
def process_query(question: str) -> str:
    # Step 1: Route by keywords (NO LLM)
    query_type = classify_by_keywords(question)
    
    # Step 2: Gather data locally (NO LLM)
    data = get_data_from_local_source(question, query_type)
    
    # Step 3: SINGLE LLM call for final answer
    return generate_answer_with_llm(question, data)
```

## Development Workflow

### Steps for New Features
1. **Understand wine domain** - Research wine concept before coding
2. **Check free-tier impact** - How many LLM calls will this need?
3. **Design local-first** - Can this work without external APIs?
4. **Use wine terminology** - Proper names in code and comments
5. **Add type hints** - All parameters and returns
6. **Test with real data** - Use actual wine examples

### Example Feature Flow
```
New Feature: "Show my Burgundy wines"
↓
1. Design SQLite schema for wine cellar
2. Implement local database query (free)
3. Add keyword routing for "my wines" queries
4. Single LLM call to format results naturally
5. Test with realistic wine data
```

## Prompt Considerations

## Common Patterns

### Wine Data Model
```python
@dataclass
class Wine:
    name: str
    producer: str
    vintage: int
    appellation: str
    grape_varieties: List[str]
    tasting_notes: Optional[str] = None
```

### Database Query
```python
def get_wines_by_region(region: str) -> List[Wine]:
    """Query local SQLite - completely free."""
    # Use proper wine filtering logic
```

### RAG Retrieval
```python
def search_wine_knowledge(query: str) -> List[Document]:
    """Semantic search in ChromaDB vector store."""
    # Include wine metadata in search
```

This configuration helps Copilot understand your wine RAG project and generate code that follows your patterns and constraints.
