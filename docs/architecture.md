# Harmonia Memory Storage System Architecture

## Overview

Harmonia is a local-first intelligent memory storage system designed for LLM chat applications. It provides persistent, context-aware memory capabilities while keeping all data completely local for privacy. The system uses a modern, layered architecture built with Python, FastAPI, SQLite, and Ollama.

## System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Client Applications                       │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐│
│  │   Python CLI    │  │   Web Client    │  │  Third-party    ││
│  │   Applications  │  │   (Future)      │  │   Tools         ││
│  └─────────────────┘  └─────────────────┘  └─────────────────┘│
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      HTTP API Layer                         │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐│
│  │   FastAPI       │  │   Middleware    │  │   Auth &        ││
│  │   Routers       │  │   Stack         │  │   Rate Limit    ││
│  └─────────────────┘  └─────────────────┘  └─────────────────┘│
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   Business Logic Layer                      │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐│
│  │   Memory        │  │   Processing    │  │   Search        ││
│  │   Manager       │  │   Pipeline      │  │   Engine        ││
│  └─────────────────┘  └─────────────────┘  └─────────────────┘│
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     Data Access Layer                       │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐│
│  │   Database      │  │   Connection    │  │   Data Models   ││
│  │   Manager       │  │   Pool          │  │   & ORM         ││
│  └─────────────────┘  └─────────────────┘  └─────────────────┘│
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    External Services                        │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐│
│  │   SQLite        │  │   Ollama LLM    │  │   File System   ││
│  │   Database      │  │   Service       │  │   Storage       ││
│  └─────────────────┘  └─────────────────┘  └─────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

### Component Interaction Flow

```
User Message Input
        │
        ▼
┌─────────────────┐
│   HTTP API      │ ◄─── Authentication & Rate Limiting
│   Endpoint      │
└─────────────────┘
        │
        ▼
┌─────────────────┐
│   Memory        │ ◄─── Validation & Business Logic
│   Manager       │
└─────────────────┘
        │
        ▼
┌─────────────────┐
│   Processing    │ ◄─── 9-Step Pipeline
│   Pipeline      │
└─────────────────┘
        │         │
        ▼         ▼
┌─────────────────┐  ┌─────────────────┐
│   Ollama LLM    │  │   Conflict      │
│   Extraction    │  │   Resolution    │
└─────────────────┘  └─────────────────┘
        │                     │
        ▼                     ▼
┌─────────────────────────────────┐
│       Database Storage          │
│   ┌─────────────────┐           │
│   │   Transaction   │           │
│   │   Management    │           │
│   └─────────────────┘           │
└─────────────────────────────────┘
        │
        ▼
┌─────────────────┐
│   Search Index  │ ◄─── FTS5 Full-Text Search
│   Update        │
└─────────────────┘
        │
        ▼
    Response
```

## Core Components

### 1. API Layer (`src/api/`)

**FastAPI Application** (`main.py`)
- Application lifecycle management with startup/shutdown handlers
- Dependency injection for core services
- Global exception handling and error formatting
- CORS configuration for cross-origin requests

**Routers** (`src/api/routers/`)
- `health.py`: Health check endpoints with component status
- `memory.py`: Memory management endpoints (CRUD + search)

**Middleware Stack** (`src/api/middleware/`)
- `LoggingMiddleware`: Request/response logging with timing
- `RateLimitMiddleware`: Token bucket rate limiting
- `AuthMiddleware`: API key authentication (optional)

**Request/Response Models** (`src/api/models/`)
- `requests.py`: Pydantic models for request validation
- `responses.py`: Standardized response formats

### 2. Business Logic Layer

**Memory Manager** (`src/processing/memory_manager.py`)
- Orchestrates the complete memory lifecycle
- Handles CRUD operations with validation
- Manages batch processing and transactions
- Implements user isolation and access control

**Processing Pipeline** (`src/processing/memory_processor.py`)
- 9-stage memory processing pipeline:
  1. **Preprocessing**: Text cleaning and normalization
  2. **Entity Extraction**: Named entity recognition
  3. **LLM Extraction**: Structured memory extraction
  4. **Confidence Scoring**: Multi-factor quality assessment
  5. **Temporal Resolution**: Relative to absolute time conversion
  6. **Conflict Detection**: Similarity-based conflict identification
  7. **Conflict Resolution**: Strategy-based conflict handling
  8. **Validation**: Data integrity and format validation
  9. **Storage**: Transactional database persistence

