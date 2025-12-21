# Pour Decisions 🍷🤖

> A wine expert chatbot powered by Retrieval-Augmented Generation (RAG) and Large Language Models

Pour Decisions is an intelligent wine assistant that combines the power of LLMs with a curated knowledge base of professional wine books. Using RAG, it provides accurate, source-cited answers to wine-related questions.

## 🌟 Features

- **RAG-Powered Answers**: Retrieves relevant information from professional wine books before generating responses
- **Source Citations**: Every answer includes references to the source material
- **Interactive UI**: User-friendly Streamlit interface with real-time source viewing
- **Flexible Retrieval**: Adjustable number of sources and relevance thresholds
- **Graceful Fallback**: Seamlessly falls back to LLM general knowledge when retrieval fails
- **Semantic Search**: Uses sentence transformers for accurate document retrieval
- **Error Handling**: Robust error handling ensures the app always works, even if ChromaDB is unavailable

## 📋 Table of Contents

- [Architecture](#architecture)
- [RAG Implementation](#rag-implementation)
- [Setup & Installation](#setup--installation)
- [Usage](#usage)
- [Configuration](#configuration)
- [Project Structure](#project-structure)
- [Development](#development)

## 🏗️ Architecture

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
│  1. Query Embedding    ───────────────────────────┐         │
│     (sentence-transformers)                       │         │
│                                                   │         │
│  2. Vector Search      ◄──────────────────────────┘         │
│     (ChromaDB)                                              │
│                                                             │
│  3. Context Building                                        │
│     - Format chunks with metadata                           │
│     - Semantic deduplication (optional)                     │
│     - Source citations                                      │
│                                                             │
│  4. Prompt Engineering                                      │
│     - System prompt with instructions                       │
│     - Context injection                                     │
│     - Citation requirements                                 │
│                                                             │
│  5. LLM Generation                                          │
│     (Google Gemini / OpenAI)                                │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
                      ┌─────────────────┐
                      │ Answer + Sources│
                      └─────────────────┘
```

## 🔍 RAG Implementation

### 1. **Document Ingestion & Storage**

Wine books are processed and stored in ChromaDB:

```python
# src/rag/load_data.py
- Splits documents into chunks (configurable size and overlap)
- Supports multiple chunking strategies:
  - Basic: Fixed-size chunks
  - By Title: Section-based chunks
  - Semantic: AI-powered semantic chunking
- Generates embeddings using sentence-transformers
- Stores in ChromaDB with metadata (source, page, chunk_id)
```

**Run data loading:**
```bash
make db-load
```

### 2. **Retrieval Component**

The retriever finds relevant documents for user queries:

```python
# src/agents/retriever.py
class ChromaRetriever:
    - Embeds user query using same model as documents
    - Queries ChromaDB for top-k most similar chunks
    - Returns documents with similarity scores
    - Filters by configurable similarity threshold
```

**Key Features:**
- Uses `sentence-transformers/all-MiniLM-L6-v2` for embeddings
- Cosine similarity for matching
- Configurable number of results (1-10)
- Minimum similarity threshold filtering (default: 0.3)

### 3. **Context Building**

Retrieved chunks are formatted into context for the LLM:

```python
# src/utils/context_builder.py

build_context_from_chunks():
    - Formats chunks with source metadata
    - Includes page numbers and filenames
    - Clear separators between chunks
    
build_context_with_deduplication():
    - Removes semantically similar duplicates
    - Uses embedding-based similarity comparison
    - Configurable deduplication threshold (0.9)
```

**Example formatted context:**
```
[Source 1 - Wine_Essentials.pdf, Page 42]
Merlot is a red wine grape variety that produces wines with...
---
[Source 2 - Bordeaux_Guide.pdf, Page 15]
Cabernet Sauvignon differs from Merlot in its tannin structure...
```

### 4. **Prompt Engineering**

Custom prompts ensure the LLM uses the context effectively:

**System Prompt:**
- Instructs model to prioritize retrieved context
- Requires source citations (e.g., "According to Source 1...")
- Specifies fallback behavior when context is insufficient
- Prevents hallucination of wine facts

**User Prompt:**
- Clear structure with context first, then question
- Step-by-step instructions for using sources
- Citation format requirements

### 5. **LLM Integration**

Supports multiple LLM providers:
- **Google Gemini** (default): `gemini-2.5-flash-preview-05-20`
- **OpenAI**: GPT models (configurable)

**Configuration:**
```yaml
model:
  provider: google
  name: gemini-2.5-flash-preview-05-20
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

## 🚀 Setup & Installation

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
./start.sh

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
docker run -p 8000:8000 -v chroma-data:/chroma/chroma chromadb/chroma:latest
```

**Option B: Using Python**
```bash
pip install chromadb
chroma run --path ./chroma-data
```

### 5. Load Your Wine Books

Place your PDF/text files in the configured directory and run:

```bash
python src/pour-decisions/load_data.py
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

## 📖 Usage

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

## ⚙️ Configuration

### `app_config.yml`

```yaml
chroma:
  client:
    host: localhost
    port: 8000
  
  chunking:
    strategy: by_title        # basic, by_title, semantic
    chunk_size: 1024
    chunk_overlap: 256
  
  retrieval:
    n_results: 5              # chunks per query
    similarity_threshold: 0.3  # minimum similarity (0.0-1.0)
    deduplication_threshold: 0.9
    use_deduplication: false
  
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
  provider: google          # google or openai
  name: gemini-2.5-flash-preview-05-20

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

## 📁 Project Structure

```
rag/
├── src/
│   ├── data/
│   │   ├── __init__.py
│   │   ├── chunks.py              # Chunking strategies
│   │   ├── load_data.py           # Data ingestion script
│   │   └── loader.py              # Collection data loader
│   │
│   ├── model/
│   │   ├── __init__.py
│   │   ├── llm.py                 # LLM initialization & invocation
│   │   ├── prompts.py             # System & user prompts
│   │   ├── rag_main.py            # RAG orchestration
│   │   └── retriever.py           # ChromaRetriever class
│   │
│   ├── ui/
│   │   ├── __init__.py
│   │   ├── app.py                 # Main Streamlit app
│   │   └── display.py             # UI components
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
│   └── rag-pipeline.md
│   
├── chroma-data/                   # ChromaDB storage
├── app_config.yml                 # App configuration
├── docker-compose.yml             # Docker setup
├── Makefile                       # ChromaDB management
├── pyproject.toml                 # Dependencies
└── README.md                      # This file
```

## 🛠️ Development

### Makefile Commands

```bash
# ChromaDB Management
make db-up          # Start ChromaDB
make db-down        # Stop ChromaDB
make db-restart     # Restart ChromaDB
make db-status      # Check status
make db-logs        # View logs
make db-clean       # Delete all ChromaDB data (destructive!)
make db-backup      # Create backup
make db-load        # Load pour-decisions into ChromaDB

# Testing
make test-connection  # Test ChromaDB connection
```

### Testing the RAG Pipeline

1. **Test with ChromaDB running:**
   ```bash
   make db-up
   streamlit run src/ui/app.py
   ```
   - Verify retrieval works
   - Check source citations appear
   - Confirm relevance scores are reasonable

2. **Test without ChromaDB (fallback):**
   ```bash
   make db-down
   streamlit run src/ui/app.py
   ```
   - Should show "❌ RAG System: Unavailable"
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
   make db-load
   ```

3. Update app.py to query multiple collections (if needed)

### Customizing Prompts

Edit `src/model/prompts.py` to customize:
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

## 🐛 Troubleshooting

### "ModuleNotFoundError: No module named 'src'"

**Solution:** Run from project root with correct PYTHONPATH:
```bash
PYTHONPATH=$(pwd) python3 src/pour-decisions/load_data.py
# or use
make db-load
```

### "Unable to connect to ChromaDB"

**Check:**
```bash
make db-status       # Is container running?
make db-logs         # Any errors in logs?
docker ps            # Is port 8000 exposed?
```

**Fix:**
```bash
make db-restart
```

### "No results found for query"

**Possible causes:**
- Knowledge base is empty → Run `make db-load`
- Similarity threshold too high → Lower it in config
- Question not related to wine books → Expected behavior

### App crashes or shows errors

**Check logs:**
- Streamlit terminal output
- `make db-logs` for ChromaDB
- Verify API keys are set correctly

## 📊 Performance Considerations

- **Embedding Model**: `all-MiniLM-L6-v2` is fast but lightweight. For better quality, consider `all-mpnet-base-v2`
- **Chunk Size**: Larger chunks (1024-2048) provide more context but may reduce precision
- **Number of Results**: More results (7-10) give better coverage but slower response time
- **Deduplication**: Adds processing time but improves context quality

## 🤝 Contributing

Contributions welcome! Areas for improvement:
- Support for more chunking strategies
- Additional LLM providers
- Multi-collection querying
- Advanced reranking algorithms
- Query expansion techniques

## 📝 License

[Your License Here]

## 🙏 Acknowledgments

- **LangChain** for RAG framework components
- **ChromaDB** for vector database
- **Streamlit** for the UI framework
- **Sentence Transformers** for embeddings
- **Google Gemini** for LLM capabilities

---

Built with ❤️ for wine enthusiasts 🍷


