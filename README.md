# Pour Decisions 🍷🤖

> A wine expert chatbot powered by Retrieval-Augmented Generation (RAG) and Large Language Models

Pour Decisions is an intelligent wine assistant that combines the power of LLMs with a curated knowledge base of professional wine books. Using RAG, it provides accurate, source-cited answers to wine-related questions.

## Features

- **RAG-Powered Answers**: Retrieves relevant information from professional wine books before generating responses
- **Source Citations**: Every answer includes references to the source material
- **Hybrid Search**: Combines vector similarity (semantic) and BM25 (keyword) search for better retrieval
- **Cross-Encoder Reranking**: Improves precision by reranking retrieved documents
- **Wine Terminology**: Built-in wine dictionary for query normalization and expansion
- **Wine Metadata Extraction**: Automatically extracts grapes, regions, vintages from documents
- **Incremental Indexing**: Only processes new or modified files when updating the knowledge base
- **Query Caching**: LRU cache for faster repeated queries
- **Semantic Deduplication**: Removes near-duplicate chunks from context
- **Interactive UI**: User-friendly Streamlit interface with real-time source viewing
- **Graceful Fallback**: Seamlessly falls back to LLM general knowledge when retrieval fails
- **Conversation Aware**: Handles follow-up questions using conversation history

## Table of Contents