**Search Engine** (`src/search/search_engine.py`)
- BM25-based relevance ranking
- SQLite FTS5 integration with custom tokenization
- Advanced filtering (date, category, confidence)
- Export functionality in multiple formats

### 3. Data Access Layer

**Database Manager** (`src/db/manager.py`)
- Connection pooling with configurable pool size
- Transaction management with savepoint support
- Health monitoring and statistics collection
- Backup/restore functionality using SQLite APIs
- Retry logic for handling database locks

**Data Models** (`src/models/`)
- `base.py`: Base model with common functionality
- `user.py`: User account and settings management
- `memory.py`: Core memory storage with metadata
- `session.py`: Chat session tracking
- `category.py`: Memory categorization system

**Schema Management** (`src/db/schema.py`)
- Complete database schema definition
- FTS5 virtual table for full-text search
- Indexes for performance optimization
- Trigger definitions for automatic updates

### 4. LLM Integration Layer

**Ollama Client** (`src/llm/ollama_client.py`)
- Connection management with health monitoring
- Automatic retry logic with exponential backoff
- Model existence verification and pulling
- Performance statistics and error tracking
- Support for both generate and chat APIs

**Prompt System** (`src/prompts/`)
- `template_engine.py`: Handlebars-style template processing
- `memory_extraction.py`: Optimized prompts for 12 memory types
- `versioning.py`: Template version management
- `types.py`: Type definitions for prompt contexts

### 5. Configuration System

**Configuration Management** (`src/core/config.py`)
- YAML-based configuration with environment overrides
- Pydantic validation with helpful error messages
- Hot-reload capability for development
- Secrets management through environment variables

**Logging System** (`src/core/logging.py`)
- Structured logging with JSON formatting
- Multiple output destinations (console, file)
- Configurable log levels and rotation
- Request correlation for distributed tracing

## Database Architecture

### Schema Design

```sql
-- Core Tables
users                 -- User account management
├── user_id (PK)
├── username
├── settings (JSON)
├── created_at
└── updated_at

memories              -- Primary memory storage
├── memory_id (PK)
├── user_id (FK)
├── content
├── original_message
├── category
├── confidence_score
├── metadata (JSON)
├── is_active
├── created_at
└── updated_at

sessions              -- Chat session tracking  
├── session_id (PK)
├── user_id (FK)
├── metadata (JSON)
├── started_at
└── ended_at

categories            -- Memory categorization
├── category_id (PK)
├── name
├── description
└── parent_id (FK)

-- Full-Text Search
memories_fts         -- FTS5 virtual table
├── memory_id
├── content
├── original_message
└── category

-- Audit Trail
memory_updates       -- Change tracking
├── update_id (PK)
├── memory_id (FK)
├── previous_content
├── new_content
├── action
├── reason
└── updated_at
```

### Performance Optimizations

**Indexes**:
```sql
-- Performance indexes
CREATE INDEX idx_memories_user_id ON memories(user_id);
CREATE INDEX idx_memories_category ON memories(category);
CREATE INDEX idx_memories_created_at ON memories(created_at);
CREATE INDEX idx_memories_confidence ON memories(confidence_score);
CREATE INDEX idx_memories_active ON memories(is_active);

-- Composite indexes for common queries
CREATE INDEX idx_memories_user_category ON memories(user_id, category);
CREATE INDEX idx_memories_user_active ON memories(user_id, is_active);
```

**FTS5 Configuration**:
```sql
-- Full-text search with custom tokenizer
CREATE VIRTUAL TABLE memories_fts USING fts5(
    content,
    original_message,
    category,
    tokenize='porter ascii',
    content_rowid='memory_id'
);

-- Automatic FTS updates
CREATE TRIGGER memories_fts_insert AFTER INSERT ON memories
WHEN NEW.is_active = 1
BEGIN
    INSERT INTO memories_fts(rowid, content, original_message, category)
    VALUES (NEW.memory_id, NEW.content, NEW.original_message, NEW.category);
END;
```

### Connection Management

**Connection Pooling**:
- Pool size: 20 connections (configurable)
- Timeout: 30 seconds for connection acquisition
- WAL mode for better concurrency
- Thread-safe operations with proper locking

