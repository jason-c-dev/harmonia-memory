# Prompt Engineering Documentation

## Overview

This document describes the prompt engineering decisions, design principles, and best practices used in the Harmonia Memory Storage System for extracting memories from user messages using Large Language Models (LLMs).

## Design Principles

### 1. **Structured Output Format**
- **Decision**: Use JSON as the primary output format for memory extraction
- **Rationale**: JSON provides structure that is easily parsable, validates well, and allows for complex nested data
- **Implementation**: All prompts explicitly request JSON responses with detailed schema specifications

### 2. **Confidence-Based Extraction**
- **Decision**: Include confidence scores (0.0-1.0) for each extracted memory
- **Rationale**: Enables filtering of low-quality extractions and provides transparency in AI decision-making
- **Implementation**: Prompts explicitly request confidence scores and explain the scoring criteria

### 3. **Multi-Modal Memory Types**
- **Decision**: Support 10 distinct memory types (Personal, Factual, Emotional, etc.)
- **Rationale**: Different types of information require different extraction strategies and have different retention values
- **Implementation**: Type-specific prompts tailored to each memory category

### 4. **Extraction Mode Flexibility**
- **Decision**: Provide three extraction modes (Strict, Moderate, Permissive)
- **Rationale**: Different use cases require different sensitivity levels for memory extraction
- **Implementation**: Mode-specific instructions embedded in system prompts

## Prompt Architecture

### System Prompt Structure

```
[Role Definition] → [Extraction Guidelines] → [Mode-Specific Instructions] → [Output Format] → [Quality Requirements]
```

#### Role Definition
- Establishes the AI as a "memory extraction AI for the Harmonia Memory System"
- Creates clear context and responsibility boundaries
- Emphasizes the importance of accuracy and relevance

#### Extraction Guidelines
- Core principles for what constitutes a valuable memory
- Focus on personal, factual, emotional, and significant information
- Emphasis on accuracy and appropriate confidence scoring

#### Mode-Specific Instructions
- **Strict Mode**: High confidence threshold (>0.8), explicit statements only
- **Moderate Mode**: Balanced approach with reasonable inferences
- **Permissive Mode**: Extract all potentially valuable information including weak inferences

#### Output Format Specification
- Detailed JSON schema with required fields
- Example structure provided for clarity
- Explicit instruction to return only valid JSON

### Template System

#### Variable Substitution
- Uses `{{variable_name}}` syntax for dynamic content injection
- Supports complex objects through JSON serialization
- Handles missing variables with clear error indicators

#### Conditional Rendering
- `{{#if condition}}...{{/if}}` blocks for mode-specific content
- `{{#unless condition}}...{{/unless}}` blocks for negative conditions
- Enables single templates to handle multiple scenarios

#### Context Injection
- Automatic conversion of PromptContext objects to template variables
- Rich context including user info, session data, and extraction parameters
- Previous memories included for context awareness

## Memory Type Strategies

### Personal Memories
- **Focus**: Biographical information, personal characteristics, individual circumstances
- **Extraction Strategy**: Look for self-referential statements and personal identifiers
- **Examples**: Name, age, location, occupation, personal traits

### Factual Memories
- **Focus**: Objective facts, data points, verifiable information
- **Extraction Strategy**: Identify statements that can be independently verified
- **Examples**: Statistics, dates, scientific facts, procedural information

### Emotional Memories
- **Focus**: Feelings, emotions, emotional responses, mood indicators
- **Extraction Strategy**: Detect emotional language, sentiment indicators, feeling expressions
- **Examples**: "I'm excited", "feeling anxious", "love this"

### Procedural Memories
- **Focus**: How-to information, processes, step-by-step instructions
- **Extraction Strategy**: Identify sequential actions, instructional content
- **Examples**: Recipes, workflows, routines, methods

### Episodic Memories
- **Focus**: Specific events, experiences, temporal occurrences
- **Extraction Strategy**: Look for narrative elements, time markers, specific incidents
- **Examples**: "Last weekend I went...", "My graduation was..."

### Relational Memories
- **Focus**: Relationships between people, connections between concepts
- **Extraction Strategy**: Identify social connections and conceptual relationships
- **Examples**: "Sarah is my friend", "This reminds me of..."

### Preference Memories
- **Focus**: Likes, dislikes, opinions, taste preferences
- **Extraction Strategy**: Detect preference indicators and value judgments
- **Examples**: "I love...", "I can't stand...", "My favorite..."

### Goal Memories
- **Focus**: Objectives, aspirations, plans, desired outcomes
- **Extraction Strategy**: Identify forward-looking statements and intentions
- **Examples**: "I want to...", "My goal is...", "I plan to..."

### Skill Memories
- **Focus**: Abilities, competencies, learned skills, expertise
- **Extraction Strategy**: Detect capability statements and skill claims
- **Examples**: "I'm proficient in...", "I can...", "I've learned..."

### Temporal Memories
- **Focus**: Time-related information, schedules, dates, temporal patterns
- **Extraction Strategy**: Extract time markers and scheduling information
- **Examples**: Appointments, deadlines, schedules, time-based patterns

## Prompt Optimization Techniques

### 1. **Few-Shot Learning**
- **Implementation**: Provide 1-3 examples of correct memory extraction
- **Benefits**: Improves consistency and quality of extractions
- **Usage**: Applied for complex message types or when accuracy is critical

