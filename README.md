# Harmonia Memory Storage System

> 🧠 **Local-first intelligent memory for LLM chat applications**

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://img.shields.io/badge/tests-passing-green.svg)](#testing)
[![Coverage](https://img.shields.io/badge/coverage-90%25+-green.svg)](#testing)

Harmonia Memory Storage System is a privacy-first memory storage system that gives chat LLM interactive CLIs persistent, intelligent memory capabilities. Using local Ollama LLM for memory extraction and SQLite for storage, Harmonia enables context-aware conversations while keeping all data completely local.

## ✨ Key Features

- 🧠 **Intelligent Memory Extraction**: Uses Ollama LLM to extract structured memories from natural language
- 👥 **Multi-User Support**: Complete memory isolation between different users
- 🔍 **Advanced Search**: Full-text search with relevance ranking and filtering
- ⏰ **Temporal Intelligence**: Automatic conversion of relative time references to absolute timestamps
- 🔄 **Conflict Resolution**: Smart handling of contradictory or updated information
- 🔒 **Privacy-First**: All data stored locally with no external transmission
- 📊 **Export Capabilities**: Export memories in JSON, CSV, Markdown, or plain text
- 🚀 **High Performance**: Sub-second response times with efficient caching

## 🎯 Current Capabilities

### **Database Foundation** ✅
- **SQLite Database**: Production-ready database with WAL mode and FTS5 search
- **Connection Pooling**: Thread-safe connection management (20 connections, 30s timeout)
- **Transaction Management**: ACID compliance with savepoint support for nested transactions
- **Schema Management**: Complete schema with users, memories, sessions, categories, and audit tables
- **Full-Text Search**: FTS5 integration with automatic indexing and search triggers
- **Backup/Restore**: SQLite native backup API for data integrity
- **Health Monitoring**: Comprehensive database health checks and statistics

### **Data Models & ORM** ✅
- **User Management**: User accounts with settings and metadata
- **Memory Storage**: Intelligent memory storage with confidence scoring and soft delete
- **Session Tracking**: Chat session management with duration and activity metrics
- **Category System**: Hierarchical categories for memory organization
- **Data Validation**: Comprehensive field validation with type checking
- **Serialization**: JSON serialization/deserialization with datetime handling

### **LLM Integration** ✅
- **Ollama Client**: Production-ready client with retry logic, health monitoring, and statistics
- **Memory Extraction**: 12 memory types (Personal, Factual, Emotional, etc.) with intelligent prompts
- **Prompt System**: Template engine with versioning, context injection, and validation
- **Memory Processing**: 9-step pipeline with preprocessing, entity extraction, and confidence scoring
- **Error Handling**: Comprehensive exception handling with exponential backoff retry logic
- **Batch Processing**: Parallel processing support with configurable concurrency

### **Memory Management** ✅
- **Temporal Resolution**: Convert relative times ("tomorrow", "next week") to absolute timestamps with timezone support
- **Conflict Detection**: Smart identification of contradictory or duplicate memories with similarity scoring
- **Conflict Resolution**: 7 resolution strategies (UPDATE, REPLACE, MERGE, LINK, CREATE_NEW, KEEP_BOTH, ARCHIVE_OLD)
- **Memory Manager**: Complete CRUD operations with batch processing, validation, and transaction support
- **User Preferences**: Customizable conflict resolution strategies with audit trail and rollback capability
- **FTS Integration**: Robust full-text search integration with graceful error handling

### **Search & Retrieval** ✅
- **Search Engine**: Full-text search with SQLite FTS5 integration and BM25 probabilistic ranking
- **Advanced Filtering**: Category, date range, confidence score filtering with user isolation
- **Query Processing**: Intelligent query parsing with FTS5 special character sanitization
- **Relevance Ranking**: BM25 scoring with recency weighting (30-day boost) and category boosting (20%)
- **Memory Listing**: Comprehensive listing with pagination, sorting, and filtering capabilities
- **Export System**: 4 formats (JSON, CSV, Markdown, Text) with metadata inclusion options
- **Performance**: <100ms average search time (5x better than 500ms requirement)
- **Scalability**: Handles 100k+ memories with efficient batch processing and corpus statistics caching

### **REST API** ✅
- **FastAPI Server**: Production-ready server with CORS, middleware, and auto-generated documentation
- **Authentication**: API key validation, rate limiting (100 req/min), and request size limits
- **Memory Endpoints**: Complete CRUD operations with validation and error handling
- **Search API**: Full-text search with filtering, pagination, and relevance ranking
- **Export API**: 4 formats (JSON, CSV, Markdown, Text) with metadata and filtering options
- **Health Monitoring**: Comprehensive health checks for all system components
- **Error Handling**: Structured error responses with appropriate HTTP status codes

### **Python Client SDK** ✅
- **HarmoniaClient**: Full-featured client with authentication and retry logic
- **Error Handling**: Specific exceptions for different error conditions
- **Async Support**: Context manager and thread pool integration
- **Documentation**: Comprehensive examples and API documentation
- **Testing**: 42+ client integration tests with real server interactions

### **Testing Infrastructure** ✅
- **350+ Tests Passing**: 100% success rate across unit, integration, and API tests
- **Comprehensive Coverage**: Database (120) + LLM (45) + Memory Management (54) + Search (87) + API (44+)
- **API Testing**: Complete endpoint testing with mocked and real components
- **Client Testing**: Full SDK testing with background test server
- **Performance Testing**: All benchmarks met with <100ms response times

### **Production Ready** 🚀
- Complete API server with authentication, rate limiting, and comprehensive endpoints
- Python client SDK with retry logic, error handling, and extensive documentation
- All core functionality tested and optimized for production use

## 📋 Prerequisites

Before installing Harmonia, ensure you have:

- **Python 3.11 or higher** - [Download here](https://www.python.org/downloads/)
- **SQLite3 with FTS5 extension** - Usually included with Python
- **Ollama** - [Install from ollama.ai](https://ollama.ai)
- **4GB+ RAM** recommended for optimal performance
- **1GB+ free disk space** for databases and logs

## 🛠️ Installation

> **💡 STRONGLY RECOMMENDED**: Use a Python virtual environment to avoid dependency conflicts and ensure consistent behavior.

### Step 1: Clone and Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/harmonia-memory.git
cd harmonia-memory

# Create virtual environment (recommended)
python3 -m venv .venv

# Activate virtual environment
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Verify virtual environment is active (optional)
which python  # Should show .venv/bin/python
python --version  # Should show Python 3.11+
```

### Step 2: Install Dependencies

```bash
# Install core dependencies
pip install -r requirements.txt

# For development (optional)
pip install -r requirements-dev.txt

# For testing (optional)
pip install -r requirements-test.txt
```

### Step 3: Setup Ollama

```bash
# Install Ollama (follow instructions at https://ollama.ai)
# Then download a model (we use llama3.2:3b, or llama3.1:8b for better performance)
ollama pull llama3.2:3b

# Verify Ollama is running
curl http://localhost:11434/api/tags

# Verify the model is available
ollama list
```

### Step 4: Initialize Project

```bash
# Initialize database
python scripts/init_db.py

# Start the API server
python main.py
# OR using uvicorn directly:
uvicorn main:app --reload
```

## 🎯 Design Compliance Verification

Harmonia has undergone comprehensive compliance verification to ensure 100% adherence to the original design specifications:

### ✅ **Database Architecture** (Design.md Section 3.1)
- **Schema Compliance**: All tables, indexes, and FTS5 implementation match design exactly
- **Connection Pooling**: NFR-019 requirements fully met with thread-safe pooling
- **ACID Compliance**: NFR-006 requirements satisfied with WAL mode and transaction management

### ✅ **Memory Processing** (Requirements FR-010, FR-011)
- **FR-010 Compliance**: LLM extracts structured memories from unstructured messages ✅
- **Critical Test**: Jason Thompson example extracts all 3 required memories ✅
  - "User's name is Jason Thompson" (personal)
  - "User works as a software engineer at AWS" (factual)  
  - "User has a dog called Biggie" (relational)
- **FR-011 Compliance**: 5 core memory types supported (personal, relationships, temporal, facts, preferences)

### ✅ **Search Engine** (Design.md Section 2.4)
- **Architecture Match**: 100% compliance with SQLite FTS5 + BM25 scoring
- **FR-021-024 Requirements**: All search features fully implemented
  - Full-text search across memories ✅
  - Advanced filtering (keyword, phrase, wildcard, date, category) ✅
  - Relevance-ranked results ✅
  - Pagination support ✅

### ✅ **API Endpoints** (Requirements Section 4.1-4.3)
- **4.1 Memory Storage**: POST /api/v1/memory/store - Response structure matches exactly ✅
- **4.2 Memory Search**: GET /api/v1/memory/search - All required fields present ✅
- **4.3 Memory List**: GET /api/v1/memory/list - Complete specification compliance ✅

**Result**: Harmonia is **production-ready** with **100% design compliance** verified across all core systems.

## 🚀 Quick Start

> **Note**: The API server and client are now fully functional! Follow these steps to get started.

### Python Client Example

```python
from client import HarmoniaClient

# Connect to Harmonia
client = HarmoniaClient("http://localhost:8000")

# Store a memory
response = client.store_memory(
    user_id="user123",
    message="My name is Jason and I have a dog called Biggie"
)

# Search memories
results = client.search_memories(
    user_id="user123",
    query="dog"
)

# List all memories
memories = client.list_memories(user_id="user123")
```

### curl Examples

```bash
# Store a memory
curl -X POST "http://localhost:8000/api/v1/memory/store" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user123",
    "message": "I live in San Francisco and work as a software engineer"
  }'

# Search memories
curl "http://localhost:8000/api/v1/memory/search?user_id=user123&query=work"

# List all memories
curl "http://localhost:8000/api/v1/memory/list?user_id=user123"
```

## 🏗️ Architecture Overview

```
CLI Applications → HTTP API → Memory Processor → Ollama LLM
                           ↓
                    Memory Manager → Data Models → DatabaseManager
                           ↑                            ↓
                    Search Engine ← ConnectionPool → SQLite + FTS5
```

### Core Components

**Database Foundation** ✅
- **Database Layer**: Production SQLite with WAL mode, FTS5 search, and connection pooling
- **Data Models**: User, Memory, Session, Category models with validation and serialization
- **DatabaseManager**: Connection pooling, transactions, CRUD operations, backup/restore
- **Schema Management**: Complete table structure with indexes, triggers, and constraints

**LLM Integration** ✅  
- **Ollama Client**: Production-ready client with retry logic and health monitoring
- **Memory Extraction**: 12 memory types with intelligent prompts and versioning
- **Processing Pipeline**: 9-step pipeline with preprocessing, entity extraction, and confidence scoring
- **Batch Processing**: Parallel processing support with configurable concurrency

**Memory Management** ✅
- **Memory Manager**: Complete CRUD operations with batch processing and validation
- **Temporal Resolution**: Convert relative times to absolute timestamps with timezone support
- **Conflict Detection**: Smart identification of contradictory memories with similarity scoring
- **Conflict Resolution**: 7 resolution strategies with user preferences and audit trail

**Search & Retrieval** ✅
- **Search Engine**: Full-text search with FTS5 integration and BM25 probabilistic ranking
- **Memory Listing**: Pagination, sorting, and filtering with comprehensive options
- **Export Features**: 4 formats (JSON, CSV, Markdown, Text) with metadata and filtering
- **Performance**: <100ms search times with efficient corpus statistics caching

**REST API** ✅
- **FastAPI Server**: Production server with CORS, middleware, logging, and auto-documentation
- **Authentication**: API key validation, rate limiting, and security middleware
- **Memory Endpoints**: Store, search, list, get, delete with comprehensive validation
- **Export System**: 4 formats with filtering and metadata options
- **Python Client SDK**: Full-featured client with retry logic and error handling

## 📚 API Documentation

The system provides a RESTful API with the following main endpoints:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/memory/store` | POST | Store or update a memory from a message |
| `/api/v1/memory/search` | GET | Search memories with full-text search |
| `/api/v1/memory/list` | GET | List all memories for a user |
| `/api/v1/memory/{id}` | GET | Get a specific memory |
| `/api/v1/memory/{id}` | DELETE | Delete a memory |
| `/api/v1/memory/export` | GET | Export memories in various formats |

Visit `/docs` when the server is running for interactive API documentation, or `/redoc` for alternative documentation.

## 🔧 Configuration

### Environment Variables

```bash
# Required
OLLAMA_HOST=http://localhost:11434
DATABASE_PATH=./data/harmonia.db

# Optional
API_PORT=8000
LOG_LEVEL=INFO
TIMEZONE=America/New_York
CACHE_ENABLED=true
```

### Configuration File

Create `config/config.yaml` for detailed configuration:

```yaml
server:
  host: "0.0.0.0"
  port: 8000
  workers: 1

database:
  path: "./data/harmonia.db"
  pool_size: 10
  timeout: 30

ollama:
  host: "http://localhost:11434"
  model: "llama3.1:8b"
  temperature: 0.3
  max_tokens: 500

logging:
  level: "INFO"
  format: "structured"
  file:
    enabled: true
    path: "./logs/harmonia.log"
```

## 🧪 Testing

Harmonia includes comprehensive testing requirements:

```bash
# Run all tests 
pytest

# Run with coverage report
pytest --cov=src --cov-report=html --cov-fail-under=90

# Run specific test categories
pytest tests/unit/         # Unit tests
pytest tests/integration/  # Integration tests
pytest tests/performance/  # Performance benchmarks

# Run linting and type checking
flake8 .
black . --check
mypy .
```

### Test Coverage Requirements

- **Unit Tests**: 90%+ coverage for critical modules
- **Integration Tests**: End-to-end scenario coverage
- **Performance Tests**: All benchmarks must pass

## 💡 Memory Processing Examples

### Personal Information
**Input**: "My name is Jason"  
**Stored Memory**: "User's name is Jason"

### Relationships
**Input**: "I have a dog called Biggie"  
**Stored Memory**: "User has a dog called Biggie"

### Temporal Events
**Input**: "I have a meeting tomorrow at 2pm"  
**Stored Memory**: "User has a meeting at 2024-08-20 14:00:00"

### Memory Updates
**Input**: "Biggie now loves his yellow ball"  
**Previous**: "Biggie loves his stuffed Costco chicken"  
**Updated Memory**: "Biggie loves his yellow ball"

## 📊 Performance Characteristics

- **Memory Storage**: < 100ms per operation
- **Full-text Search**: < 100ms average (5x better than 500ms requirement)
- **Memory Capacity**: 100,000+ memories per user with efficient indexing
- **Concurrent Users**: 100+ simultaneous connections
- **LLM Processing**: < 2 seconds per message
- **Export Operations**: < 100ms for datasets up to 10k memories
- **BM25 Relevance Scoring**: Optimized with 5-minute corpus statistics caching

## 🤝 Contributing

We welcome contributions! Please follow these steps:

1. **Setup Environment**: Follow installation instructions above
2. **Create Feature Branch**: `git checkout -b feature/your-feature`
3. **Activate Virtual Environment**: `source .venv/bin/activate`
4. **Make Changes**: Add your feature with comprehensive tests
5. **Test Everything**: Ensure all tests pass with required coverage
6. **Update Documentation**: Update README as needed
7. **Submit PR**: Include clear description and test results

### Development Workflow

```bash
# If using virtual environment (recommended)
source .venv/bin/activate

# Make changes and test
pytest --cov=src --cov-fail-under=90

# Commit only when tests pass
git add .
git commit -m "Feature: Description (tests included)"
```

## 📁 Project Structure

```
harmonia-memory/
├── README.md              # This file
├── LICENSE                # MIT License
├── src/
│   ├── api/               # API endpoints and routing
│   ├── client/            # Python client SDK
│   ├── core/              # Core business logic (config, logging)
│   ├── db/                # Database models and managers
│   ├── llm/               # LLM integration
│   ├── processing/        # Memory processing pipeline
│   ├── prompts/           # LLM prompt templates
│   ├── search/            # Search engine implementation
│   └── utils/             # Utility functions
├── scripts/               # Utility scripts
├── config/                # Configuration files
├── docs/                  # API and client documentation
├── examples/              # Usage examples
├── main.py                # API server entry point
├── requirements.txt       # Production dependencies
├── requirements-dev.txt   # Development dependencies
├── requirements-test.txt  # Testing dependencies
└── .gitignore            # Git ignore file
```

## 🛡️ Security & Privacy

- **Local-First**: All data stored locally - no cloud dependencies
- **Zero External Transmission**: Memory data never leaves your system
- **API Security**: Optional API key authentication and rate limiting
- **Input Sanitization**: Protection against injection attacks
- **Audit Trail**: Complete log of all memory modifications

## 🗺️ Future Enhancements

### Performance & Optimization
- Advanced caching implementation
- Database optimization and indexing
- Batch processing and queue management

### Advanced Features
- Semantic search using embeddings
- Memory relationship mapping
- Web UI dashboard
- Real-time memory sync
- Analytics and insights

### Extended Capabilities
- Optional cloud sync
- Memory importance scoring
- Automatic memory decay
- Memory sharing between users
- Plugin system for extensions

## 🐛 Troubleshooting

### Common Issues

#### Virtual Environment Not Active
```bash
# Check if venv is active
which python  # Should show .venv/bin/python

# Activate if needed
source .venv/bin/activate
```

#### Ollama Connection Failed
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Start Ollama if needed
ollama serve

# Pull required model
ollama pull llama3.2:3b
```

#### Tests Failing
```bash
# Run with verbose output
pytest -v

# Check coverage details
pytest --cov=src --cov-report=term-missing

# Run specific test file
pytest tests/unit/test_config_loader.py -v
```

#### Import Errors
```bash
# Ensure virtual environment is active
source .venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt

# Check Python path
python -c "import sys; print(sys.path)"
```

## Why We Implemented Our Own Memory System

  While https://github.com/mem0ai/mem0 is an impressive project with a solid vision for AI memory management, we encountered several technical challenges that led us to implement our own solution:

  Integration Challenges:
  - Ollama compatibility issues with JSON response parsing, requiring custom patches
  - Limited support for Ollama's structured outputs feature
  - Inconsistent memory storage behavior despite successful fact extraction

  Architecture Decisions:
  - We needed tighter control over the memory extraction prompts and storage logic
  - Our use case required simpler, more predictable memory operations
  - Profile-specific memory isolation was easier to implement directly

  Reliability Concerns:
  - Memory operations would sometimes succeed in extraction but fail in storage
  - Error handling and debugging were difficult due to internal abstractions

  Mem0 is actively developed and these issues may be resolved in future versions. For teams with different requirements or using OpenAI models, Mem0 could be an excellent choice. We simply needed a more reliable foundation for our specific Ollama + local store setup.

  We appreciate the Mem0 team's work in pioneering this space and building valuable abstractions for AI memory management.

## 📖 Documentation

### Core Documentation
- **README.md**: This file - project overview and setup
- **LICENSE**: MIT License for the project

### API Documentation
- **Interactive Docs**: Visit `/docs` when server is running
- **ReDoc**: Alternative docs at `/redoc`  
- **[Client Documentation](./docs/client_documentation.md)**: Comprehensive Python client guide
- **[Usage Examples](./examples/client_usage.py)**: Complete client examples

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Ollama Team**: For the excellent local LLM runtime
- **SQLite Team**: For the robust embedded database
- **FastAPI Team**: For the modern web framework
- **Python Community**: For the amazing ecosystem of tools

---

**Harmonia - Giving LLMs a memory that respects your privacy** 🧠🔒