**Transaction Handling**:
```python
# Savepoint support for nested transactions
with db_manager.transaction() as tx:
    # Primary operation
    memory_id = tx.create_memory(memory_data)
    
    with tx.savepoint() as sp:
        # Secondary operation that might fail
        try:
            tx.update_search_index(memory_id)
        except Exception:
            sp.rollback()  # Only rollback savepoint
    
    # Transaction commits if no exceptions
```

## Memory Processing Pipeline

### Pipeline Architecture

```
Input Message
     │
     ▼
┌─────────────────┐
│ 1. Preprocessing │ ── Text cleaning, normalization
└─────────────────┘
     │
     ▼
┌─────────────────┐
│ 2. Entity       │ ── Named entity recognition
│    Extraction   │
└─────────────────┘
     │
     ▼
┌─────────────────┐
│ 3. LLM          │ ── Ollama-based memory extraction
│    Extraction   │    (12 memory types)
└─────────────────┘
     │
     ▼
┌─────────────────┐
│ 4. Confidence   │ ── Multi-factor scoring:
│    Scoring      │    - Content specificity
└─────────────────┘    - Entity presence
     │                 - Language clarity
     ▼
┌─────────────────┐
│ 5. Temporal     │ ── Convert relative times:
│    Resolution   │    "tomorrow" → 2025-08-24
└─────────────────┘
     │
     ▼
┌─────────────────┐
│ 6. Conflict     │ ── Similarity detection:
│    Detection    │    - Semantic similarity
└─────────────────┘    - Entity overlap
     │                 - Temporal proximity
     ▼
┌─────────────────┐
│ 7. Conflict     │ ── Resolution strategies:
│    Resolution   │    - UPDATE, MERGE, VERSION
└─────────────────┘    - LINK, CREATE_NEW, SKIP
     │
     ▼
┌─────────────────┐
│ 8. Validation   │ ── Data integrity checks
└─────────────────┘
     │
     ▼
┌─────────────────┐
│ 9. Storage      │ ── Transactional persistence
└─────────────────┘    + FTS index update
     │
     ▼
  Stored Memory
```

### Memory Types and Extraction

**Supported Memory Types**:
1. **Personal**: Biographical information, traits
2. **Factual**: Objective facts, data points  
3. **Emotional**: Feelings, moods, emotional states
4. **Relational**: Relationships, connections
5. **Temporal**: Time-bound information, schedules
6. **Procedural**: How-to information, processes
7. **Episodic**: Specific events, experiences
8. **Preference**: Likes, dislikes, opinions
9. **Goal**: Objectives, aspirations, plans
10. **Skill**: Abilities, competencies
11. **Meta**: Information about information
12. **Other**: Miscellaneous valuable content

**Extraction Process**:
```python
# LLM prompt structure
system_prompt = f"""
You are a memory extraction AI for the Harmonia Memory System.
Extract structured memories from user messages.

EXTRACTION GUIDELINES:
- Focus on personal, factual, emotional, and significant information
- Assign appropriate memory types from: {MEMORY_TYPES}
- Provide confidence scores (0.0-1.0) based on clarity and specificity
- Extract only explicitly stated or strongly implied information

OUTPUT FORMAT:
Return valid JSON with this structure:
{{
    "memories": [
        {{
            "content": "Extracted memory statement",
            "memory_type": "personal|factual|emotional|...",
            "confidence": 0.95,
            "entities": ["extracted", "entities"],
            "temporal_info": "2025-08-24T14:00:00Z",
            "reasoning": "Why this memory was extracted"
        }}
    ]
}}
"""

user_prompt = f"Message: {user_message}"
```

### Conflict Resolution

**Detection Algorithm**:
```python
def detect_conflicts(new_memory, existing_memories):
    conflicts = []
    
    for existing in existing_memories:
        similarity_score = calculate_similarity(
            new_memory.content, 
            existing.content
        )
        
        entity_overlap = calculate_entity_overlap(
            new_memory.entities,
            existing.entities
        )
        
        temporal_proximity = calculate_temporal_proximity(
            new_memory.timestamp,
            existing.timestamp
        )
        
        # Composite conflict score
        conflict_score = (
            similarity_score * 0.5 + 
            entity_overlap * 0.3 + 
            temporal_proximity * 0.2
        )
        
        if conflict_score > CONFLICT_THRESHOLD:
            conflicts.append({
                'existing': existing,
                'score': conflict_score
            })
    
    return conflicts
```

