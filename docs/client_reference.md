# Harmonia Python Client Reference

## Overview

The Harmonia Python client provides a comprehensive, production-ready interface for interacting with the Harmonia Memory Storage API. It includes automatic retry logic, proper error handling, type hints, and support for all API endpoints.

## Installation

The client is included with the Harmonia system. For standalone use:

```python
import sys
sys.path.append('path/to/harmonia/src')
from client import HarmoniaClient
```

## Quick Start

```python
from client import HarmoniaClient

# Basic usage
client = HarmoniaClient("http://localhost:8000")

# Store a memory
response = client.store_memory(
    user_id="user123",
    message="I have a cat named Whiskers"
)

if response.success:
    print(f"Memory stored: {response.data['memory_id']}")

# Search memories
results = client.search_memories(
    user_id="user123", 
    query="cat"
)

for memory in results.data['results']:
    print(memory['content'])
```

## Client Configuration

### Constructor Parameters

```python
HarmoniaClient(
    base_url: str = "http://localhost:8000",
    api_key: Optional[str] = None,
    timeout: int = 30,
    max_retries: int = 3,
    retry_delay: float = 1.0,
    verify_ssl: bool = True,
    user_agent: Optional[str] = None
)
```

**Parameters**:
- `base_url`: Base URL of the Harmonia API server
- `api_key`: Optional API key for authentication
- `timeout`: Request timeout in seconds
- `max_retries`: Maximum retry attempts for failed requests
- `retry_delay`: Base delay between retries (exponential backoff)
- `verify_ssl`: Whether to verify SSL certificates  
- `user_agent`: Custom user agent string

### Advanced Configuration

```python
from client import HarmoniaClient

client = HarmoniaClient(
    base_url="https://api.harmonia.example.com",
    api_key="your-secure-api-key",
    timeout=60,           # 60 second timeout
    max_retries=5,        # Retry up to 5 times
    retry_delay=2.0,      # 2 second base delay
    verify_ssl=True,
    user_agent="MyApp/1.0"
)
```

## API Methods

### Health Check

Check API server health and get system status.

```python
def health_check(self) -> HarmoniaResponse
```

**Example**:
```python
response = client.health_check()

if response.success:
    status = response.data['status']
    components = response.data['components']
    print(f"API Status: {status}")
    print(f"Database: {components['database']['status']}")
    print(f"Search Engine: {components['search_engine']['status']}")
```

### Memory Storage

Store new memories from natural language messages.

```python
def store_memory(
    self,
    user_id: str,
    message: str,
    session_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    resolution_strategy: str = "auto"
) -> HarmoniaResponse
```

**Parameters**:
- `user_id`: Unique identifier for the user
- `message`: Natural language message to extract memories from
- `session_id`: Optional session identifier for context
- `metadata`: Additional metadata to store
- `resolution_strategy`: Conflict resolution strategy (`auto`, `update`, `merge`, `version`, `skip`)

**Examples**:

```python
# Basic memory storage
response = client.store_memory(
    user_id="alice",
    message="I work as a software engineer at TechCorp"
)

# With session context
response = client.store_memory(
    user_id="alice",
    message="The meeting went well today",
    session_id="daily_standup_2025_08_23"
)

# With metadata and conflict resolution
response = client.store_memory(
    user_id="alice", 
    message="I now work at NewCorp as a senior engineer",
    metadata={"source": "linkedin_update", "confidence": 0.9},
    resolution_strategy="update"
)

# Process response
if response.success:
    memory_id = response.data['memory_id']
    extracted = response.data['extracted_memory'] 
    action = response.data['action']  # 'created', 'updated', 'merged'
    confidence = response.data['confidence']
    
    print(f"Action: {action}")
    print(f"Extracted: {extracted}")
    print(f"Confidence: {confidence}")
```

### Memory Search

Search memories using full-text search with filtering.

```python
def search_memories(
    self,
    user_id: str,
    query: str,
    limit: int = 10,
    offset: int = 0,
    category: Optional[str] = None,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    min_confidence: Optional[float] = None,
    max_confidence: Optional[float] = None,
    sort_by: str = "relevance",
    sort_order: str = "desc",
    include_metadata: bool = False
) -> HarmoniaResponse
```

**Examples**:

```python
from datetime import datetime, timedelta

# Basic search
response = client.search_memories("alice", "software engineer")

# Advanced search with filters
response = client.search_memories(
    user_id="alice",
    query="meeting project",
    limit=20,
    category="work", 
    min_confidence=0.7,
    sort_by="created_at",
    sort_order="desc"
)

# Date range search
last_week = datetime.now() - timedelta(days=7)
response = client.search_memories(
    user_id="alice",
    query="*",  # Match all
    from_date=last_week,
    to_date=datetime.now(),
    include_metadata=True
)

# Process results
if response.success:
    results = response.data['results']
    total = response.data['pagination']['total_count']
    
    print(f"Found {total} memories:")
    for result in results:
        content = result['content']
        score = result['relevance_score']
        highlights = result.get('highlights', [])
        
        print(f"Score: {score:.2f} - {content}")
        if highlights:
            print(f"Highlights: {highlights}")
```

### Memory Listing

List memories with optional filtering and pagination.

```python
def list_memories(
    self,
    user_id: str,
    limit: int = 50,
    offset: int = 0,
    category: Optional[str] = None,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    min_confidence: Optional[float] = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    include_inactive: bool = False
) -> HarmoniaResponse
```

**Examples**:

```python
# List all memories
response = client.list_memories("alice")

# List with pagination
response = client.list_memories(
    user_id="alice",
    limit=25,
    offset=50,  # Get page 3
    sort_by="updated_at"
)

# Filter by category and confidence
response = client.list_memories(
    user_id="alice",
    category="personal",
    min_confidence=0.8,
    sort_by="confidence",
    sort_order="desc"
)

# Process memories
if response.success:
    memories = response.data['memories']
    pagination = response.data['pagination']
    
    print(f"Page {pagination['offset']//pagination['limit'] + 1}")
    print(f"Showing {len(memories)} of {pagination['total_count']} memories")
    
    for memory in memories:
        print(f"ID: {memory['memory_id']}")
        print(f"Content: {memory['content']}")
        print(f"Created: {memory['created_at']}")
        print(f"Confidence: {memory['confidence_score']}")
```

### Get Memory by ID

Retrieve a specific memory by its identifier.

```python  
def get_memory(self, memory_id: str) -> HarmoniaResponse
```

**Example**:
```python
response = client.get_memory("mem_abc123def456")

if response.success:
    memory = response.data['memory']
    history = response.data.get('update_history', [])
    
    print(f"Content: {memory['content']}")
    print(f"Category: {memory['category']}")
    print(f"Confidence: {memory['confidence_score']}")
    
    if history:
        print(f"Updates: {len(history)}")
        for update in history:
            print(f"  - {update['updated_at']}: {update['action']}")
```

### Delete Memory

Delete a specific memory (soft delete).

```python
def delete_memory(self, memory_id: str) -> HarmoniaResponse  
```

**Example**:
```python
response = client.delete_memory("mem_abc123def456")

if response.success:
    print(f"Deleted: {response.data['message']}")
else:
    print(f"Failed to delete: {response.error}")
```

### Export Memories

Export memories in various formats with filtering.

```python
def export_memories(
    self,
    user_id: str,
    format: str = "json",
    include_metadata: bool = False,
    category: Optional[str] = None,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    min_confidence: Optional[float] = None,
    max_memories: Optional[int] = None
) -> HarmoniaResponse
```

**Parameters**:
- `format`: Export format (`json`, `csv`, `markdown`, `text`)
- `include_metadata`: Include memory metadata in export
- `category`: Filter by category
- `from_date`: Date range start
- `to_date`: Date range end  
- `min_confidence`: Minimum confidence score
- `max_memories`: Maximum memories to export

**Examples**:

```python
import json

# Export all memories as JSON
response = client.export_memories(
    user_id="alice",
    format="json",
    include_metadata=True
)

if response.success:
    exported_data = response.data['data']
    memory_count = response.data['memory_count']
    
    print(f"Exported {memory_count} memories")
    
    # Save to file
    with open('alice_memories.json', 'w') as f:
        json.dump(exported_data, f, indent=2)

# Export work memories as CSV
response = client.export_memories(
    user_id="alice",
    format="csv", 
    category="work",
    min_confidence=0.7
)

if response.success:
    csv_data = response.data['data']
    with open('work_memories.csv', 'w') as f:
        f.write(csv_data)

# Export recent memories as Markdown
last_month = datetime.now() - timedelta(days=30)
response = client.export_memories(
    user_id="alice",
    format="markdown",
    from_date=last_month,
    max_memories=100
)

if response.success:
    markdown_content = response.data['data']
    with open('recent_memories.md', 'w') as f:
        f.write(markdown_content)
```