### 2. **Chain of Thought**
- **Implementation**: Request reasoning explanations alongside extractions
- **Benefits**: Improves extraction quality and provides debugging insights
- **Usage**: Include "reasoning" field in JSON output for complex extractions

### 3. **Temperature Control**
- **Low Temperature (0.1-0.3)**: For consistent, reliable extractions
- **Medium Temperature (0.4-0.6)**: For balanced creativity and consistency
- **High Temperature (0.7-1.0)**: For exploratory or creative extractions

### 4. **Token Management**
- **System Prompts**: ~800-1200 tokens for comprehensive instructions
- **User Prompts**: Variable based on message length and context
- **Output Limits**: 300-500 tokens for typical memory extractions

## Quality Assurance

### Validation Rules

#### Structural Validation
- Valid JSON format required
- Required fields: content, memory_type, confidence
- Optional fields: entities, temporal_info, context, relationships

#### Content Validation
- Memory type must be from valid enum values
- Confidence score must be between 0.0 and 1.0
- Content must be non-empty and meaningful

#### Semantic Validation
- Extracted content should relate to original message
- Memory type should match content category
- Confidence should reflect extraction certainty

### Error Handling

#### Malformed Responses
- JSON parsing errors trigger re-extraction with simplified prompts
- Partial responses are salvaged when possible
- Fallback to structured text parsing for critical failures

#### Low-Quality Extractions
- Confidence thresholds filter unreliable memories
- Content length minimums prevent trivial extractions
- Relevance scoring ensures message-memory alignment

## Performance Optimization

### Prompt Caching
- System prompts cached to reduce token usage
- Template compilation cached for frequently used patterns
- Context injection optimized for minimal overhead

### Batch Processing
- Multiple messages can be processed with shared context
- Batch-specific optimizations for related message groups
- Parallel processing for independent extractions

### Model Selection
- **llama3.2:3b**: Balanced performance and speed for most tasks
- **Larger models**: Available for complex or critical extractions
- **Model switching**: Automatic based on message complexity

## Versioning Strategy

### Template Versioning
- Semantic versioning (1.0, 1.1, 2.0) for prompt templates
- Backward compatibility maintained for API stability
- Performance metrics tracked per version for optimization

### A/B Testing Framework
- Multiple prompt versions tested simultaneously
- Accuracy and performance metrics compared
- Best-performing versions promoted to production

### Migration Strategy
- Gradual rollout of new prompt versions
- Fallback to previous versions on failure
- User feedback integration for prompt improvement

## Best Practices

### Prompt Design
1. **Be Explicit**: Clear instructions prevent ambiguous interpretations
2. **Provide Examples**: Few-shot learning improves consistency
3. **Use Structure**: JSON schema guides output format
4. **Handle Edge Cases**: Account for empty, vague, or irrelevant messages

### Context Management
1. **Include Relevant History**: Previous memories provide context
2. **Limit Context Size**: Balance completeness with token efficiency
3. **Maintain Session State**: Track extraction patterns across conversations

### Quality Control
1. **Validate Everything**: Never trust LLM output without validation
2. **Use Confidence Scores**: Filter low-quality extractions
3. **Monitor Performance**: Track accuracy and adjust prompts accordingly
4. **Implement Fallbacks**: Handle failures gracefully

## Common Challenges and Solutions

### Challenge: Inconsistent Output Format
- **Solution**: Strict JSON schema enforcement with validation
- **Prevention**: Clear format examples and explicit instructions

### Challenge: Over-Extraction of Trivial Information
- **Solution**: Confidence thresholds and relevance filtering
- **Prevention**: Better definition of "valuable memory" in prompts

### Challenge: Missing Important Memories
- **Solution**: Multiple extraction passes with different strategies
- **Prevention**: Comprehensive memory type coverage and permissive mode

### Challenge: Language Model Hallucination
- **Solution**: Strict adherence to source message content
- **Prevention**: Explicit instructions to extract only stated information

### Challenge: Performance Degradation
- **Solution**: Prompt optimization and model selection
- **Prevention**: Regular performance monitoring and A/B testing

## Future Improvements

### Planned Enhancements
1. **Multi-Language Support**: Prompt templates for non-English messages
2. **Domain-Specific Prompts**: Specialized prompts for technical, medical, legal domains
3. **Adaptive Extraction**: Dynamic prompt adjustment based on user behavior
4. **Semantic Similarity**: Enhanced relevance scoring using embeddings

### Research Areas
1. **Prompt Compression**: Reducing token usage while maintaining quality
2. **Multi-Modal Integration**: Handling images, audio, and other content types
3. **Continuous Learning**: Prompt optimization based on user feedback
4. **Explainable Extraction**: Better transparency in memory extraction decisions

## Conclusion

The prompt engineering approach for Harmonia Memory Storage System prioritizes accuracy, consistency, and flexibility while maintaining high performance. The structured approach to prompt design, comprehensive validation, and continuous optimization ensures reliable memory extraction across diverse use cases and message types.

The modular template system allows for easy maintenance and experimentation, while the versioning framework enables safe deployment of prompt improvements. This foundation supports the system's goal of creating a reliable, intelligent memory system for personal and professional use.