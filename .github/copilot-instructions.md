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
- **Formatting**: Black (120 chars, isort for imports
- **Naming**: Use wine domain terms (vintage, appellation, not year, location)

### Coding Requirements
- Do not generate markdown files to explain the code generated unless explicitly requested. Markdown files
  are only needed for project documentation and design, not code explanations.
- Do not use emojis in code comments, docstrings, logs.
- Generated code must be less verbose, only use comments where necessary for clarity.
- Avoid redundant code; use helper functions or classes to encapsulate repeated logic.
- Avoid using a lot of print statements, only use logging where appropriate.

### Critical Constraints
1. **Minimize LLM calls** - Use keyword routing, not LLM classification
2. **Local-first** - Prefer database queries and calculations over external APIs
3. **No paid services** - All tools must be free or have a generous free tier to minimize cost (DuckDuckGo, not SerpAPI)
4. **Cache results** - Avoid repeated expensive operations

## Development Workflow

### Steps for New Features
1. **Understand wine domain** - Research wine concept before coding
2. **Check free-tier impact** - How many LLM calls will this need?
3. **Design local-first** - Can this work without external APIs?
4. **Use wine terminology** - Proper names in code and comments
5. **Add type hints** - All parameters and returns
6. **Test with real data** - Use actual wine examples
7. **Review for verbosity** - Remove unnecessary comments and prints
