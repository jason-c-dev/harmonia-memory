# Harmonia Memory Storage API Reference

## Overview

The Harmonia Memory Storage API provides a RESTful interface for storing, searching, and managing intelligent memory data extracted from natural language messages. The API is built with FastAPI and provides comprehensive memory management capabilities with full-text search, conflict resolution, and export functionality.

> **📖 For comprehensive usage examples with all 10 memory types and advanced features, see the [API User Guide](api_user_guide.md)**

**Base URL**: `http://localhost:8000`  
**API Version**: `v1`  
**Content Type**: `application/json`

## Authentication

Authentication is optional and disabled by default. When enabled, the API uses API key authentication.

```http
Authorization: Bearer your-api-key-here
```

## Rate Limiting

- **Default Limits**: 100 requests per minute, 1000 requests per hour
- **Rate Limit Headers**: 
  - `X-RateLimit-Limit`: Request limit
  - `X-RateLimit-Remaining`: Remaining requests
  - `X-RateLimit-Reset`: Reset timestamp

## Response Format

All API responses follow this standard format:

```json
{
  "success": true,
  "data": {},
  "error": null,
  "timestamp": "2025-08-23T12:30:45.123456Z"
}
```

**Error Response Format**:
```json
{
  "success": false,
  "error": "error_type",
  "message": "Human readable error message",
  "status_code": 400,
  "timestamp": "2025-08-23T12:30:45.123456Z"
}
```

## Health Check Endpoints

### Simple Health Check
**GET** `/api/v1/health/simple`

Check if the API server is running and responsive.

**Response**: 200 OK
```json
{
  "status": "healthy",
  "timestamp": "2025-08-23T12:30:45.123456Z",
  "uptime_seconds": 123.45
}
```

### Comprehensive Health Check  
**GET** `/api/v1/health`

Detailed health status including all system components.

**Response**: 200 OK
```json
{
  "status": "healthy",
  "timestamp": "2025-08-23T12:30:45.123456Z",
  "version": "1.0.0",
  "uptime_seconds": 123.45,
  "components": {
    "database": {
      "status": "healthy",
      "connection_pool_size": 10,
      "active_connections": 1,
      "last_check": "2025-08-23T12:30:45.123456Z"
    },
    "search_engine": {
      "status": "healthy", 
      "indexed_memories": 1250,
      "last_check": "2025-08-23T12:30:45.123456Z"
    },
    "memory_manager": {
      "status": "healthy",
      "operations_count": 5432,
      "error_count": 12,
      "error_rate": 0.0022,
      "last_check": "2025-08-23T12:30:45.123456Z"
    },
    "ollama": {
      "status": "healthy",
      "model": "llama3.2:3b",
      "response_time_ms": 245,
      "last_check": "2025-08-23T12:30:45.123456Z"
    }
  },
  "metadata": {
    "environment": "production",
    "api_version": "v1"
  }
}
```

## Memory Management Endpoints

### Store Memory
**POST** `/api/v1/memory/store`

Extract and store memories from a natural language message using LLM processing.

**Request Body**:
```json
{
  "user_id": "user123",
  "message": "I have a golden retriever named Max who loves playing fetch",
  "session_id": "session_abc123",
  "metadata": {
    "source": "chat",
    "channel": "general"
  },
  "resolution_strategy": "auto"
}
```

**Parameters**:
- `user_id` (required): Unique identifier for the user
- `message` (required): Natural language message to extract memories from
- `session_id` (optional): Chat session identifier for context
- `metadata` (optional): Additional metadata to store with the memory
- `resolution_strategy` (optional): Conflict resolution strategy (`auto`, `update`, `merge`, `version`, `skip`)

**Response**: 200 OK
```json
{
  "success": true,
  "memory_id": "mem_abc123def456",
  "extracted_memory": "User has a golden retriever named Max who loves playing fetch",
  "action": "created",
  "confidence": 0.95,
  "processing_time_ms": 67,
  "conflicts_resolved": 0,
  "metadata": {
    "memory_type": "relational",
    "entities": ["Max", "golden retriever"],
    "extraction_model": "llama3.2:3b"
  }
}
```

**Error Responses**:
- `400 Bad Request`: Invalid input data
- `422 Unprocessable Entity`: Validation errors
- `500 Internal Server Error`: Processing failed

### Search Memories
**GET** `/api/v1/memory/search`

Search memories using full-text search with advanced filtering options.

**Query Parameters**:
- `user_id` (required): User identifier
- `query` (required): Search query string
- `limit` (optional, default: 10): Maximum number of results  
- `offset` (optional, default: 0): Pagination offset
- `category` (optional): Filter by memory category
- `from_date` (optional): ISO 8601 date string for date range start
- `to_date` (optional): ISO 8601 date string for date range end
- `min_confidence` (optional): Minimum confidence score (0.0-1.0)
- `max_confidence` (optional): Maximum confidence score (0.0-1.0)
- `sort_by` (optional): Sort field (`relevance`, `created_at`, `updated_at`, `confidence`)
- `sort_order` (optional): Sort order (`asc`, `desc`)
- `include_metadata` (optional): Include memory metadata in results

