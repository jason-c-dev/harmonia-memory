"""
Type definitions for prompt system.
"""
from enum import Enum
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime


class MemoryType(Enum):
    """Types of memories that can be extracted."""
    PERSONAL = "personal"           # Personal information, preferences, facts about the user
    FACTUAL = "factual"            # Objective facts, data, information
    EMOTIONAL = "emotional"        # Feelings, emotions, emotional responses
    PROCEDURAL = "procedural"      # How-to information, processes, procedures
    EPISODIC = "episodic"          # Events, experiences, specific occurrences
    RELATIONAL = "relational"      # Relationships, connections between people/things
    PREFERENCE = "preference"      # Likes, dislikes, preferences, opinions
    GOAL = "goal"                  # Objectives, targets, aspirations
    SKILL = "skill"               # Abilities, competencies, learned skills
    TEMPORAL = "temporal"          # Time-related information, schedules, dates


class PromptVersion(Enum):
    """Prompt template versions."""
    V1_0 = "1.0"
    V1_1 = "1.1"
    V2_0 = "2.0"
    LATEST = "latest"


class ExtractionMode(Enum):
    """Memory extraction modes."""
    STRICT = "strict"           # Only extract explicit, clear memories
    MODERATE = "moderate"       # Extract clear and reasonably inferred memories  
    PERMISSIVE = "permissive"   # Extract all possible memories including weak inferences


@dataclass
class PromptContext:
    """Context information for prompt rendering."""
    user_id: str
    session_id: str
    message_text: str
    previous_memories: List[Dict[str, Any]] = None
    user_timezone: str = "UTC"
    extraction_mode: ExtractionMode = ExtractionMode.MODERATE
    memory_types: List[MemoryType] = None
    max_memories: int = 10
    confidence_threshold: float = 0.7
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.previous_memories is None:
            self.previous_memories = []
        if self.memory_types is None:
            self.memory_types = list(MemoryType)
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass 
class ExtractedMemory:
    """Structure for extracted memory data."""
    content: str
    memory_type: MemoryType
    confidence: float
    entities: List[str] = None
    temporal_info: Optional[str] = None
    context: Optional[str] = None
    relationships: List[str] = None
    
    def __post_init__(self):
        if self.entities is None:
            self.entities = []
        if self.relationships is None:
            self.relationships = []


@dataclass
class MemoryExtractionResult:
    """Result of memory extraction process."""
    memories: List[ExtractedMemory]
    extraction_confidence: float
    processing_time_ms: float
    prompt_version: str
    model_used: str
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'memories': [
                {
                    'content': mem.content,
                    'memory_type': mem.memory_type.value,
                    'confidence': mem.confidence,
                    'entities': mem.entities,
                    'temporal_info': mem.temporal_info,
                    'context': mem.context,
                    'relationships': mem.relationships
                }
                for mem in self.memories
            ],
            'extraction_confidence': self.extraction_confidence,
            'processing_time_ms': self.processing_time_ms,
            'prompt_version': self.prompt_version,
            'model_used': self.model_used,
            'error_message': self.error_message
        }