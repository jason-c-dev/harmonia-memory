# Harmonia Memory API Testing Guide

This comprehensive guide provides step-by-step instructions for starting the Harmonia Memory Storage System server and testing all API endpoints using curl commands.

## Table of Contents

1. [Server Setup and Startup](#server-setup-and-startup)
2. [API Overview](#api-overview)
3. [Health Check Endpoints](#health-check-endpoints)
4. [Memory Storage Scenarios](#memory-storage-scenarios)
5. [Memory Retrieval Scenarios](#memory-retrieval-scenarios)
6. [Memory Management Operations](#memory-management-operations)
7. [Export Operations](#export-operations)
8. [Error Handling Examples](#error-handling-examples)
9. [Troubleshooting](#troubleshooting)

## Server Setup and Startup

### Prerequisites

Before starting the server, ensure you have:

1. **Python 3.11+ installed**
2. **Virtual environment activated**
3. **Dependencies installed**
4. **Database initialized**
5. **Ollama service running (optional for basic testing)**

### Quick Start

```bash
# 1. Navigate to project directory
cd /path/to/harmonia-memory

# 2. Activate virtual environment (REQUIRED)
source .venv/bin/activate

# 3. Verify environment
which python  # Should show .venv/bin/python
python --version  # Should show Python 3.11+

# 4. Initialize database (if not already done)
PYTHONPATH=src python scripts/init_db.py

# 5. Start the server
PYTHONPATH=src uvicorn main:create_app --factory --host 0.0.0.0 --port 8000 --reload
```

### Alternative Startup Methods

**Method 1: Direct Python execution**
```bash
source .venv/bin/activate
PYTHONPATH=src python -c "
import uvicorn
from main import create_app
app = create_app()
uvicorn.run(app, host='0.0.0.0', port=8000, log_level='info')
"
```

**Method 2: Background process**
```bash
source .venv/bin/activate
PYTHONPATH=src uvicorn main:create_app --factory --host 0.0.0.0 --port 8000 &
```

### Verify Server is Running

```bash
# Check if server is responding
curl -s http://localhost:8000/api/v1/health/simple

# Expected response:
# {
#   "status": "healthy",
#   "timestamp": "2025-08-20T12:30:45.123456",
#   "uptime_seconds": 123.45
# }
```

## API Overview

The Harmonia Memory API provides the following endpoints:

- **Health Checks**: `/health`, `/health/simple`
- **Memory Operations**: `/api/v1/memory/*`
- **Base URL**: `http://localhost:8000`
- **Content Type**: `application/json`

### Common Headers

All POST/PUT requests require:
```bash
-H "Content-Type: application/json"
```

## Health Check Endpoints

### Simple Health Check

```bash
curl -X GET "http://localhost:8000/api/v1/health/simple"
```

**Expected Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-08-20T12:30:45.123456",
  "uptime_seconds": 123.45
}
```

### Comprehensive Health Check

```bash
curl -X GET "http://localhost:8000/api/v1/health"
```

**Expected Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-08-20T12:30:45.123456",
  "version": "1.0.0",
  "uptime_seconds": 123.45,
  "components": {
    "database": {
      "status": "healthy",
      "connection_pool_size": 10,
      "active_connections": 1,
      "last_check": "2025-08-20T12:30:45.123456"
    },
    "search_engine": {
      "status": "healthy",
      "indexed_memories": 0,
      "last_check": "2025-08-20T12:30:45.123456"
    },
    "memory_manager": {
      "status": "healthy",
      "operations_count": 0,
      "error_count": 0,
      "error_rate": 0.0,
      "last_check": "2025-08-20T12:30:45.123456"
    }
  },
  "metadata": {
    "environment": "production",
    "api_version": "v1"
  }
}
```

## Memory Storage Scenarios

### 1. Basic Personal Information

**Store user's name:**
```bash
curl -X POST "http://localhost:8000/api/v1/memory/store" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user123",
    "message": "My name is Jason Thompson"
  }'
```

**Expected Response:**
```json
{
  "success": true,
  "memory_id": "mem_abc123def456",
  "extracted_memory": "User's name is Jason Thompson",
  "action": "created",
  "confidence": 1.0,
  "processing_time_ms": 45
}
```

### 2. Relationship Information

**Store information about pets:**
```bash
curl -X POST "http://localhost:8000/api/v1/memory/store" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user123",
    "message": "I have a golden retriever named Biggie who loves tennis balls"
  }'
```

**Expected Response:**
```json
{
  "success": true,
  "memory_id": "mem_xyz789abc123",
  "extracted_memory": "User has a golden retriever named Biggie who loves tennis balls",
  "action": "created",
  "confidence": 0.95,
  "processing_time_ms": 67
}
```

### 3. Preferences and Interests

**Store food preferences:**
```bash
curl -X POST "http://localhost:8000/api/v1/memory/store" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user123",
    "message": "I am vegetarian and love spicy Indian food"
  }'
```

**Store hobby information:**
```bash
curl -X POST "http://localhost:8000/api/v1/memory/store" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user123",
    "message": "I play guitar on weekends and enjoy jazz music"
  }'
```

### 4. Temporal Events

**Store scheduled events:**
```bash
curl -X POST "http://localhost:8000/api/v1/memory/store" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user123",
    "message": "I have a dentist appointment tomorrow at 2 PM"
  }'
```

**Store recurring events:**
```bash
curl -X POST "http://localhost:8000/api/v1/memory/store" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user123",
    "message": "I go to yoga class every Tuesday and Thursday evening"
  }'
```

### 5. Work and Professional Information

**Store job information:**
```bash
curl -X POST "http://localhost:8000/api/v1/memory/store" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user123",
    "message": "I work as a software engineer at TechCorp and specialize in machine learning"
  }'
```

### 6. Memory Updates (Conflict Resolution)

**Update existing information:**
```bash
# First, store initial information
curl -X POST "http://localhost:8000/api/v1/memory/store" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user123",
    "message": "My favorite color is blue"
  }'

# Then update it
curl -X POST "http://localhost:8000/api/v1/memory/store" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user123",
    "message": "Actually, my favorite color is green now"
  }'
```

**Expected Response for Update:**
```json
{
  "success": true,
  "memory_id": "mem_def456ghi789",
  "extracted_memory": "User's favorite color is green",
  "action": "updated",
  "confidence": 0.9,
  "processing_time_ms": 52,
  "conflicts_resolved": 1
}
```

### 7. Complex Contextual Information

**Store detailed context:**
```bash
curl -X POST "http://localhost:8000/api/v1/memory/store" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user123",
    "message": "When I lived in San Francisco from 2019 to 2022, I worked at a startup called DataFlow where I led the backend team of 5 engineers and we built APIs for financial data processing"
  }'
```

## Memory Retrieval Scenarios

### 1. Search by Keywords

**Search for pet-related memories:**
```bash
curl -X GET "http://localhost:8000/api/v1/memory/search?user_id=user123&query=dog%20pet%20animal"
```

**Search for work-related memories:**
```bash
curl -X GET "http://localhost:8000/api/v1/memory/search?user_id=user123&query=job%20work%20engineer"
```

**Expected Response:**
```json
{
  "success": true,
  "memories": [
    {
      "memory_id": "mem_xyz789abc123",
      "content": "User has a golden retriever named Biggie who loves tennis balls",
      "original_message": "I have a golden retriever named Biggie who loves tennis balls",
      "category": "pets",
      "confidence_score": 0.95,
      "timestamp": "2025-08-20T12:30:45.123456",
      "created_at": "2025-08-20T12:30:45.123456",
      "relevance_score": 0.92
    }
  ],
  "total_count": 1,
  "search_time_ms": 23
}
```

### 2. Search with Filters

**Search recent memories (last 7 days):**
```bash
curl -X GET "http://localhost:8000/api/v1/memory/search?user_id=user123&query=*&days=7"
```

**Search by category:**
```bash
curl -X GET "http://localhost:8000/api/v1/memory/search?user_id=user123&query=*&category=personal"
```

**Search with pagination:**
```bash
curl -X GET "http://localhost:8000/api/v1/memory/search?user_id=user123&query=*&limit=10&offset=0"
```

### 3. Fuzzy and Semantic Search

**Search with typos:**
```bash
curl -X GET "http://localhost:8000/api/v1/memory/search?user_id=user123&query=guitr%20musik"
```

**Search by concept:**
```bash
curl -X GET "http://localhost:8000/api/v1/memory/search?user_id=user123&query=musical%20instruments"
```

### 4. Complex Search Queries

**Multiple keyword search:**
```bash
curl -X GET "http://localhost:8000/api/v1/memory/search?user_id=user123&query=software%20engineer%20machine%20learning"
```

**Phrase search:**
```bash
curl -X GET "http://localhost:8000/api/v1/memory/search?user_id=user123&query=\"golden%20retriever\""
```

## Memory Management Operations

### 1. List All Memories

**Get all memories for a user:**
```bash
curl -X GET "http://localhost:8000/api/v1/memory/list?user_id=user123"
```

**Get memories with pagination:**
```bash
curl -X GET "http://localhost:8000/api/v1/memory/list?user_id=user123&limit=5&offset=10"
```

**Expected Response:**
```json
{
  "success": true,
  "memories": [
    {
      "memory_id": "mem_abc123def456",
      "content": "User's name is Jason Thompson",
      "original_message": "My name is Jason Thompson",
      "category": "personal",
      "confidence_score": 1.0,
      "timestamp": "2025-08-20T12:30:45.123456",
      "created_at": "2025-08-20T12:30:45.123456",
      "updated_at": "2025-08-20T12:30:45.123456",
      "is_active": true
    }
  ],
  "total_count": 1,
  "limit": 50,
  "offset": 0
}
```

### 2. Get Specific Memory

**Retrieve memory by ID:**
```bash
curl -X GET "http://localhost:8000/api/v1/memory/mem_abc123def456?user_id=user123"
```

**Expected Response:**
```json
{
  "success": true,
  "memory": {
    "memory_id": "mem_abc123def456",
    "content": "User's name is Jason Thompson",
    "original_message": "My name is Jason Thompson",
    "category": "personal",
    "confidence_score": 1.0,
    "timestamp": "2025-08-20T12:30:45.123456",
    "created_at": "2025-08-20T12:30:45.123456",
    "updated_at": "2025-08-20T12:30:45.123456",
    "metadata": {},
    "is_active": true
  }
}
```

### 3. Delete Memory

**Delete a specific memory:**
```bash
curl -X DELETE "http://localhost:8000/api/v1/memory/mem_abc123def456?user_id=user123"
```

**Expected Response:**
```json
{
  "success": true,
  "message": "Memory deleted successfully",
  "memory_id": "mem_abc123def456"
}
```

## Export Operations

### 1. Export as JSON

**Export all memories:**
```bash
curl -X GET "http://localhost:8000/api/v1/memory/export?user_id=user123&format=json" \
  -o memories_export.json
```

### 2. Export as CSV

**Export memories in CSV format:**
```bash
curl -X GET "http://localhost:8000/api/v1/memory/export?user_id=user123&format=csv" \
  -o memories_export.csv
```

### 3. Export as Markdown

**Export memories in Markdown format:**
```bash
curl -X GET "http://localhost:8000/api/v1/memory/export?user_id=user123&format=markdown" \
  -o memories_export.md
```

### 4. Filtered Export

**Export recent memories:**
```bash
curl -X GET "http://localhost:8000/api/v1/memory/export?user_id=user123&format=json&days=30" \
  -o recent_memories.json
```

**Export by category:**
```bash
curl -X GET "http://localhost:8000/api/v1/memory/export?user_id=user123&format=json&category=work" \
  -o work_memories.json
```

## Error Handling Examples

### 1. Invalid User ID

```bash
curl -X POST "http://localhost:8000/api/v1/memory/store" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "",
    "message": "Test message"
  }'
```

**Expected Error Response:**
```json
{
  "success": false,
  "error": "validation_error",
  "message": "user_id cannot be empty",
  "status_code": 400
}
```

### 2. Empty Message

```bash
curl -X POST "http://localhost:8000/api/v1/memory/store" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user123",
    "message": ""
  }'
```

**Expected Error Response:**
```json
{
  "success": false,
  "error": "validation_error",
  "message": "message cannot be empty",
  "status_code": 400
}
```

### 3. Memory Not Found

```bash
curl -X GET "http://localhost:8000/api/v1/memory/nonexistent_id?user_id=user123"
```

**Expected Error Response:**
```json
{
  "success": false,
  "error": "not_found",
  "message": "Memory not found",
  "status_code": 404
}
```

### 4. Server Error Simulation

**Force a server error (if debugging):**
```bash
curl -X GET "http://localhost:8000/api/v1/memory/search?user_id=user123&query=*&limit=-1"
```

## Troubleshooting

### Common Issues and Solutions

#### 1. Server Not Starting

**Problem**: `ImportError` or `ModuleNotFoundError`
```bash
# Solution: Ensure virtual environment is activated and PYTHONPATH is set
source .venv/bin/activate
export PYTHONPATH=src
```

**Problem**: Database connection failed
```bash
# Solution: Initialize database
PYTHONPATH=src python scripts/init_db.py
```

#### 2. Connection Refused

**Problem**: `curl: (7) Failed to connect to localhost port 8000: Connection refused`
```bash
# Solution: Check if server is running
ps aux | grep uvicorn

# Restart server if needed
PYTHONPATH=src uvicorn main:create_app --factory --host 0.0.0.0 --port 8000
```

#### 3. JSON Parse Errors

**Problem**: `422 Unprocessable Entity`
```bash
# Solution: Check JSON syntax and Content-Type header
curl -X POST "http://localhost:8000/api/v1/memory/store" \
  -H "Content-Type: application/json" \  # This header is required
  -d '{"user_id": "test", "message": "valid json"}'  # Valid JSON syntax
```

#### 4. Performance Issues

**Problem**: Slow response times
```bash
# Check server logs for bottlenecks
tail -f server.log

# Monitor system resources
top -p $(pgrep uvicorn)
```

### Debugging Commands

**Check server status:**
```bash
curl -s http://localhost:8000/api/v1/health | jq '.'
```

**Test database connectivity:**
```bash
curl -s http://localhost:8000/api/v1/health | jq '.components.database.status'
```

**Check memory count:**
```bash
curl -s "http://localhost:8000/api/v1/memory/list?user_id=test_user&limit=1" | jq '.total_count'
```

**Verbose curl output:**
```bash
curl -v -X GET "http://localhost:8000/api/v1/health/simple"
```

### Log Analysis

**View server logs:**
```bash
# If running with systemd
journalctl -u harmonia-memory -f

# If running in terminal
tail -f /path/to/log/file

# Check for specific errors
grep -i error /path/to/log/file
```

## Advanced Testing Scenarios

### Load Testing with Multiple Users

```bash
# Create memories for multiple users
for i in {1..10}; do
  curl -X POST "http://localhost:8000/api/v1/memory/store" \
    -H "Content-Type: application/json" \
    -d "{\"user_id\": \"user$i\", \"message\": \"Test message for user $i\"}"
done
```

### Concurrent Request Testing

```bash
# Run multiple curl commands in parallel
for i in {1..5}; do
  curl -X GET "http://localhost:8000/api/v1/memory/search?user_id=user123&query=test" &
done
wait
```

### Memory Stress Testing

```bash
# Store a large number of memories
for i in {1..100}; do
  curl -X POST "http://localhost:8000/api/v1/memory/store" \
    -H "Content-Type: application/json" \
    -d "{\"user_id\": \"stress_test_user\", \"message\": \"Stress test memory number $i with some additional content to make it longer\"}"
done
```

---

## Summary

This guide provides comprehensive coverage of:

- ✅ Server startup and configuration
- ✅ All API endpoints with practical examples
- ✅ Memory storage scenarios (personal info, relationships, preferences, temporal events, work, updates, complex context)
- ✅ Memory retrieval scenarios (keyword search, filters, fuzzy search, complex queries)
- ✅ Memory management operations (list, get, delete)
- ✅ Export operations in multiple formats
- ✅ Error handling and validation examples
- ✅ Troubleshooting and debugging guidance
- ✅ Advanced testing scenarios

For additional help, refer to:
- [API Reference](./api.md) - Detailed API specification
- [System Architecture](../feature/initial-design/design.md) - Technical implementation details
- [Project README](../README.md) - Project overview and setup

---

*Generated for Harmonia Memory Storage System v1.0.0*