**Example**: `/api/v1/memory/search?user_id=user123&query=dog+pet&limit=5&category=pets&min_confidence=0.7`

**Response**: 200 OK
```json
{
  "success": true,
  "results": [
    {
      "memory_id": "mem_abc123def456",
      "content": "User has a golden retriever named Max who loves playing fetch",
      "original_message": "I have a golden retriever named Max who loves playing fetch",
      "category": "pets",
      "confidence_score": 0.95,
      "timestamp": "2025-08-23T12:30:45.123456Z",
      "created_at": "2025-08-23T12:30:45.123456Z",
      "updated_at": "2025-08-23T12:30:45.123456Z",
      "relevance_score": 0.92,
      "highlights": ["<mark>golden retriever</mark> named Max"],
      "metadata": {
        "source": "chat",
        "entities": ["Max", "golden retriever"]
      }
    }
  ],
  "pagination": {
    "total_count": 1,
    "limit": 10,
    "offset": 0,
    "has_more": false
  },
  "search_time_ms": 4
}
```

### List Memories  
**GET** `/api/v1/memory/list`

List memories with optional filtering and pagination.

**Query Parameters**:
- `user_id` (required): User identifier
- `limit` (optional, default: 50): Maximum number of results
- `offset` (optional, default: 0): Pagination offset
- `category` (optional): Filter by category
- `from_date` (optional): Date range start
- `to_date` (optional): Date range end
- `min_confidence` (optional): Minimum confidence score
- `sort_by` (optional): Sort field (`created_at`, `updated_at`, `confidence`)
- `sort_order` (optional): Sort order (`asc`, `desc`) 
- `include_inactive` (optional): Include soft-deleted memories

**Response**: 200 OK
```json
{
  "success": true,
  "memories": [
    {
      "memory_id": "mem_abc123def456",
      "content": "User has a golden retriever named Max who loves playing fetch",
      "original_message": "I have a golden retriever named Max who loves playing fetch",
      "category": "pets",
      "confidence_score": 0.95,
      "timestamp": "2025-08-23T12:30:45.123456Z",
      "created_at": "2025-08-23T12:30:45.123456Z",
      "updated_at": "2025-08-23T12:30:45.123456Z",
      "is_active": true,
      "metadata": {}
    }
  ],
  "pagination": {
    "total_count": 1,
    "limit": 50,
    "offset": 0,
    "has_more": false
  }
}
```

### Get Memory by ID
**GET** `/api/v1/memory/{memory_id}`

Retrieve a specific memory by its ID.

**Path Parameters**:
- `memory_id`: Unique memory identifier

**Query Parameters**:
- `user_id` (required): User identifier for access control

**Response**: 200 OK
```json
{
  "success": true,
  "memory": {
    "memory_id": "mem_abc123def456",
    "content": "User has a golden retriever named Max who loves playing fetch",
    "original_message": "I have a golden retriever named Max who loves playing fetch",
    "category": "pets",
    "confidence_score": 0.95,
    "timestamp": "2025-08-23T12:30:45.123456Z",
    "created_at": "2025-08-23T12:30:45.123456Z", 
    "updated_at": "2025-08-23T12:30:45.123456Z",
    "metadata": {
      "source": "chat",
      "entities": ["Max", "golden retriever"],
      "memory_type": "relational"
    },
    "is_active": true
  },
  "update_history": [
    {
      "updated_at": "2025-08-23T12:30:45.123456Z",
      "previous_content": "User has a dog named Max",
      "action": "updated",
      "reason": "conflict_resolution"
    }
  ]
}
```

**Error Responses**:
- `404 Not Found`: Memory not found or access denied

### Delete Memory
**DELETE** `/api/v1/memory/{memory_id}`

Delete a specific memory (soft delete).

**Path Parameters**:
- `memory_id`: Unique memory identifier

**Query Parameters**:
- `user_id` (required): User identifier for access control

**Response**: 200 OK
```json
{
  "success": true,
  "message": "Memory deleted successfully",
  "memory_id": "mem_abc123def456"
}
```

## Export Endpoints

### Export Memories
**GET** `/api/v1/memory/export`

Export memories in various formats with optional filtering.

**Query Parameters**:
- `user_id` (required): User identifier
- `format` (required): Export format (`json`, `csv`, `markdown`, `text`)
- `include_metadata` (optional): Include metadata in export
- `category` (optional): Filter by category
- `from_date` (optional): Date range start
- `to_date` (optional): Date range end  
- `min_confidence` (optional): Minimum confidence score
- `max_memories` (optional): Maximum memories to export

**Response**: 200 OK