**Resolution Strategies**:
```python
class ConflictResolution:
    def update_strategy(self, new_memory, existing_memory):
        """Replace existing memory with new one."""
        return self.db.update_memory(
            existing_memory.id, 
            new_memory.content,
            metadata={'previous_content': existing_memory.content}
        )
    
    def merge_strategy(self, new_memory, existing_memory):
        """Combine information from both memories."""
        merged_content = self.llm.merge_memories(
            existing_memory.content,
            new_memory.content
        )
        return self.db.update_memory(
            existing_memory.id,
            merged_content,
            metadata={'merge_source': new_memory.content}
        )
    
    def version_strategy(self, new_memory, existing_memory):
        """Keep both as separate versions."""
        # Update existing to add version metadata
        self.db.update_memory(
            existing_memory.id,
            existing_memory.content,
            metadata={'version': 1}
        )
        
        # Store new as version 2
        return self.db.create_memory(
            new_memory.content,
            metadata={'version': 2, 'parent': existing_memory.id}
        )
```

## Security Architecture

### Authentication System

**API Key Authentication** (Optional):
```python
class AuthMiddleware:
    def __init__(self, app, api_keys: List[str]):
        self.app = app
        self.api_keys = set(api_keys)
    
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            # Extract Authorization header
            headers = dict(scope.get("headers", []))
            auth_header = headers.get(b"authorization", b"").decode()
            
            if auth_header.startswith("Bearer "):
                token = auth_header[7:]
                if token in self.api_keys:
                    # Valid token, continue
                    return await self.app(scope, receive, send)
            
            # Invalid or missing token
            response = JSONResponse(
                status_code=401,
                content={"error": "authentication_required"}
            )
            return await response(scope, receive, send)
```

**User Isolation**:
- All data operations require user_id parameter
- Database-level filtering ensures data isolation
- No cross-user data access possible through API

### Rate Limiting

**Token Bucket Algorithm**:
```python
class RateLimiter:
    def __init__(self, requests_per_minute: int):
        self.capacity = requests_per_minute
        self.tokens = requests_per_minute
        self.last_refill = time.time()
    
    def allow_request(self) -> bool:
        now = time.time()
        
        # Refill tokens based on time elapsed
        time_passed = now - self.last_refill
        tokens_to_add = time_passed * (self.capacity / 60.0)
        
        self.tokens = min(self.capacity, self.tokens + tokens_to_add)
        self.last_refill = now
        
        if self.tokens >= 1:
            self.tokens -= 1
            return True
        
        return False
```

### Input Validation

**Request Validation**:
```python
class MemoryStoreRequest(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=100)
    message: str = Field(..., min_length=1, max_length=10000)
    session_id: Optional[str] = Field(None, max_length=100)
    metadata: Optional[Dict[str, Any]] = Field(None)
    resolution_strategy: str = Field("auto", regex="^(auto|update|merge|version|skip)$")
    
    @validator('message')
    def validate_message_content(cls, v):
        # Remove excessive whitespace
        cleaned = ' '.join(v.split())
        if len(cleaned) < 1:
            raise ValueError('Message cannot be empty after cleaning')
        return cleaned
```

**SQL Injection Prevention**:
- All database operations use parameterized queries
- SQLite connection with strict parameter binding
- No dynamic SQL construction from user input

## Performance Architecture

### Caching Strategy

**Multi-Level Caching**:
```python
class CacheManager:
    def __init__(self):
        # L1: In-memory LRU cache
        self.memory_cache = LRUCache(maxsize=1000)
        
        # L2: Search result cache
        self.search_cache = TTLCache(maxsize=500, ttl=300)  # 5 minutes
        
        # L3: User context cache
        self.user_cache = TTLCache(maxsize=100, ttl=3600)   # 1 hour
    
    def get_memory(self, memory_id: str):
        # Check L1 cache first
        if memory_id in self.memory_cache:
            return self.memory_cache[memory_id]
        
        # Fetch from database
        memory = self.db.get_memory(memory_id)
        
        # Store in L1 cache
        self.memory_cache[memory_id] = memory
        return memory
```

### Database Optimization