## Response Objects

All API methods return a `HarmoniaResponse` object with these properties:

```python
class HarmoniaResponse:
    success: bool           # True if request succeeded
    data: Dict[str, Any]    # Response data (empty if failed)
    error: Optional[str]    # Error message (None if succeeded)  
    status_code: int        # HTTP status code
    headers: Dict[str, str] # Response headers
    raw_response: Any       # Raw HTTP response object
```

**Usage**:
```python
response = client.store_memory("alice", "Test message")

# Check success
if response.success:
    # Access response data
    memory_id = response.data['memory_id']
    confidence = response.data['confidence']
else:
    # Handle error
    print(f"Error: {response.error}")
    print(f"Status: {response.status_code}")
```

## Error Handling

The client provides specific exception types for different error conditions:

### Exception Hierarchy

```python
HarmoniaClientError           # Base exception
├── AuthenticationError       # 401 Unauthorized  
├── AuthorizationError        # 403 Forbidden
├── ValidationError           # 400 Bad Request, 422 Unprocessable Entity
├── NotFoundError            # 404 Not Found
├── ConflictError            # 409 Conflict
├── RateLimitError           # 429 Too Many Requests
├── ServerError              # 500 Internal Server Error
├── ServiceUnavailableError  # 503 Service Unavailable
├── NetworkError             # Network connectivity issues
└── TimeoutError             # Request timeout
```

### Error Handling Examples

```python
from client import (
    HarmoniaClient, HarmoniaClientError, AuthenticationError,
    RateLimitError, ValidationError, NotFoundError, ServerError,
    NetworkError, TimeoutError
)

try:
    response = client.store_memory("alice", "Test message")
    
    if response.success:
        print(f"Success: {response.data['memory_id']}")
    else:
        print(f"API Error: {response.error}")
        
except AuthenticationError as e:
    print(f"Authentication failed: {e.message}")
    # Check API key configuration
    
except RateLimitError as e:
    print(f"Rate limited: {e.message}")
    if e.retry_after:
        print(f"Retry after {e.retry_after} seconds")
        time.sleep(e.retry_after)
        
except ValidationError as e:
    print(f"Invalid input: {e.message}")
    # Check request parameters
    
except NotFoundError as e:
    print(f"Resource not found: {e.message}")
    
except ServerError as e:
    print(f"Server error: {e.message}")
    # Log for investigation
    
except NetworkError as e:
    print(f"Network error: {e.message}")
    # Check connectivity
    
except TimeoutError as e:
    print(f"Request timeout: {e.message}")
    # Consider increasing timeout
    
except HarmoniaClientError as e:
    # Catch-all for other errors
    print(f"Client error: {e.message}")
    print(f"Status code: {e.status_code}")
```

### Retry Logic

The client includes automatic retry logic for transient errors:

```python
# Configure retry behavior
client = HarmoniaClient(
    base_url="http://localhost:8000",
    max_retries=5,        # Retry up to 5 times
    retry_delay=2.0       # 2 second base delay (exponential backoff)
)

# Retries are automatic for:
# - Network errors
# - Timeout errors  
# - 500 Internal Server Error
# - 503 Service Unavailable
# - Connection errors
```

## Context Manager Usage

Use the client as a context manager for automatic resource cleanup:

```python
# Automatic session management
with HarmoniaClient("http://localhost:8000") as client:
    response = client.health_check()
    print(f"Status: {response.data['status']}")
    
    # Store multiple memories
    messages = [
        "I love programming in Python",
        "My favorite IDE is VS Code", 
        "I enjoy working on AI projects"
    ]
    
    for message in messages:
        response = client.store_memory("alice", message)
        if response.success:
            print(f"Stored: {response.data['extracted_memory']}")

# Session automatically closed
```

## Pagination Helper

For handling paginated results efficiently:

```python
def get_all_memories(client, user_id, **filters):
    """Retrieve all memories using pagination."""
    all_memories = []
    offset = 0
    limit = 100
    
    while True:
        response = client.list_memories(
            user_id=user_id,
            limit=limit,
            offset=offset,
            **filters
        )
        
        if not response.success:
            print(f"Error: {response.error}")
            break
            
        memories = response.data['memories']
        all_memories.extend(memories)
        
        # Check if more results available
        pagination = response.data['pagination'] 
        if not pagination['has_more']:
            break
            
        offset += limit
        print(f"Retrieved {len(all_memories)} memories so far...")
    
    return all_memories

# Usage
all_work_memories = get_all_memories(
    client, 
    "alice",
    category="work",
    min_confidence=0.8
)

print(f"Total work memories: {len(all_work_memories)}")
```

## Batch Operations

For processing multiple operations efficiently:

```python
def store_multiple_memories(client, user_id, messages, max_workers=5):
    """Store multiple memories with concurrent processing."""
    import concurrent.futures
    import threading
    
    results = []
    lock = threading.Lock()
    
    def store_single(message):
        try:
            response = client.store_memory(user_id, message)
            result = {
                'message': message,
                'success': response.success,
                'memory_id': response.data.get('memory_id') if response.success else None,
                'error': response.error if not response.success else None
            }
        except Exception as e:
            result = {
                'message': message,
                'success': False,
                'memory_id': None,
                'error': str(e)
            }
        
        with lock:
            results.append(result)
            
        return result
    
    # Process in parallel
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(store_single, msg) for msg in messages]
        
        # Wait for completion
        for future in concurrent.futures.as_completed(futures):
            try:
                future.result()
            except Exception as e:
                print(f"Task failed: {e}")
    
    return results

# Usage
messages = [
    "I attended the Python conference last week",
    "The keynote about AI was fascinating", 
    "I met several interesting developers",
    "The networking session was very valuable",
    "I learned about new ML frameworks"
]

results = store_multiple_memories(client, "alice", messages)

successful = [r for r in results if r['success']]
failed = [r for r in results if not r['success']]

print(f"Successfully stored: {len(successful)}")
print(f"Failed to store: {len(failed)}")
```

## Async Usage

While the client is synchronous, you can use it in async contexts:

```python
import asyncio
import concurrent.futures

async def async_store_memory(client, user_id, message):
    """Async wrapper for memory storage."""
    loop = asyncio.get_event_loop()
    
    with concurrent.futures.ThreadPoolExecutor() as executor:
        response = await loop.run_in_executor(
            executor,
            client.store_memory,
            user_id,
            message
        )
    
    return response

async def async_search_memories(client, user_id, query):
    """Async wrapper for memory search."""
    loop = asyncio.get_event_loop()
    
    with concurrent.futures.ThreadPoolExecutor() as executor:
        response = await loop.run_in_executor(
            executor,
            client.search_memories,
            user_id,
            query
        )
    
    return response

async def main():
    """Async main function."""
    client = HarmoniaClient("http://localhost:8000")
    
    # Store memories concurrently
    tasks = []
    messages = [
        "I love async programming",
        "Concurrency makes things faster", 
        "Python asyncio is powerful"
    ]
    
    for message in messages:
        task = async_store_memory(client, "alice", message)
        tasks.append(task)
    
    # Wait for all to complete
    results = await asyncio.gather(*tasks)
    
    print("Stored memories:")
    for result in results:
        if result.success:
            print(f"- {result.data['extracted_memory']}")
    
    # Search memories
    search_result = await async_search_memories(client, "alice", "async")
    
    if search_result.success:
        memories = search_result.data['results']
        print(f"\nFound {len(memories)} async-related memories")

# Run async code
asyncio.run(main())
```

## Best Practices

### 1. Configuration Management

Use environment variables for configuration:

```python
import os

client = HarmoniaClient(
    base_url=os.getenv('HARMONIA_API_URL', 'http://localhost:8000'),
    api_key=os.getenv('HARMONIA_API_KEY'),
    timeout=int(os.getenv('HARMONIA_TIMEOUT', '30')),
    max_retries=int(os.getenv('HARMONIA_MAX_RETRIES', '3'))
)
```

### 2. Connection Testing

