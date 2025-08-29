# API User Guide Test Report

Generated: 2025-08-29T08:58:18.815120

## Summary

- **Total Tests**: 26
- **Passed**: 21 (80.8%)
- **Failed**: 5 (19.2%)
- **Test Duration**: 77.07 seconds

## Test Categories

### Memory Types (10 types)
Tests for all 10 memory types defined in the system:
- Personal, Factual, Emotional, Procedural, Episodic
- Relational, Preference, Goal, Skill, Temporal

### Advanced Features
- Conflict Resolution
- Temporal Resolution
- Search Functionality
- Export Formats
- Per-User Isolation
- Batch Processing
- Confidence Scoring
- Entity Extraction

## Detailed Results


### Memory Type

- ✅ **Memory Type: Personal Memory**
  - Details: Extracted memory: User is 28 years old
- ❌ **Memory Type: Factual Memory**
  - Error: Internal server error during memory storage
- ✅ **Memory Type: Emotional Memory**
  - Details: Extracted memory: User is excited about an upcoming project
- ❌ **Memory Type: Procedural Memory**
  - Error: Internal server error during memory storage
- ✅ **Memory Type: Episodic Memory**
  - Details: Extracted memory: We decided to adopt TypeScript for the new project
- ✅ **Memory Type: Relational Memory**
  - Details: Extracted memory: User has a colleague who helps with React issues
- ✅ **Memory Type: Preference Memory**
  - Details: Extracted memory: User dislikes working with legacy jQuery code
- ✅ **Memory Type: Goal Memory**
  - Details: Extracted memory: User wants to learn Rust by the end of this year
- ❌ **Memory Type: Skill Memory**
  - Error: No memory extracted
- ✅ **Memory Type: Temporal Memory**
  - Details: Extracted memory: User has a dentist appointment next Tuesday at 2 PM

### Conflict Resolution

- ✅ **Conflict Resolution: Location Update**
  - Details: No conflicts detected (may be expected)

### Temporal Resolution

- ✅ **Temporal Resolution: Tomorrow's meeting**
  - Details: Processed: I have a meeting tomorrow at 3 PM...
- ✅ **Temporal Resolution: Next week deadline**
  - Details: Processed: The project is due next Friday...
- ✅ **Temporal Resolution: Relative past**
  - Details: Processed: I started this job 3 months ago...

### Search

- ✅ **Search: Basic Query**
  - Details: Found 2 results for 'programming'
- ✅ **Search: With Confidence Filter**
  - Details: Found 1 high-confidence results

### Export

- ✅ **Export: JSON Format**
  - Details: Exported 2 characters
- ✅ **Export: CSV Format**
  - Details: Exported 0 characters
- ✅ **Export: MARKDOWN Format**
  - Details: Exported 36 characters
- ✅ **Export: TEXT Format**
  - Details: Exported 47 characters

### Per-User Database Isolation

- ✅ **Per-User Database Isolation**
  - Details: Each user sees only their own memories

### Batch Processing

- ✅ **Batch Processing**
  - Details: Processed 3/3 messages in batch

### Confidence Scoring

- ❌ **Confidence Scoring: High confidence**
  - Error: Internal server error during memory storage
- ✅ **Confidence Scoring: Medium confidence**
  - Details: Confidence: 0.93
- ✅ **Confidence Scoring: Lower confidence**
  - Details: Confidence: 0.75

### Entity Extraction

- ❌ **Entity Extraction**
  - Error: Internal server error during memory storage

## Test Users Created

Total test users: 20

- test_personal
- test_factual
- test_emotional
- test_procedural
- test_episodic
- test_relational
- test_preference
- test_goal
- test_skill
- test_temporal
- test_conflicts
- test_temporal_resolution
- test_search
- test_export
- isolation_alice
- isolation_bob
- isolation_charlie
- test_batch
- test_confidence
- test_entities

## Recommendations

⚠️ Some tests failed. Please review the errors above and:
1. Ensure the server is running with all dependencies
2. Check that Ollama is running with the required model
3. Verify database permissions and disk space