**Query Optimization**:
```sql
-- Optimized search query with proper indexing
SELECT m.*, rank 
FROM memories m
JOIN (
    SELECT rowid, rank 
    FROM memories_fts
    WHERE memories_fts MATCH ?
    ORDER BY rank
    LIMIT ? OFFSET ?
) fts ON m.memory_id = fts.rowid
WHERE m.user_id = ? 
  AND m.is_active = 1
  AND (? IS NULL OR m.category = ?)
  AND (? IS NULL OR m.confidence_score >= ?)
  AND (? IS NULL OR m.created_at >= ?)
ORDER BY fts.rank;
```

**Connection Pool Tuning**:
```python
# Production configuration
DATABASE_CONFIG = {
    'pool_size': 20,           # Max connections
    'timeout': 30,             # Connection timeout
    'retry_attempts': 10,      # DB lock retries
    'wal_mode': True,          # Enable WAL for concurrency
    'cache_size': 10000,       # Page cache size
    'mmap_size': 268435456,    # 256MB memory mapping
}
```

### Memory Management

**Resource Cleanup**:
```python
class ResourceManager:
    def __init__(self):
        self.active_connections = weakref.WeakSet()
        self.active_sessions = weakref.WeakKeyDictionary()
    
    def cleanup_expired_sessions(self):
        """Clean up expired LLM sessions."""
        current_time = time.time()
        expired = []
        
        for session, last_used in self.active_sessions.items():
            if current_time - last_used > SESSION_TIMEOUT:
                expired.append(session)
        
        for session in expired:
            session.close()
            del self.active_sessions[session]
```

## Monitoring and Observability

### Health Monitoring

**Component Health Checks**:
```python
class HealthMonitor:
    async def check_database(self) -> HealthStatus:
        try:
            start_time = time.time()
            result = await self.db.execute("SELECT 1")
            response_time = time.time() - start_time
            
            return HealthStatus(
                status="healthy",
                response_time_ms=response_time * 1000,
                details={
                    "connection_pool_size": self.db.pool_size,
                    "active_connections": self.db.active_connections,
                    "last_check": datetime.utcnow().isoformat()
                }
            )
        except Exception as e:
            return HealthStatus(
                status="unhealthy", 
                error=str(e)
            )
```

### Metrics Collection

**Performance Metrics**:
- Request duration histograms
- Database query performance
- LLM processing times
- Error rates by endpoint
- Cache hit/miss ratios
- Memory extraction success rates

```python
class MetricsCollector:
    def record_request_duration(self, endpoint: str, duration: float):
        self.histogram.observe(duration, labels={'endpoint': endpoint})
    
    def record_memory_extraction(self, success: bool, confidence: float):
        self.extraction_counter.inc(labels={'success': success})
        if success:
            self.confidence_histogram.observe(confidence)
```

### Logging Architecture

**Structured Logging**:
```python
{
    "timestamp": "2025-08-23T12:30:45.123456Z",
    "level": "INFO",
    "logger": "harmonia.api",
    "message": "Memory stored successfully",
    "request_id": "req_abc123",
    "user_id": "alice", 
    "memory_id": "mem_def456",
    "processing_time_ms": 67,
    "confidence": 0.95,
    "context": {
        "endpoint": "/api/v1/memory/store",
        "method": "POST",
        "ip_address": "127.0.0.1"
    }
}
```

## Deployment Architecture

### Local Deployment

**Single Instance Setup**:
```
┌─────────────────────────────────────┐
│            Local Machine             │
│  ┌─────────────┐  ┌─────────────────┐│
│  │   Harmonia  │  │     Ollama      ││
│  │   Server    │◄─┤   LLM Service   ││
│  │             │  │                 ││
│  └─────────────┘  └─────────────────┘│
│         │                           │
│         ▼                           │
│  ┌─────────────────┐                │
│  │ SQLite Database │                │
│  │ + FTS5 Index    │                │
│  └─────────────────┘                │
└─────────────────────────────────────┘
```

### Production Deployment Considerations

**Scaling Strategy**:
- Multiple Harmonia instances with shared SQLite database
- Read replicas for improved read performance
- Load balancing for API endpoints
- Dedicated Ollama instances for LLM processing

**High Availability**:
- SQLite backup and restore procedures
- Health check endpoints for monitoring
- Graceful shutdown handling
- Container orchestration support

This architecture provides a robust, scalable foundation for intelligent memory storage while maintaining the system's core principles of local-first operation and privacy preservation.