Test connectivity before critical operations:

```python
def test_connection(client):
    """Test basic API connectivity."""
    try:
        response = client.health_check()
        
        if response.success:
            status = response.data['status']
            if status == 'healthy':
                print("✓ API connection healthy")
                return True
            else:
                print(f"⚠ API status: {status}")
                return False
        else:
            print(f"✗ Health check failed: {response.error}")
            return False
            
    except Exception as e:
        print(f"✗ Connection test failed: {e}")
        return False

# Test before operations
if test_connection(client):
    # Proceed with operations
    response = client.store_memory("alice", "Test message")
```

### 3. Logging Configuration

Enable logging for debugging:

```python
import logging

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger('harmonia_client')

# Client operations will now log detailed information
client = HarmoniaClient("http://localhost:8000")
response = client.health_check()
```

### 4. Response Validation

Always validate responses properly:

```python
def safe_store_memory(client, user_id, message):
    """Safely store memory with proper validation."""
    try:
        response = client.store_memory(user_id, message)
        
        if response.success:
            # Validate response structure
            required_fields = ['memory_id', 'extracted_memory', 'confidence']
            
            for field in required_fields:
                if field not in response.data:
                    print(f"Warning: Missing field '{field}' in response")
                    return None
            
            return response.data
        else:
            print(f"Storage failed: {response.error}")
            return None
            
    except Exception as e:
        print(f"Unexpected error: {e}")
        return None

# Usage
result = safe_store_memory(client, "alice", "Test message")
if result:
    print(f"Memory ID: {result['memory_id']}")
    print(f"Confidence: {result['confidence']}")
```

## Troubleshooting

### Common Issues

#### 1. Import Errors
```python
# Error: ModuleNotFoundError: No module named 'client'
# Solution: Add src to Python path
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from client import HarmoniaClient
```

#### 2. Connection Errors
```python
# Error: Connection refused
# Check if API server is running
try:
    response = client.health_check()
    print("API is running")
except NetworkError as e:
    print("API server not accessible")
    # Check server status: python main.py
```

#### 3. Authentication Issues
```python
# Error: AuthenticationError
# Check API key configuration
client = HarmoniaClient(
    base_url="http://localhost:8000",
    api_key="your-valid-api-key"  # Ensure this matches server config
)
```

#### 4. Timeout Issues
```python
# Error: TimeoutError
# Increase timeout for slower operations
client = HarmoniaClient(
    base_url="http://localhost:8000",
    timeout=120  # 2 minutes for LLM processing
)
```

### Debug Mode

Enable detailed debugging:

```python
import logging

# Enable all logging
logging.basicConfig(level=logging.DEBUG)

# Enable client debugging
client = HarmoniaClient(
    base_url="http://localhost:8000",
    timeout=30
)

# Enable request/response logging
import urllib3
urllib3.disable_warnings()  # Disable SSL warnings if needed

# Operations will now show detailed request/response info
```

## Performance Tips

### 1. Connection Reuse
```python
# Reuse client instance instead of creating new ones
client = HarmoniaClient("http://localhost:8000")

# Good: Reuse connection
for message in messages:
    response = client.store_memory("alice", message)

# Avoid: Creating new clients
for message in messages:
    temp_client = HarmoniaClient("http://localhost:8000")  # Inefficient
    response = temp_client.store_memory("alice", message)
```

### 2. Batch Processing
```python
# Process in batches for better performance
def process_in_batches(items, batch_size=10):
    for i in range(0, len(items), batch_size):
        batch = items[i:i+batch_size]
        yield batch

messages = ["message1", "message2", ...]  # Large list

for batch in process_in_batches(messages, batch_size=20):
    # Process batch
    for message in batch:
        client.store_memory("alice", message)
    
    # Small delay between batches to avoid overwhelming server
    time.sleep(0.1)
```

### 3. Appropriate Timeouts
```python
# Configure timeouts based on operation type
quick_client = HarmoniaClient(
    base_url="http://localhost:8000",
    timeout=10  # For search/list operations
)

slow_client = HarmoniaClient(
    base_url="http://localhost:8000", 
    timeout=120  # For memory storage (includes LLM processing)
)
```

This comprehensive client reference provides everything needed to effectively use the Harmonia Python client in production applications.