**JSON Format**:
```json
{
  "success": true,
  "format": "json",
  "memory_count": 150,
  "exported_at": "2025-08-23T12:30:45.123456Z",
  "data": [
    {
      "memory_id": "mem_abc123def456",
      "content": "User has a golden retriever named Max who loves playing fetch",
      "category": "pets",
      "confidence_score": 0.95,
      "created_at": "2025-08-23T12:30:45.123456Z",
      "metadata": {}
    }
  ]
}
```

**CSV Format**:
```
memory_id,content,category,confidence_score,created_at
mem_abc123def456,"User has a golden retriever named Max",pets,0.95,2025-08-23T12:30:45.123456Z
```

**Markdown Format**:
```markdown
# Memory Export

**User ID**: user123  
**Export Date**: 2025-08-23T12:30:45.123456Z  
**Total Memories**: 150

## Pets
- User has a golden retriever named Max who loves playing fetch (Confidence: 0.95)

## Work
- User works as a software engineer at TechCorp (Confidence: 0.98)
```

**Text Format**:
```
HARMONIA MEMORY EXPORT
User: user123
Date: 2025-08-23T12:30:45.123456Z
Total Memories: 150

[PETS]
User has a golden retriever named Max who loves playing fetch

[WORK]  
User works as a software engineer at TechCorp
```

## Memory Types

The system supports 12 distinct memory types for intelligent categorization:

| Type | Description | Examples |
|------|-------------|----------|
| `personal` | Personal information and characteristics | Name, age, location, traits |
| `factual` | Objective facts and data | Statistics, dates, procedures |
| `emotional` | Feelings and emotional responses | "I'm excited", "feeling anxious" |
| `relational` | Relationships and connections | "Sarah is my friend", family info |
| `temporal` | Time-related information | Appointments, schedules, deadlines |
| `procedural` | How-to information and processes | Recipes, workflows, instructions |
| `episodic` | Specific events and experiences | "Last weekend I went...", trips |
| `preference` | Likes, dislikes, and opinions | "I love pizza", favorite colors |
| `goal` | Objectives and aspirations | "I want to learn Spanish" |
| `skill` | Abilities and competencies | "I'm proficient in Python" |
| `meta` | Information about information | Source citations, context |
| `other` | Miscellaneous valuable information | Uncategorized memories |

## Conflict Resolution Strategies

When storing memories that conflict with existing ones, the API supports several resolution strategies:

| Strategy | Description | Use Case |
|----------|-------------|----------|
| `auto` | Automatic resolution based on confidence | Default, lets system decide |
| `update` | Replace old memory with new one | Corrections and updates |
| `merge` | Combine information from both | Complementary information |
| `version` | Keep both as separate versions | Track changes over time |
| `skip` | Keep existing memory, ignore new | Preserve established facts |

## Error Codes

| HTTP Code | Error Type | Description |
|-----------|------------|-------------|
| 400 | `validation_error` | Invalid request data or parameters |
| 401 | `authentication_error` | Invalid or missing API key |
| 403 | `authorization_error` | Insufficient permissions |
| 404 | `not_found` | Resource not found |
| 409 | `conflict_error` | Resource conflict |
| 422 | `processing_error` | Memory processing failed |
| 429 | `rate_limit_exceeded` | Too many requests |
| 500 | `internal_error` | Server error |
| 503 | `service_unavailable` | Service temporarily unavailable |

## Usage Examples

### Store Personal Information
```bash
curl -X POST "http://localhost:8000/api/v1/memory/store" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user123",
    "message": "My name is Alice and I work as a software engineer at TechCorp"
  }'
```

### Search for Work-Related Memories
```bash
curl "http://localhost:8000/api/v1/memory/search?user_id=user123&query=work+engineer&category=factual"
```

### Export Recent Memories as JSON
```bash
curl "http://localhost:8000/api/v1/memory/export?user_id=user123&format=json&from_date=2025-08-01" \
  -o memories.json
```

### Update Existing Information
```bash
curl -X POST "http://localhost:8000/api/v1/memory/store" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user123", 
    "message": "I now work at NewCorp as a senior engineer",
    "resolution_strategy": "update"
  }'
```

## Performance Characteristics

- **Memory Storage**: Average 67ms (including LLM processing)
- **Search Operations**: Average 4ms with BM25 ranking  
- **CRUD Operations**: 2-3ms for database operations
- **Export Operations**: 3ms for up to 10k memories
- **Rate Limits**: 100 req/min, 1000 req/hour by default
- **Concurrent Users**: Optimized for 10+ simultaneous users

## SDK Support

Official Python client SDK available:

```python
from client import HarmoniaClient

client = HarmoniaClient(base_url="http://localhost:8000")
response = client.store_memory("user123", "I love programming")
```

See [Client Documentation](client_reference.md) for complete SDK reference.

## Interactive Documentation

When running the server, visit:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
- **OpenAPI JSON**: `http://localhost:8000/openapi.json`

## Version History

- **v1.0.0**: Initial release with full memory management capabilities
  - Memory storage with LLM extraction
  - Full-text search with BM25 ranking
  - Export functionality in 4 formats
  - Conflict resolution system
  - Production-ready API with authentication and rate limiting