# Harmonia Memory Storage System - Comprehensive API User Guide

## Table of Contents
1. [Introduction & Architecture](#introduction--architecture)
2. [Memory Types Deep Dive](#memory-types-deep-dive)
3. [Complete API Workflow Examples](#complete-api-workflow-examples)
4. [Advanced Features](#advanced-features)
5. [Per-User Database Architecture](#per-user-database-architecture)
6. [Conflict Resolution Strategies](#conflict-resolution-strategies)
7. [Temporal Resolution](#temporal-resolution)
8. [Export & Backup](#export--backup)

---

## Introduction & Architecture

Harmonia is a local-first memory storage system designed for chat LLMs, providing intelligent memory extraction, storage, and retrieval with complete user data isolation.

### System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Client Application                       │
├─────────────────────────────────────────────────────────────┤
│                    Harmonia Python Client                    │
├─────────────────────────────────────────────────────────────┤
│                      FastAPI REST API                        │
├─────────────────────────────────────────────────────────────┤
│                   Memory Processing Pipeline                 │
│  ┌──────────┬──────────┬──────────┬──────────┬──────────┐  │
│  │Preprocess│ Extract  │ Conflict │ Temporal │ Confidence│  │
│  │          │ Entities │ Detect   │ Resolve  │ Score     │  │
│  └──────────┴──────────┴──────────┴──────────┴──────────┘  │
├─────────────────────────────────────────────────────────────┤
│                    LLM Integration (Ollama)                  │
├─────────────────────────────────────────────────────────────┤
│                 Per-User SQLite Databases                    │
│  ┌──────────┬──────────┬──────────┬──────────┬──────────┐  │
│  │ User A   │ User B   │ User C   │ User D   │   ...     │  │
│  │ DB File  │ DB File  │ DB File  │ DB File  │           │  │
│  └──────────┴──────────┴──────────┴──────────┴──────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### Memory Processing Pipeline

When a message is submitted for memory extraction:

1. **Preprocessing**: Clean and analyze the message
2. **Entity Extraction**: Identify people, places, things
3. **Memory Extraction**: Use LLM to extract structured memories
4. **Conflict Detection**: Check for contradictions with existing memories
5. **Temporal Resolution**: Convert relative times to absolute timestamps
6. **Confidence Scoring**: Calculate reliability scores
7. **Storage**: Save to user's isolated database

---

## Memory Types Deep Dive

Harmonia supports 10 distinct memory types, each optimized for different kinds of information:

### 1. Personal Memories
**Purpose**: Store information about the user themselves  
**Use Cases**: Name, age, occupation, background  
**Confidence Weight**: High (0.9)

```python
from client import HarmoniaClient

client = HarmoniaClient("http://localhost:8000")

# Personal memory examples
response = client.store_memory(
    user_id="alice",
    message="My name is Alice Chen and I'm 28 years old. I work as a software engineer at a startup in San Francisco."
)

# This extracts multiple personal memories:
# - "User's name is Alice Chen" (personal, confidence: 0.95)
# - "User is 28 years old" (personal, confidence: 0.95)
# - "User works as a software engineer" (personal, confidence: 0.9)
# - "User works at a startup" (personal, confidence: 0.9)
# - "User works in San Francisco" (personal, confidence: 0.9)
```

### 2. Factual Memories
**Purpose**: Objective facts and verifiable information  
**Use Cases**: Data, statistics, general knowledge  
**Confidence Weight**: High (0.85)

```python
# Factual memory examples
response = client.store_memory(
    user_id="alice",
    message="Python 3.12 was released on October 2, 2023. It includes improved error messages and performance enhancements."
)

# Extracts:
# - "Python 3.12 was released on October 2, 2023" (factual, confidence: 0.95)
# - "Python 3.12 includes improved error messages" (factual, confidence: 0.9)
# - "Python 3.12 includes performance enhancements" (factual, confidence: 0.9)
```

### 3. Emotional Memories
**Purpose**: Feelings, emotions, and emotional responses  
**Use Cases**: Mood tracking, emotional preferences  
**Confidence Weight**: Medium (0.75)

```python
# Emotional memory examples
response = client.store_memory(
    user_id="alice",
    message="I'm really excited about the upcoming project! Though I'm a bit nervous about the presentation."
)

# Extracts:
# - "User is excited about the upcoming project" (emotional, confidence: 0.85)
# - "User is nervous about the presentation" (emotional, confidence: 0.85)
```

### 4. Procedural Memories
**Purpose**: How-to information, processes, and methods  
**Use Cases**: Instructions, workflows, recipes  
**Confidence Weight**: High (0.85)

```python
# Procedural memory examples
response = client.store_memory(
    user_id="alice",
    message="To deploy our app, first run 'npm build', then 'docker build -t app .', and finally 'kubectl apply -f deploy.yaml'"
)

# Extracts:
# - "App deployment step 1: run 'npm build'" (procedural, confidence: 0.9)
# - "App deployment step 2: run 'docker build -t app .'" (procedural, confidence: 0.9)
# - "App deployment step 3: run 'kubectl apply -f deploy.yaml'" (procedural, confidence: 0.9)
```

### 5. Episodic Memories
**Purpose**: Specific events and experiences  
**Use Cases**: Past events, meetings, occurrences  
**Confidence Weight**: High (0.8)

```python
# Episodic memory examples
response = client.store_memory(
    user_id="alice",
    message="Yesterday's team meeting went really well. We decided to adopt TypeScript for the new project."
)

# Extracts:
# - "Team meeting occurred yesterday and went well" (episodic, confidence: 0.85)
# - "Team decided to adopt TypeScript for new project" (episodic, confidence: 0.9)
```

### 6. Relational Memories
**Purpose**: Relationships and connections between people/things  
**Use Cases**: Family, friends, team members, associations  
**Confidence Weight**: High (0.85)

```python
# Relational memory examples
response = client.store_memory(
    user_id="alice",
    message="My manager Sarah is very supportive. My colleague Bob helps me with React issues."
)

# Extracts:
# - "User's manager is Sarah" (relational, confidence: 0.95)
# - "Sarah is supportive" (relational, confidence: 0.85)
# - "User's colleague is Bob" (relational, confidence: 0.95)
# - "Bob helps user with React issues" (relational, confidence: 0.85)
```

### 7. Preference Memories
**Purpose**: Likes, dislikes, opinions, and preferences  
**Use Cases**: User preferences, favorites, opinions  
**Confidence Weight**: Medium (0.75)

```python
# Preference memory examples
response = client.store_memory(
    user_id="alice",
    message="I prefer VS Code over other editors. I don't like working with legacy jQuery code."
)

# Extracts:
# - "User prefers VS Code over other editors" (preference, confidence: 0.9)
# - "User dislikes working with legacy jQuery code" (preference, confidence: 0.85)
```

### 8. Goal Memories
**Purpose**: Objectives, targets, and aspirations  
**Use Cases**: Career goals, learning objectives, targets  
**Confidence Weight**: Medium (0.75)

```python
# Goal memory examples
response = client.store_memory(
    user_id="alice",
    message="I want to become a senior engineer within 2 years. My goal is to learn Rust by the end of this year."
)

# Extracts:
# - "User wants to become senior engineer within 2 years" (goal, confidence: 0.85)
# - "User's goal is to learn Rust by end of year" (goal, confidence: 0.85)
```

### 9. Skill Memories
**Purpose**: Abilities, competencies, and expertise  
**Use Cases**: Technical skills, languages, capabilities  
**Confidence Weight**: High (0.8)

```python
# Skill memory examples
response = client.store_memory(
    user_id="alice",
    message="I'm proficient in Python and JavaScript. I can also speak Mandarin and Spanish fluently."
)

# Extracts:
# - "User is proficient in Python" (skill, confidence: 0.9)
# - "User is proficient in JavaScript" (skill, confidence: 0.9)
# - "User speaks Mandarin fluently" (skill, confidence: 0.9)
# - "User speaks Spanish fluently" (skill, confidence: 0.9)
```

### 10. Temporal Memories
**Purpose**: Time-related information and schedules  
**Use Cases**: Appointments, deadlines, schedules  
**Confidence Weight**: High (0.85)

```python
# Temporal memory examples
response = client.store_memory(
    user_id="alice",
    message="I have a dentist appointment next Tuesday at 2 PM. The project deadline is March 15th."
)

# Extracts (with temporal resolution):
# - "User has dentist appointment on [resolved date] at 14:00" (temporal, confidence: 0.9)
# - "Project deadline is March 15th" (temporal, confidence: 0.95)
```

---

## Complete API Workflow Examples

### Example 1: Building User Profile Over Time

```python
from client import HarmoniaClient
import time

client = HarmoniaClient("http://localhost:8000")
user_id = "john_doe"

# Day 1: Initial introduction
print("Day 1: Initial introduction")
response = client.store_memory(
    user_id=user_id,
    message="Hi! I'm John, a data scientist from Seattle. I love hiking and photography."
)
print(f"Stored {len(response.data.get('memories_created', []))} memories")

# Day 2: Work information
print("\nDay 2: Work information")
response = client.store_memory(
    user_id=user_id,
    message="I work at Amazon on machine learning models for recommendation systems."
)

# Day 3: Update/conflict - John changes jobs
print("\nDay 3: Job change (conflict resolution)")
response = client.store_memory(
    user_id=user_id,
    message="I just started a new job at Microsoft working on Azure AI services."
)
if response.data.get('conflicts_resolved'):
    print(f"Resolved conflicts: {response.data['conflicts_resolved']}")

# Search John's current work information
print("\nSearching for current work info:")
results = client.search_memories(
    user_id=user_id,
    query="work job company",
    limit=5
)
for memory in results.data['results']:
    print(f"- {memory['content']} (confidence: {memory['confidence_score']})")

# List all memories chronologically
print("\nAll memories for John:")
memories = client.list_memories(
    user_id=user_id,
    sort_by="CREATED_AT",
    sort_order="ASC"
)
for memory in memories.data['memories']:
    print(f"- [{memory['category']}] {memory['content']}")
```

### Example 2: Extraction Modes Comparison

```python
# Demonstrate different extraction modes
test_message = "I think I might like Python, but I'm not entirely sure. Maybe I'll learn it someday."

# Strict mode - only explicit facts
print("STRICT MODE:")
response = client.store_memory(
    user_id="test_user",
    message=test_message,
    metadata={"extraction_mode": "strict"}
)
# Likely extracts nothing or very little due to uncertainty

# Moderate mode - balanced extraction
print("\nMODERATE MODE (default):")
response = client.store_memory(
    user_id="test_user",
    message=test_message,
    metadata={"extraction_mode": "moderate"}
)
# Extracts: "User is considering learning Python" with medium confidence

# Permissive mode - extract all possible information
print("\nPERMISSIVE MODE:")
response = client.store_memory(
    user_id="test_user",
    message=test_message,
    metadata={"extraction_mode": "permissive"}
)
# Extracts multiple memories including weak inferences
```

### Example 3: Multi-User Scenario

```python
# Demonstrate complete data isolation between users
users = ["alice", "bob", "charlie"]

# Each user stores their own information
for user in users:
    client.store_memory(
        user_id=user,
        message=f"My favorite programming language is {'Python' if user == 'alice' else 'JavaScript' if user == 'bob' else 'Go'}"
    )

# Search each user's memories - complete isolation
for user in users:
    results = client.search_memories(
        user_id=user,
        query="programming language"
    )
    print(f"\n{user}'s memories:")
    for memory in results.data['results']:
        print(f"  - {memory['content']}")
    # Each user only sees their own memories
```

---

## Advanced Features

### Entity Extraction

Harmonia automatically extracts entities (people, places, organizations) from messages:

```python
response = client.store_memory(
    user_id="alice",
    message="I met with Tim Cook at Apple Park in Cupertino to discuss the iPhone 15 launch."
)

# Automatically extracts entities:
# - People: ["Tim Cook"]
# - Organizations: ["Apple"]
# - Places: ["Apple Park", "Cupertino"]
# - Products: ["iPhone 15"]
```

### Confidence Scoring

Each memory receives a confidence score based on multiple factors:

```python
# High confidence (0.9+): Clear, explicit statements
client.store_memory(
    user_id="alice",
    message="My email is alice@example.com"  # Confidence: 0.95
)

# Medium confidence (0.7-0.9): Reasonable inferences
client.store_memory(
    user_id="alice",
    message="I usually work from home on Fridays"  # Confidence: 0.8
)

# Lower confidence (0.5-0.7): Uncertain or implied information
client.store_memory(
    user_id="alice",
    message="I might consider learning Kubernetes next year"  # Confidence: 0.6
)
```

### Batch Processing

Process multiple messages efficiently:

```python
messages = [
    "I graduated from Stanford in 2019",
    "My thesis was on neural networks",
    "I specialized in computer vision"
]

for message in messages:
    client.store_memory(
        user_id="alice",
        message=message,
        session_id="batch_import_001"
    )

# All memories are linked to the same session for tracking
```

### Filtering and Search

Advanced search with multiple filters:

```python
# Search with comprehensive filters
results = client.search_memories(
    user_id="alice",
    query="python",
    category="skill",  # Filter by memory type
    min_confidence=0.8,  # Only high confidence memories
    from_date="2024-01-01",  # Date range
    to_date="2024-12-31",
    sort_by="RELEVANCE",  # Sort by relevance score
    limit=10
)

# List memories with filters
memories = client.list_memories(
    user_id="alice",
    category="personal",  # Only personal memories
    min_confidence=0.7,
    include_inactive=False,  # Exclude soft-deleted memories
    sort_by="UPDATED_AT",
    sort_order="DESC"
)
```

---

## Per-User Database Architecture

### How It Works

Each user gets a completely isolated SQLite database:

```
data/users/
├── alice/
│   ├── harmonia.db       # Alice's memories
│   ├── harmonia.db-wal   # Write-ahead log
│   └── harmonia.db-shm   # Shared memory
├── bob/
│   ├── harmonia.db       # Bob's memories
│   ├── harmonia.db-wal
│   └── harmonia.db-shm
└── charlie/
    └── harmonia.db       # Charlie's memories
```

### Benefits

1. **Complete Data Isolation**: No possibility of data leakage between users
2. **Performance**: Each database is optimized for single-user access
3. **Scalability**: Add users without affecting existing ones
4. **Backup/Restore**: Easy per-user backup and recovery
5. **GDPR Compliance**: Simple user data deletion

### Automatic Database Creation

Databases are created automatically on first access:

```python
# First time user - database created automatically
response = client.store_memory(
    user_id="new_user_123",  # New user ID
    message="Hello, this is my first message!"
)
# Creates: data/users/new_user_123/harmonia.db

# Verify user exists
health = client.health_check()
print(f"Total users: {health.data['database']['total_users']}")
```

### Database Management

```python
# Get user statistics
response = client.get_user_stats(user_id="alice")
print(f"Database size: {response.data['database_size']} bytes")
print(f"Total memories: {response.data['memory_count']}")

# Export user data (GDPR compliance)
export = client.export_memories(
    user_id="alice",
    format="json",
    include_metadata=True
)
with open(f"alice_backup.json", "w") as f:
    f.write(export.data['data'])

# Delete user completely (GDPR right to erasure)
response = client.delete_user(user_id="alice")
# Removes entire alice/ directory and all data
```

---

## Conflict Resolution Strategies

When new information conflicts with existing memories, Harmonia provides intelligent resolution:

### Resolution Strategies

1. **UPDATE**: Modify existing memory with new information
2. **REPLACE**: Replace old memory entirely
3. **MERGE**: Combine both pieces of information
4. **LINK**: Keep both, create relationship between them
5. **CREATE_NEW**: Add as new memory, keep old
6. **KEEP_BOTH**: Maintain both as separate memories
7. **ARCHIVE_OLD**: Archive old, use new as primary

### Conflict Examples

```python
# Example 1: Simple update
client.store_memory(user_id="alice", message="I live in Boston")
# Later...
client.store_memory(user_id="alice", message="I moved to New York")
# Result: UPDATE strategy - "User lives in New York" (archives Boston)

# Example 2: Preference change
client.store_memory(user_id="alice", message="I love Java programming")
# Later...
client.store_memory(user_id="alice", message="I hate Java, Python is much better")
# Result: REPLACE strategy - Complete preference reversal

# Example 3: Additional information
client.store_memory(user_id="alice", message="I know Python")
# Later...
client.store_memory(user_id="alice", message="I know Python and JavaScript")
# Result: MERGE strategy - "User knows Python and JavaScript"

# Example 4: Temporal conflict
client.store_memory(user_id="alice", message="Meeting is at 2 PM")
# Later...
client.store_memory(user_id="alice", message="Meeting moved to 3 PM")
# Result: UPDATE with temporal context
```

### Custom Resolution Strategy

```python
# Force specific resolution strategy
response = client.store_memory(
    user_id="alice",
    message="I now work at Google",  # Conflicts with previous employer
    resolution_strategy="keep_both"  # Keep employment history
)

# Check resolution details
if response.data.get('conflicts_resolved'):
    for conflict in response.data['conflicts_resolved']:
        print(f"Resolved: {conflict['action']} - {conflict['conflict_type']}")
```

---

## Temporal Resolution

Harmonia intelligently converts relative time references to absolute timestamps:

### Relative Time Examples

```python
import datetime

# Current time context is automatically provided
client.store_memory(
    user_id="alice",
    message="I have a meeting tomorrow at 3 PM"
)
# Converts to: "Meeting on 2024-01-16 15:00:00" (if today is 2024-01-15)

client.store_memory(
    user_id="alice",
    message="The project is due next Friday"
)
# Converts to specific date: "Project due on 2024-01-19"

client.store_memory(
    user_id="alice",
    message="I started this job 3 months ago"
)
# Converts to: "Started job on 2023-10-15" (if today is 2024-01-15)
```

### Supported Time Expressions

- **Relative days**: tomorrow, yesterday, today
- **Relative weeks**: next week, last week, this week
- **Relative months**: next month, last month, in 2 months
- **Relative years**: next year, last year, 2 years ago
- **Day names**: Monday, Tuesday, next Monday
- **Specific dates**: January 15th, 01/15/2024, 2024-01-15
- **Time expressions**: at 3 PM, in the morning, midnight

### Timezone Handling

```python
# Specify user timezone for accurate conversion
response = client.store_memory(
    user_id="alice",
    message="Call me at 9 AM tomorrow",
    metadata={"timezone": "America/New_York"}
)
# Stores with EST/EDT timezone context

# Query with timezone awareness
results = client.search_memories(
    user_id="alice",
    query="meetings",
    from_date="2024-01-15T09:00:00-05:00",  # EST
    to_date="2024-01-15T17:00:00-05:00"
)
```

---

## Export & Backup

### Export Formats

Harmonia supports multiple export formats for different use cases:

```python
# JSON Export - Complete data with metadata
json_export = client.export_memories(
    user_id="alice",
    format="json",
    include_metadata=True
)

# CSV Export - Tabular format for analysis
csv_export = client.export_memories(
    user_id="alice",
    format="csv",
    include_metadata=False
)

# Markdown Export - Human-readable documentation
md_export = client.export_memories(
    user_id="alice",
    format="markdown",
    category="skill"  # Export only skills
)

# Plain Text Export - Simple text format
text_export = client.export_memories(
    user_id="alice",
    format="text",
    min_confidence=0.8  # High confidence only
)
```

### Filtered Exports

Export specific subsets of memories:

```python
# Export recent high-confidence personal memories
export = client.export_memories(
    user_id="alice",
    format="json",
    category="personal",
    min_confidence=0.8,
    from_date="2024-01-01",
    include_metadata=True
)

# Save to file
import json
with open("alice_personal_memories_2024.json", "w") as f:
    data = json.loads(export.data['data'])
    json.dump(data, f, indent=2)

print(f"Exported {export.data['memory_count']} memories")
```

### Backup and Restore

```python
# Full backup for a user
def backup_user(user_id: str):
    export = client.export_memories(
        user_id=user_id,
        format="json",
        include_metadata=True
    )
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"backup_{user_id}_{timestamp}.json"
    
    with open(filename, "w") as f:
        f.write(export.data['data'])
    
    return filename

# Backup all users
users = ["alice", "bob", "charlie"]
for user in users:
    backup_file = backup_user(user)
    print(f"Backed up {user} to {backup_file}")
```

---

## Best Practices

### 1. Message Quality
- Provide clear, well-structured messages for better extraction
- Include context when relevant
- Separate distinct facts into clear statements

### 2. Session Management
- Use session IDs to group related memories
- Helps with context and temporal resolution

```python
session_id = "conversation_" + str(int(time.time()))
for message in conversation_messages:
    client.store_memory(
        user_id="alice",
        message=message,
        session_id=session_id
    )
```

### 3. Confidence Thresholds
- Use higher thresholds (0.8+) for critical information
- Lower thresholds (0.6+) for exploratory analysis

### 4. Regular Maintenance
- Periodically export and backup user data
- Monitor database sizes
- Clean up inactive memories

```python
# Maintenance routine
def maintain_user_data(user_id: str):
    # Export backup
    backup_user(user_id)
    
    # Check statistics
    stats = client.get_user_stats(user_id)
    if stats.data['database_size'] > 100_000_000:  # 100MB
        print(f"Warning: Large database for {user_id}")
    
    # Clean old low-confidence memories
    memories = client.list_memories(
        user_id=user_id,
        max_confidence=0.5,
        to_date="2023-01-01"
    )
    for memory in memories.data['memories']:
        client.delete_memory(
            user_id=user_id,
            memory_id=memory['memory_id']
        )
```

### 5. Error Handling
Always implement proper error handling:

```python
from client import HarmoniaClient, HarmoniaError

try:
    response = client.store_memory(
        user_id="alice",
        message="Important information"
    )
    if response.success:
        print(f"Success: {response.data['memory_id']}")
    else:
        print(f"Failed: {response.error}")
        
except HarmoniaError as e:
    print(f"API Error: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

---

## Performance Considerations

### Memory Extraction Performance
- Simple messages: 200-500ms
- Complex messages: 500-2000ms
- Batch processing: Use session IDs for related messages

### Search Performance
- Full-text search: <100ms for 100k memories
- Filtered search: <50ms with proper indexes
- Use category filters to improve performance

### Database Performance
- Each user database handles 100k+ memories efficiently
- Automatic indexing on key fields
- SQLite WAL mode for concurrent reads

### Optimization Tips

```python
# 1. Batch related operations
messages = ["msg1", "msg2", "msg3"]
session_id = "batch_001"
for msg in messages:
    client.store_memory(user_id="alice", message=msg, session_id=session_id)

# 2. Use specific searches
# Good - specific search with filters
results = client.search_memories(
    user_id="alice",
    query="python programming",
    category="skill",
    limit=10
)

# Less optimal - broad search
results = client.search_memories(
    user_id="alice",
    query="*",  # Avoid wildcards
    limit=1000  # Large limits
)

# 3. Regular maintenance
# Archive old memories instead of keeping everything active
client.archive_memories(
    user_id="alice",
    before_date="2023-01-01",
    min_confidence=0.5
)
```

---

## Troubleshooting

### Common Issues and Solutions

**1. Memory not extracted**
- Check message clarity and structure
- Verify extraction mode (strict vs permissive)
- Review confidence thresholds

**2. Conflicts not resolving properly**
- Check resolution strategy
- Verify temporal context
- Review conflict detection sensitivity

**3. Search not finding memories**
- Check search query syntax
- Verify category filters
- Ensure memories are active (not soft-deleted)

**4. Database growing too large**
- Export and archive old memories
- Increase confidence thresholds
- Implement regular cleanup routines

---

## API Endpoints Summary

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/memory/store` | POST | Store new memory from message |
| `/api/v1/memory/search` | GET | Full-text search memories |
| `/api/v1/memory/list` | GET | List memories with filters |
| `/api/v1/memory/{id}` | GET | Get specific memory |
| `/api/v1/memory/{id}` | DELETE | Delete specific memory |
| `/api/v1/memory/export` | GET | Export memories in various formats |
| `/api/v1/health` | GET | System health check |

---

## Next Steps

1. **Run the test suite**: Execute `test_api_user_guide.py` to validate all examples
2. **Explore the API**: Use the interactive docs at `http://localhost:8000/docs`
3. **Check the client reference**: See `docs/client_reference.md` for detailed client documentation
4. **Review configuration**: See `docs/configuration.md` for system configuration options

---

*For more information, see the [main README](../README.md) or [API Reference](api_reference.md)*