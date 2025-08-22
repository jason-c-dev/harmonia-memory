"""
Conflict detection engine for identifying conflicts between memories.
"""
import re
import difflib
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple, Set
from dataclasses import dataclass
from enum import Enum
import logging

from models.memory import Memory
from core.logging import get_logger

logger = get_logger(__name__)


class ConflictType(Enum):
    """Types of memory conflicts."""
    EXACT_DUPLICATE = "exact_duplicate"
    PARTIAL_DUPLICATE = "partial_duplicate"
    CONTRADICTION = "contradiction"
    TEMPORAL_OVERLAP = "temporal_overlap"
    UPDATE_NEEDED = "update_needed"
    MERGE_CANDIDATE = "merge_candidate"
    RELATED_MEMORY = "related_memory"


class ConflictSeverity(Enum):
    """Severity levels for conflicts."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Conflict:
    """Information about a detected conflict."""
    conflict_type: ConflictType
    severity: ConflictSeverity
    new_memory: Memory
    existing_memory: Memory
    similarity_score: float
    confidence: float
    details: Dict[str, Any]
    suggested_action: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert conflict to dictionary for serialization."""
        return {
            'conflict_type': self.conflict_type.value,
            'severity': self.severity.value,
            'new_memory_id': self.new_memory.memory_id,
            'existing_memory_id': self.existing_memory.memory_id,
            'similarity_score': self.similarity_score,
            'confidence': self.confidence,
            'details': self.details,
            'suggested_action': self.suggested_action
        }