- [Architecture](#architecture)
- [RAG Implementation](#rag-implementation)
- [Setup & Installation](#setup--installation)
- [Usage](#usage)
- [Configuration](#configuration)
- [Project Structure](#project-structure)
- [Development](#development)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      User Interface (Streamlit)             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │ Chat Input   │  │ RAG Controls │  │   Sources    │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    RAG Pipeline                             │
│                                                             │
│  1. Query Preprocessing                                     │
│     - Wine terminology normalization                        │
│     - Query expansion with related terms                    │
│                                                             │
│  2. Hybrid Retrieval                                        │
│     ┌─────────────────┐    ┌─────────────────┐             │
│     │  Vector Search  │    │  BM25 Search    │             │
│     │   (ChromaDB)    │    │  (Keyword)      │             │
│     └────────┬────────┘    └────────┬────────┘             │
│              │                      │                       │
│              └──────────┬───────────┘                       │
│                         ▼                                   │
│              ┌─────────────────────┐                        │
│              │  Reciprocal Rank    │                        │
│              │  Fusion (RRF)       │                        │
│              └──────────┬──────────┘                        │
│                         ▼                                   │
│  3. Reranking (Cross-Encoder)                               │
│     - Score query-document pairs                            │
│     - Return top-k most relevant                            │
│                                                             │
│  4. Context Building                                        │
│     - Semantic deduplication                                │
│     - Format with source metadata                           │
│                                                             │
│  5. LLM Generation (Google Gemini)                          │
│     - Conversation-aware prompts                            │
│     - Citation requirements                                 │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
                      ┌─────────────────┐
                      │ Answer + Sources│
                      └─────────────────┘
```

## RAG Implementation

### 1. **Document Ingestion & Storage**

Wine books are processed and stored in ChromaDB:

```
src/rag/
├── load_data.py     # CLI for data ingestion
├── loader.py        # CollectionDataLoader class
├── chunks.py        # Chunking strategies
└── index_tracker.py # Incremental indexing manifest
```

**Features:**
- Multiple chunking strategies: Basic, By Title, Semantic
- Wine metadata extraction (grapes, regions, vintages, classifications)
- Document context extraction (title, chapter, section)
- Incremental indexing - only new/modified files are processed
- Content hash-based duplicate detection

**Run data loading:**
```bash
make chroma-upload    # Incremental (default)
make chroma-reindex   # Force reindex all
make chroma-status    # View index status
```

### 2. **Retrieval Component**

The retriever uses hybrid search combining vector and keyword matching:

```
src/rag/
├── retriever.py        # ChromaRetriever (vector search)
├── bm25_search.py      # BM25Index (keyword search)
├── hybrid_retriever.py # HybridRetriever (RRF fusion)
├── reranker.py         # DocumentReranker (cross-encoder)
└── wine_terms.py       # Wine terminology dictionary
```

**Key Features:**
- **Query Preprocessing**: Wine term normalization and expansion
- **Hybrid Search**: Vector (70%) + BM25 (30%) with RRF fusion
- **Cross-Encoder Reranking**: `ms-marco-MiniLM-L-6-v2` for precision
- **Query Caching**: LRU cache (100 queries) for repeated queries
- **Similarity Filtering**: Configurable threshold (default: 0.3)

### 3. **Context Building**

Retrieved chunks are formatted into context for the LLM:

```
src/rag/deduplication.py    # Semantic deduplication
src/utils/context_builder.py # Context formatting
```

**Features:**
- Hash-based exact duplicate removal
- Semantic deduplication using embeddings
- Source metadata formatting (filename, page, chunk_id)
- Configurable deduplication threshold (default: 0.9)

### 4. **Prompt Engineering**

Custom prompts ensure the LLM uses the context effectively:

```
src/agents/prompts/
├── rag_only_system_prompt.md  # System behavior
└── rag_only_user_prompt.md    # Context + question format
```

**System Prompt Features:**
- Prioritize retrieved context over general knowledge
- Require source citations (e.g., "[1]", "[2]")
- Handle follow-up questions using conversation history
- Prevent hallucination of wine facts
- Only cite sources that exist in provided context

### 5. **LLM Integration**

Supports multiple LLM providers:
- **Google Gemini** (default): `gemini-2.5-flash`
- **OpenAI**: GPT models (configurable)

**Configuration:**
```yaml
model:
  provider: google
  name: gemini-2.5-flash
```

### 6. **Error Handling & Fallbacks**

Robust error handling at every level:

| Component | Error Scenario | Fallback Behavior |
|-----------|---------------|--------------------|
| ChromaDB Connection | Server unavailable | Disable RAG, use LLM only |
| Retriever | Query fails | Empty context, continue with LLM |
| Context Building | No results found | Empty context, LLM general knowledge |
| LLM | API error | Show error message, allow retry |
| Network | Timeout | Show timeout message, retry option |

**User Experience:**
- System status indicator (✅ Connected / ❌ Unavailable)
- Clear error messages (no cryptic errors)
- Seamless degradation to LLM-only mode
- No crashes or broken functionality

## Setup & Installation

### Quick Start with Docker (Recommended)

The easiest way to run Pour Decisions is with Docker Compose:

```bash
# 1. Clone the repository
git clone <your-repo-url>
cd pour-decisions

# 2. Copy environment file and add your Google API key
cp .env.example .env
nano .env  # Add your GOOGLE_API_KEY

# 3. Run the quick start script
./quickstart.sh

# Or manually:
docker-compose up --build
```

Access the app at: **http://localhost:8501**

That's it! Docker Compose will:
- ✅ Build the application container
- ✅ Start ChromaDB vector store
- ✅ Set up persistent storage
- ✅ Configure networking between services

**See [DEPLOYMENT.md](DEPLOYMENT.md) for production deployment guides (Render.com, Fly.io, VPS).**

---

### Manual Installation (Development)

For local development without Docker:

### Prerequisites

- Python 3.11+
- Google API Key (for Gemini) or OpenAI API Key

### 1. Clone the Repository

```bash
git clone <your-repo-url>
cd pour-decisions
```

### 2. Install Dependencies

```bash
# Using uv (recommended)
pip install uv
uv pip install --group ui

# Or using pip
pip install -r requirements.txt
```

### 3. Configure Environment

Create a `.env` file:

```bash
# LLM Provider
GOOGLE_API_KEY=your_google_api_key_here

# ChromaDB Settings (for local ChromaDB server)
CHROMA_HOST=localhost
CHROMA_PORT=8000

# Optional: Langfuse (for tracing)
LANGFUSE_SECRET_KEY=your_key
LANGFUSE_PUBLIC_KEY=your_key
LANGFUSE_HOST=https://cloud.langfuse.com
```

### 4. Start ChromaDB

**Option A: Using Docker (easiest)**
```bash
docker run -p 8000:8000 -v chroma-cellar-data:/chroma/chroma chromadb/chroma:latest
```

**Option B: Using Python**
```bash
pip install chromadb
chroma run --path ./chroma-cellar-data
```

### 5. Load Your Wine Books

Place your PDF/text files in the configured directory and run:

```bash
python src/rag/load_data.py
```

This will:
- Process and chunk your documents
- Generate embeddings
- Store everything in ChromaDB

### 6. Run the App

```bash
streamlit run src/ui/app.py
```

Open your browser to `http://localhost:8501`

## Usage

### Basic Questions

Ask any wine-related question:
- "What is the difference between Merlot and Cabernet Sauvignon?"
- "How should I store an opened bottle of wine?"
- "What are the main wine regions in France?"
- "Suggest a wine pairing for spicy Thai food."

### RAG Controls (Sidebar)

**System Status:**
- ✅ RAG System: Connected → ChromaDB is working
- ❌ RAG System: Unavailable → Using LLM only

**Settings:**
- **Enable RAG Retrieval**: Toggle retrieval on/off
- **Number of sources**: Slider (1-10) to control how many chunks to retrieve
- **Show relevance scores**: Display similarity percentages

**View Sources:**
- Expandable cards for each retrieved source
- Shows filename, page number
- Relevance indicators (🟢 High, 🟡 Medium, 🟠 Low)
- Content snippets from each source

### Example Interaction

**User:** "What makes Burgundy wines special?"

**App:**
1. Retrieves 5 relevant chunks from wine books
2. Shows sources in sidebar:
   - 📄 Burgundy_Complete_Guide.pdf (Page 23) - 85% relevance
   - 📄 French_Wine_Regions.pdf (Page 67) - 78% relevance
   - ...
3. Generates answer with citations:
   > "According to Source 1, Burgundy wines are renowned for their terroir-driven character. The region's limestone-rich soils (Source 2) contribute to..."

## Configuration

### `app_config.yml`

```yaml
chroma:
  client:
    host: localhost
    port: 8000
  
  chunking:
    strategy: by_title           # basic, by_title, semantic
    chunk_size: 1024
    chunk_overlap: 256
    extract_wine_metadata: true  # extract grape, region, vintage
  
  retrieval:
    n_results: 5                 # chunks per query
    similarity_threshold: 0.3   # minimum similarity (0.0-1.0)
    # Deduplication
    use_deduplication: true
    deduplication_threshold: 0.9
    # Hybrid search
    enable_hybrid: true
    hybrid_vector_weight: 0.7
    hybrid_keyword_weight: 0.3
    # Reranking
    enable_reranking: true
    reranker_model: cross-encoder/ms-marco-MiniLM-L-6-v2
    rerank_top_k: 5
  
  settings:
    batch_size: 2500
    embedder: sentence-transformers/all-MiniLM-L6-v2
  
  collections:
    - name: wine_books
      local_data_path: /path/to/your/wine/books
      metadata:
        description: "Professional wine books collection"
        hnsw:space: cosine

model:
  provider: google
  name: gemini-2.5-flash

initial_message:
  answer: "Hi there! Ask me anything about wine."
```

### Key Parameters

| Parameter | Description | Default | Recommended Range |
|-----------|-------------|---------|-------------------|
| `n_results` | Number of chunks to retrieve | 5 | 3-10 |
| `similarity_threshold` | Minimum similarity to include | 0.3 | 0.2-0.5 |
| `chunk_size` | Size of document chunks | 1024 | 512-2048 |
| `chunk_overlap` | Overlap between chunks | 256 | 128-512 |
| `deduplication_threshold` | Similarity for dedup | 0.9 | 0.85-0.95 |
| `enable_hybrid` | Use hybrid search | true | true/false |
| `enable_reranking` | Use cross-encoder reranking | true | true/false |
| `rerank_top_k` | Results after reranking | 5 | 3-10 |

## Project Structure

```
pour-decisions/
├── src/
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── llm.py                 # LLM initialization & invocation
│   │   └── prompts/               # System & user prompts
│   │
│   ├── database/
│   │   ├── db.py                  # SQLite database
│   │   ├── models.py              # Wine cellar models
│   │   └── repository/            # Data access layer
│   │
│   ├── rag/
│   │   ├── __init__.py
│   │   ├── bm25_search.py         # BM25 keyword search
│   │   ├── chunks.py              # Chunking strategies
│   │   ├── deduplication.py       # Semantic deduplication
│   │   ├── hybrid_retriever.py    # Hybrid search (RRF)
│   │   ├── index_tracker.py       # Incremental indexing
│   │   ├── load_data.py           # CLI for data ingestion
│   │   ├── loader.py              # Collection data loader
│   │   ├── metadata_extractor.py  # Wine metadata extraction
│   │   ├── reranker.py            # Cross-encoder reranking
│   │   ├── retriever.py           # ChromaDB vector search
│   │   └── wine_terms.py          # Wine terminology dictionary
│   │
│   ├── ui/
│   │   ├── __init__.py
│   │   ├── app.py                 # Main Streamlit app
│   │   ├── resources.py           # Cached resources
│   │   ├── sidebar.py             # Sidebar components
│   │   ├── helper/                # UI helpers
│   │   └── pages/                 # Streamlit pages
│   │
│   └── utils/
│       ├── __init__.py
│       ├── chroma.py              # ChromaDB utilities
│       ├── context_builder.py     # Context formatting
│       ├── env.py                 # Environment variables
│       ├── logger.py              # Logging setup
│       ├── tracing.py             # Langfuse integration
│       └── utils.py               # General utilities
│
├── docs/
│   ├── pour-decisions-rag-pipeline.md  # RAG documentation
│   └── quick-reference.md
│
├── design/
│   └── rag/
│       └── rag-improvement-plan.md     # Improvement roadmap
│   
├── chroma-data/                   # ChromaDB storage
│   └── manifests/                 # Index tracking manifests
├── cellar-data/                   # Wine cellar SQLite DB
├── app_config.yml                 # App configuration
├── docker-compose.yml             # Docker setup
├── Makefile                       # Development commands
├── pyproject.toml                 # Dependencies
└── README.md                      # This file
```

## Development

### Makefile Commands

```bash
# Application
make run              # Run app locally with ChromaDB

# ChromaDB Management
make chroma-up        # Start ChromaDB container
make chroma-down      # Stop ChromaDB container
make chroma-health    # Check container health
make chroma-reset     # Reset ChromaDB (clear all data)
make chroma-backup    # Backup ChromaDB data
make chroma-restore   # Restore from backup

# Data Indexing
make chroma-upload    # Index new/modified files (incremental)
make chroma-reindex   # Force reindex all files
make chroma-status    # Show index status

# Wine Cellar Database
make cellar-init      # Initialize database
make cellar-info      # Show database info
make cellar-backup    # Backup database
```

### Testing the RAG Pipeline

1. **Test with ChromaDB running:**
   ```bash
   make chroma-up
   make run
   ```
   - Verify retrieval works
   - Check source citations appear
   - Confirm relevance scores are reasonable

2. **Test without ChromaDB (fallback):**
   ```bash
   make chroma-down
   make run
   ```
   - Should show "RAG System: Unavailable"
   - RAG toggle should be disabled
   - App should still answer questions using LLM only

3. **Test edge cases:**
   - Ask questions not in your knowledge base
   - Try with 1 vs 10 sources
   - Toggle deduplication on/off
   - Test with very specific queries

### Adding New Collections

1. Update `app_config.yml`:
   ```yaml
   collections:
     - name: wine_books
       local_data_path: /path/to/books
     - name: wine_reviews      # New collection
       local_data_path: /path/to/reviews
   ```

2. Reload data:
   ```bash
   make chroma-upload
   ```

3. Update app.py to query multiple collections (if needed)

### Customizing Prompts

Edit `src/agents/prompts/` to customize:
- System behavior
- Citation format
- Fallback messages
- Response style

### Monitoring & Tracing

The app integrates with Langfuse for observability:
- Track all LLM calls
- Monitor retrieval quality
- Analyze user queries
- Debug issues in production

## Troubleshooting

### "ModuleNotFoundError: No module named 'src'"

**Solution:** Run from project root with correct PYTHONPATH:
```bash
PYTHONPATH=$(pwd) python3 -m src.rag.load_data
# or use
make chroma-upload
```

### "Unable to connect to ChromaDB"

**Check:**
```bash
make chroma-health   # Is container running?
docker ps            # Is port 8000 exposed?
```

**Fix:**
```bash
make chroma-up
```

### "No results found for query"

**Possible causes:**
- Knowledge base is empty → Run `make chroma-upload`
- Similarity threshold too high → Lower it in config
- Question not related to wine books → Expected behavior

### App crashes or shows errors

**Check logs:**
- Streamlit terminal output
- `docker logs pour_decisions_chromadb` for ChromaDB
- Verify API keys are set correctly

## Performance Considerations

- **Embedding Model**: `all-MiniLM-L6-v2` is fast but lightweight. For better quality, consider `all-mpnet-base-v2`
- **Chunk Size**: Larger chunks (1024-2048) provide more context but may reduce precision
- **Number of Results**: More results (7-10) give better coverage but slower response time
- **Deduplication**: Adds processing time but improves context quality

## Contributing

Contributions welcome! Areas for improvement:
- Support for more embedding models
- Additional LLM providers
- Multi-collection querying
- Small-to-big retrieval (retrieve small chunks, return larger context)
- Prompt compression for reducing token usage
- Knowledge graph integration

## License

[Your License Here]

## Acknowledgments

- **LangChain** for RAG framework components
- **ChromaDB** for vector database
- **Streamlit** for the UI framework
- **Sentence Transformers** for embeddings
- **Google Gemini** for LLM capabilities

---

Built with ❤️ for wine enthusiasts 🍷


