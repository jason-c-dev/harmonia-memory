# Harmonia Python Client Documentation

The Harmonia Python client provides a convenient interface for interacting with the Harmonia Memory Storage API.

## Installation

The client is included with the Harmonia system. To use it:

```python
import sys
sys.path.append('path/to/harmonia/src')
from client import HarmoniaClient
```

For production use, you may want to package and install the client separately.

## Quick Start

```python
from client import HarmoniaClient

# Initialize client
client = HarmoniaClient(
    base_url="http://localhost:8000",
    api_key="your-api-key"  # Optional, if authentication is enabled
)

# Store a memory
response = client.store_memory(
    user_id="user123",
    message="I have a cat named Fluffy"
)

if response.success:
    print(f"Memory stored: {response.data['memory_id']}")

# Search memories
response = client.search_memories(
    user_id="user123",
    query="cat"
)

if response.success:
    for result in response.data['results']:
        print(f"Found: {result['content']}")
```

## Client Configuration

### HarmoniaClient Parameters

- **base_url** (str): Base URL of the Harmonia API server (default: "http://localhost:8000")
- **api_key** (str, optional): API key for authentication
- **timeout** (int): Request timeout in seconds (default: 30)
- **max_retries** (int): Maximum retry attempts (default: 3)
- **retry_delay** (float): Delay between retries in seconds (default: 1.0)
- **verify_ssl** (bool): Whether to verify SSL certificates (default: True)

### Example with Custom Configuration

```python
client = HarmoniaClient(
    base_url="https://api.harmonia.example.com",
    api_key="your-secure-api-key",
    timeout=60,
    max_retries=5,
    retry_delay=2.0,
    verify_ssl=True
)
```

## API Methods

### Health Check

Check API server health and status.

```python
response = client.health_check()
print(f"Status: {response.data['status']}")
print(f"Components: {response.data['components']}")
```

### Memory Storage

Store a new memory from a message.

```python
response = client.store_memory(
    user_id="user123",
    message="I have a meeting tomorrow at 2pm",
    session_id="session_abc",  # Optional
    metadata={"source": "calendar"},  # Optional
    resolution_strategy="auto"  # Optional: auto, update, merge, version
)

if response.success:
    print(f"Memory ID: {response.data['memory_id']}")
    print(f"Extracted: {response.data['extracted_memory']}")
    print(f"Action: {response.data['action']}")  # created, updated, merged
    print(f"Confidence: {response.data['confidence']}")
```

### Memory Search

Search memories with full-text search and filtering.

```python
response = client.search_memories(
    user_id="user123",
    query="meeting",
    limit=10,
    offset=0,
    category="work",  # Optional filter
    from_date=datetime(2024, 1, 1),  # Optional filter
    to_date=datetime(2024, 12, 31),  # Optional filter
    min_confidence=0.7,  # Optional filter
    max_confidence=1.0,  # Optional filter
    sort_by="relevance",  # relevance, created_at, updated_at, confidence
    sort_order="desc",  # asc, desc
    include_metadata=True
)

if response.success:
    results = response.data['results']
    pagination = response.data['pagination']
    
    print(f"Found {pagination['total_count']} results")
    for result in results:
        print(f"Score: {result['relevance_score']:.2f}")
        print(f"Content: {result['content']}")
        print(f"Highlights: {result['highlights']}")
```

### Memory Listing

List memories with filtering and pagination.

```python
response = client.list_memories(
    user_id="user123",
    limit=50,
    offset=0,
    category="personal",  # Optional filter
    from_date=datetime.now() - timedelta(days=30),  # Optional
    to_date=datetime.now(),  # Optional
    min_confidence=0.5,  # Optional
    sort_by="updated_at",
    sort_order="desc",
    include_inactive=False
)

if response.success:
    memories = response.data['memories']
    pagination = response.data['pagination']
    
    for memory in memories:
        print(f"ID: {memory['memory_id']}")
        print(f"Content: {memory['content']}")
        print(f"Created: {memory['created_at']}")
```

### Get Specific Memory

Retrieve a specific memory by ID.

```python
response = client.get_memory("memory_id_123")

if response.success:
    memory = response.data['memory']
    print(f"Content: {memory['content']}")
    print(f"Confidence: {memory['confidence_score']}")
    
    # Access update history if available
    history = response.data.get('update_history', [])
    for update in history:
        print(f"Updated: {update['updated_at']}")
```

### Delete Memory

Delete a specific memory by ID.

```python
response = client.delete_memory("memory_id_123")

if response.success:
    print(f"Deleted: {response.data['message']}")
```

### Export Memories

Export memories in various formats.

```python
response = client.export_memories(
    user_id="user123",
    format="json",  # json, csv, markdown, text
    include_metadata=True,
    category="work",  # Optional filter
    from_date=datetime(2024, 1, 1),  # Optional
    min_confidence=0.8  # Optional
)

if response.success:
    exported_data = response.data['data']
    memory_count = response.data['memory_count']
    
    print(f"Exported {memory_count} memories")
    
    # Save to file
    if response.data['format'] == 'json':
        import json
        with open('memories.json', 'w') as f:
            json.dump(exported_data, f, indent=2)
```