class ConflictDetector:
    """Detects conflicts between new and existing memories."""
    
    def __init__(self):
        """Initialize conflict detector with configurable thresholds."""
        self.logger = logger
        
        # Similarity thresholds
        self.exact_duplicate_threshold = 0.95
        self.partial_duplicate_threshold = 0.6
        self.related_memory_threshold = 0.4
        
        # Temporal overlap threshold (in hours)
        self.temporal_overlap_threshold = 2.0
        
        # Common contradiction patterns
        self.contradiction_patterns = [
            # Negation patterns with specific context
            (r'\b(like|love|enjoy)s?\b', r'\b(don\'t|doesn\'t|never)\s+(?:like|love|enjoy)\b'),
            (r'\bis\s+(married)\b', r'\bis\s+(single)\b'),
            (r'\bis\s+(single)\b', r'\bis\s+(married)\b'),
            (r'\b(works?\s+at)\b', r'\b(quit|fired|left|unemployed)\b'),
            (r'\b(lives?\s+in)\b', r'\b(moved\s+(?:from|away)|left)\b'),
        ]
        
        # Entity extraction patterns for relationship detection
        self.entity_patterns = {
            'person': r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2})\b(?=\s+(?:works?|is|has|lives?|goes?))',
            'location': r'\b(?:in|at|from|to)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2})\b',
            'organization': r'\b(?:works?\s+at|employed\s+by|company|corporation)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2})\b',
            'date': r'\b(\d{1,2}[-/]\d{1,2}[-/]\d{2,4}|\d{4}[-/]\d{1,2}[-/]\d{1,2}|(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}(?:,\s*\d{4})?)\b',
            'time': r'\b(\d{1,2}:\d{2}(?:\s*[AaPp][Mm])?|\d{1,2}\s*[AaPp][Mm])\b'
        }
        
        self.logger.info("ConflictDetector initialized with thresholds")
    
    def detect_conflicts(self, new_memory: Memory, existing_memories: List[Memory]) -> List[Conflict]:
        """
        Detect conflicts between a new memory and existing memories.
        
        Args:
            new_memory: The new memory to check
            existing_memories: List of existing memories to compare against
            
        Returns:
            List of detected conflicts
        """
        conflicts = []
        
        if not existing_memories:
            self.logger.debug("No existing memories to compare against")
            return conflicts
        
        self.logger.debug(f"Checking {len(existing_memories)} existing memories for conflicts")
        
        for existing_memory in existing_memories:
            # Skip inactive memories
            if not existing_memory.is_active:
                continue
                
            # Calculate similarity
            similarity = self.calculate_similarity(new_memory.content, existing_memory.content)
            
            # Detect different types of conflicts
            conflict = self._detect_conflict_type(new_memory, existing_memory, similarity)
            
            if conflict:
                conflicts.append(conflict)
                self.logger.debug(f"Detected {conflict.conflict_type.value} conflict with similarity {similarity:.3f}")
        
        # Sort conflicts by severity and similarity
        conflicts.sort(key=lambda c: (c.severity.value, -c.similarity_score))
        
        self.logger.info(f"Detected {len(conflicts)} conflicts for new memory")
        return conflicts
    
    def calculate_similarity(self, content1: str, content2: str) -> float:
        """
        Calculate semantic similarity between two memory contents.
        
        Args:
            content1: First memory content
            content2: Second memory content
            
        Returns:
            Similarity score between 0 and 1
        """
        if not content1 or not content2:
            return 0.0
        
        # Normalize content
        content1_norm = self._normalize_content(content1)
        content2_norm = self._normalize_content(content2)
        
        if content1_norm == content2_norm:
            return 1.0
        
        # Use difflib SequenceMatcher for basic similarity
        matcher = difflib.SequenceMatcher(None, content1_norm, content2_norm)
        base_similarity = matcher.ratio()
        
        # Enhance with entity-based similarity
        entity_similarity = self._calculate_entity_similarity(content1, content2)
        
        # Weighted combination
        final_similarity = (base_similarity * 0.7) + (entity_similarity * 0.3)
        
        self.logger.debug(f"Similarity: base={base_similarity:.3f}, entity={entity_similarity:.3f}, final={final_similarity:.3f}")
        
        return min(final_similarity, 1.0)
    
    def _detect_conflict_type(self, new_memory: Memory, existing_memory: Memory, similarity: float) -> Optional[Conflict]:
        """
        Determine the type of conflict between two memories.
        
        Args:
            new_memory: The new memory
            existing_memory: The existing memory
            similarity: Pre-calculated similarity score
            
        Returns:
            Conflict object if a conflict is detected, None otherwise
        """
        # Check for exact duplicate
        if similarity >= self.exact_duplicate_threshold:
            return self._create_conflict(
                ConflictType.EXACT_DUPLICATE,
                ConflictSeverity.LOW,
                new_memory,
                existing_memory,
                similarity,
                0.95,
                {"reason": "Nearly identical content"},
                "update_timestamp"
            )
        
        # Check for partial duplicate
        elif similarity >= self.partial_duplicate_threshold:
            # Check if it's a contradiction
            if self._is_contradiction(new_memory.content, existing_memory.content):
                return self._create_conflict(
                    ConflictType.CONTRADICTION,
                    ConflictSeverity.HIGH,
                    new_memory,
                    existing_memory,
                    similarity,
                    0.85,
                    {"reason": "Contradictory information detected"},
                    "resolve_contradiction"
                )
            else:
                # Check if it's an update
                if self._is_update(new_memory, existing_memory):
                    return self._create_conflict(
                        ConflictType.UPDATE_NEEDED,
                        ConflictSeverity.MEDIUM,
                        new_memory,
                        existing_memory,
                        similarity,
                        0.8,
                        {"reason": "Content appears to be an update"},
                        "update_memory"
                    )
                else:
                    return self._create_conflict(
                        ConflictType.MERGE_CANDIDATE,
                        ConflictSeverity.MEDIUM,
                        new_memory,
                        existing_memory,
                        similarity,
                        0.75,
                        {"reason": "Similar content that could be merged"},
                        "merge_memories"
                    )
        
        # Check for temporal overlap
        elif self._has_temporal_overlap(new_memory, existing_memory):
            return self._create_conflict(
                ConflictType.TEMPORAL_OVERLAP,
                ConflictSeverity.MEDIUM,
                new_memory,
                existing_memory,
                similarity,
                0.7,
                {"reason": "Temporal overlap detected"},
                "check_temporal_conflict"
            )
        
        # Check for related memory
        elif similarity >= self.related_memory_threshold:
            return self._create_conflict(
                ConflictType.RELATED_MEMORY,
                ConflictSeverity.LOW,
                new_memory,
                existing_memory,
                similarity,
                0.6,
                {"reason": "Related content detected"},
                "link_memories"
            )
        
        return None
    
    def _create_conflict(self, conflict_type: ConflictType, severity: ConflictSeverity,
                        new_memory: Memory, existing_memory: Memory, similarity: float,
                        confidence: float, details: Dict[str, Any], suggested_action: str) -> Conflict:
        """Create a conflict object."""
        return Conflict(
            conflict_type=conflict_type,
            severity=severity,
            new_memory=new_memory,
            existing_memory=existing_memory,
            similarity_score=similarity,
            confidence=confidence,
            details=details,
            suggested_action=suggested_action
        )
    
    def _normalize_content(self, content: str) -> str:
        """Normalize content for comparison."""
        # Convert to lowercase
        normalized = content.lower().strip()
        
        # Remove extra whitespace
        normalized = re.sub(r'\s+', ' ', normalized)
        
        # Remove common punctuation
        normalized = re.sub(r'[^\w\s]', '', normalized)
        
        return normalized
    
    def _calculate_entity_similarity(self, content1: str, content2: str) -> float:
        """Calculate similarity based on extracted entities."""
        entities1 = self._extract_entities(content1)
        entities2 = self._extract_entities(content2)
        
        if not entities1 and not entities2:
            return 0.0
        
        # Calculate overlap for each entity type
        total_similarity = 0.0
        total_types = 0
        
        for entity_type in self.entity_patterns.keys():
            set1 = set(entities1.get(entity_type, []))
            set2 = set(entities2.get(entity_type, []))
            
            if set1 or set2:
                if set1 and set2:
                    intersection = len(set1.intersection(set2))
                    union = len(set1.union(set2))
                    similarity = intersection / union if union > 0 else 0.0
                else:
                    similarity = 0.0
                
                total_similarity += similarity
                total_types += 1
        
        return total_similarity / total_types if total_types > 0 else 0.0
    
    def _extract_entities(self, content: str) -> Dict[str, List[str]]:
        """Extract entities from content using regex patterns."""
        entities = {}
        
        for entity_type, pattern in self.entity_patterns.items():
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                # Clean and normalize entity names
                cleaned_matches = [match.strip().title() for match in matches if match.strip()]
                entities[entity_type] = cleaned_matches
        
        return entities
    
    def _is_contradiction(self, content1: str, content2: str) -> bool:
        """Check if two contents contradict each other."""
        content1_lower = content1.lower()
        content2_lower = content2.lower()
        
        # Check for explicit contradictions first
        # Extract key terms and check for contradictions with them
        
        # Extract preferences with objects
        pref_match1 = re.search(r'\b(like|love|enjoy)s?\s+([a-z]+)', content1_lower)
        pref_match2 = re.search(r'\b(like|love|enjoy)s?\s+([a-z]+)', content2_lower)
        neg_pref_match1 = re.search(r'\b(don\'t|doesn\'t|never)\s+(?:like|love|enjoy)\s+([a-z]+)', content1_lower)
        neg_pref_match2 = re.search(r'\b(don\'t|doesn\'t|never)\s+(?:like|love|enjoy)\s+([a-z]+)', content2_lower)
        
        if pref_match1 and neg_pref_match2:
            if pref_match1.group(2) == neg_pref_match2.group(2):
                return True
        if pref_match2 and neg_pref_match1:
            if pref_match2.group(2) == neg_pref_match1.group(2):
                return True
        
        # Check for hate vs like
        hate_match1 = re.search(r'\b(hate|dislike)s?\s+([a-z]+)', content1_lower)
        hate_match2 = re.search(r'\b(hate|dislike)s?\s+([a-z]+)', content2_lower)
        
        if pref_match1 and hate_match2:
            if pref_match1.group(2) == hate_match2.group(2):
                return True
        if pref_match2 and hate_match1:
            if pref_match2.group(2) == hate_match1.group(2):
                return True
        
        # Simple keyword contradictions
        simple_contradictions = [
            ('married', 'single'),
            ('single', 'married'),
            ('employed', 'unemployed'),
            ('unemployed', 'employed'),
            ('likes coffee', 'doesn\'t like coffee'),
            ('loves coffee', 'hates coffee'),
        ]
        
        for phrase1, phrase2 in simple_contradictions:
            if phrase1 in content1_lower and phrase2 in content2_lower:
                return True
            if phrase2 in content1_lower and phrase1 in content2_lower:
                return True
        
        # Check employment contradictions
        work_match1 = re.search(r'\bworks?\s+at\s+([A-Za-z\s]+)', content1_lower)
        work_match2 = re.search(r'\bworks?\s+at\s+([A-Za-z\s]+)', content2_lower)
        unemployed1 = 'unemployed' in content1_lower
        unemployed2 = 'unemployed' in content2_lower
        
        if (work_match1 and unemployed2) or (work_match2 and unemployed1):
            return True
        
        # Check location contradictions  
        lives_match1 = re.search(r'\blives?\s+in\s+([A-Za-z\s]+)', content1_lower)
        lives_match2 = re.search(r'\blives?\s+in\s+([A-Za-z\s]+)', content2_lower)
        moved_match1 = re.search(r'\bmoved\s+(?:from|away)', content1_lower)
        moved_match2 = re.search(r'\bmoved\s+(?:from|away)', content2_lower)
        
        if (lives_match1 and moved_match2) or (lives_match2 and moved_match1):
            return True
        
        return False
    
    def _is_update(self, new_memory: Memory, existing_memory: Memory) -> bool:
        """Check if new memory is an update to existing memory."""
        # Check if new memory has more recent information
        if new_memory.created_at and existing_memory.created_at:
            if new_memory.created_at > existing_memory.created_at:
                # Look for update indicators
                update_indicators = [
                    'now works at', 'moved to', 'recently', 'currently',
                    'updated', 'changed', 'new', 'latest'
                ]
                
                new_content_lower = new_memory.content.lower()
                for indicator in update_indicators:
                    if indicator in new_content_lower:
                        return True
        
        return False
    
    def _has_temporal_overlap(self, new_memory: Memory, existing_memory: Memory) -> bool:
        """Check if memories have temporal overlap."""
        if not new_memory.timestamp or not existing_memory.timestamp:
            return False
        
        # Calculate time difference
        time_diff = abs((new_memory.timestamp - existing_memory.timestamp).total_seconds() / 3600)
        
        # Check if within overlap threshold
        return time_diff <= self.temporal_overlap_threshold
    
    def get_conflict_summary(self, conflicts: List[Conflict]) -> Dict[str, Any]:
        """Generate a summary of detected conflicts."""
        if not conflicts:
            return {
                'total_conflicts': 0,
                'by_type': {},
                'by_severity': {},
                'suggested_actions': []
            }
        
        # Count by type
        by_type = {}
        for conflict in conflicts:
            conflict_type = conflict.conflict_type.value
            by_type[conflict_type] = by_type.get(conflict_type, 0) + 1
        
        # Count by severity
        by_severity = {}
        for conflict in conflicts:
            severity = conflict.severity.value
            by_severity[severity] = by_severity.get(severity, 0) + 1
        
        # Get unique suggested actions
        suggested_actions = list(set(conflict.suggested_action for conflict in conflicts))
        
        return {
            'total_conflicts': len(conflicts),
            'by_type': by_type,
            'by_severity': by_severity,
            'suggested_actions': suggested_actions,
            'highest_similarity': max(conflict.similarity_score for conflict in conflicts),
            'critical_conflicts': len([c for c in conflicts if c.severity == ConflictSeverity.CRITICAL])
        }