## Error Handling

The client provides specific exception types for different error conditions:

```python
from client import (
    HarmoniaClientError, AuthenticationError, RateLimitError,
    ValidationError, NotFoundError, ServerError, NetworkError, TimeoutError
)

try:
    response = client.store_memory("user123", "Test message")
    
except AuthenticationError as e:
    print(f"Authentication failed: {e.message}")
    
except RateLimitError as e:
    print(f"Rate limited: {e.message}")
    if e.retry_after:
        print(f"Retry after {e.retry_after} seconds")
        
except ValidationError as e:
    print(f"Invalid input: {e.message}")
    
except NotFoundError as e:
    print(f"Resource not found: {e.message}")
    
except ServerError as e:
    print(f"Server error: {e.message}")
    
except NetworkError as e:
    print(f"Network error: {e.message}")
    
except TimeoutError as e:
    print(f"Request timed out: {e.message}")
    
except HarmoniaClientError as e:
    print(f"General error: {e.message}")
    print(f"Status code: {e.status_code}")
    print(f"Response: {e.response}")
```

## Response Objects

All API methods return a `HarmoniaResponse` object with the following properties:

```python
response = client.store_memory("user123", "Test")

# Check if request succeeded
if response.success:
    print("Request succeeded")

# Access response data
data = response.data  # Parsed JSON response

# Access raw HTTP response
status_code = response.status_code
headers = response.headers
raw = response.raw_response

# Get error message if failed
if not response.success:
    error_msg = response.error
```

## Context Manager Usage

Use the client as a context manager for automatic resource cleanup:

```python
with HarmoniaClient(base_url="http://localhost:8000") as client:
    response = client.health_check()
    print(f"Status: {response.data['status']}")
    
# Session automatically closed
```

## Pagination Helper

For handling paginated results:

```python
def get_all_memories(client, user_id, **filters):
    """Get all memories using pagination."""
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
            break
            
        memories = response.data['memories']
        all_memories.extend(memories)
        
        if not response.data['pagination']['has_more']:
            break
            
        offset += limit
    
    return all_memories

# Usage
all_memories = get_all_memories(client, "user123", category="work")
```

## Best Practices

### 1. Error Handling
Always handle exceptions appropriately:

```python
try:
    response = client.store_memory(user_id, message)
    if response.success:
        # Handle success
        memory_id = response.data['memory_id']
    else:
        # Handle API-level errors
        print(f"API error: {response.error}")
        
except HarmoniaClientError as e:
    # Handle client-level errors
    print(f"Client error: {e.message}")
```

### 2. Rate Limiting
Respect rate limits and implement backoff:

```python
import time

def store_with_backoff(client, user_id, message, max_attempts=3):
    for attempt in range(max_attempts):
        try:
            return client.store_memory(user_id, message)
        except RateLimitError as e:
            if attempt < max_attempts - 1 and e.retry_after:
                time.sleep(e.retry_after)
                continue
            raise
```

### 3. Batch Operations
For multiple operations, consider batching:

```python
def store_multiple_memories(client, user_id, messages):
    """Store multiple memories with error handling."""
    results = []
    
    for message in messages:
        try:
            response = client.store_memory(user_id, message)
            results.append({
                'message': message,
                'success': response.success,
                'memory_id': response.data.get('memory_id') if response.success else None,
                'error': response.error if not response.success else None
            })
        except HarmoniaClientError as e:
            results.append({
                'message': message,
                'success': False,
                'memory_id': None,
                'error': e.message
            })
    
    return results
```

### 4. Configuration Management
Use environment variables for configuration:

```python
import os

client = HarmoniaClient(
    base_url=os.getenv('HARMONIA_API_URL', 'http://localhost:8000'),
    api_key=os.getenv('HARMONIA_API_KEY'),
    timeout=int(os.getenv('HARMONIA_TIMEOUT', '30'))
)
```

## Async Usage

While the client is synchronous, you can use it in async contexts with thread pools:

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

# Usage
response = await async_store_memory(client, "user123", "Async message")
```

## Troubleshooting

### Common Issues

1. **Connection Errors**: Check if the API server is running and accessible
2. **Authentication Errors**: Verify API key is correct and has permissions
3. **Timeout Errors**: Increase timeout value or check network connectivity
4. **Rate Limit Errors**: Implement proper backoff logic
5. **Validation Errors**: Check input data format and constraints

### Debug Mode

Enable debug logging to troubleshoot issues:

```python
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('client')

# Client operations will now log detailed information
client = HarmoniaClient(base_url="http://localhost:8000")
response = client.health_check()
```

### Testing Connection

Test basic connectivity:

```python
def test_connection(base_url):
    """Test basic API connectivity."""
    try:
        client = HarmoniaClient(base_url=base_url, timeout=5)
        response = client.health_check()
        
        if response.success:
            print(f"✓ Connected to {base_url}")
            print(f"  Status: {response.data['status']}")
            print(f"  Version: {response.data.get('version', 'unknown')}")
            return True
        else:
            print(f"✗ API error: {response.error}")
            return False
            
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        return False

# Test connection
test_connection("http://localhost:8000")
```