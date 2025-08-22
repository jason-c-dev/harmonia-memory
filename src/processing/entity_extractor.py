"""
Entity extraction from memory content.
"""
import re
from typing import List, Dict, Set, Any, Optional
from dataclasses import dataclass
from datetime import datetime

from core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ExtractedEntity:
    """Extracted entity information."""
    text: str
    entity_type: str
    confidence: float
    start_position: int
    end_position: int
    context: str
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class EntityExtractor:
    """Extracts entities from memory content and establishes relationships."""
    
    def __init__(self):
        """Initialize entity extractor."""
        self.logger = logger
        
        # Enhanced entity patterns with confidence scoring
        self.entity_patterns = {
            'person': {
                'patterns': [
                    (r'\b[A-Z][a-z]{1,15}(?:\s+[A-Z][a-z]{1,15}){1,3}\b', 0.8),  # Full names
                    (r'\b(?:Mr|Mrs|Ms|Dr|Prof)\.?\s+[A-Z][a-z]+\b', 0.9),  # Titles with names
                    (r'\bI\'m\s+([A-Z][a-z]+)\b', 0.95),  # "I'm John"
                    (r'\bmy name is\s+([A-Z][a-z]+)\b', 0.95),  # "my name is Alice"
                    (r'\bcalled\s+([A-Z][a-z]+)\b', 0.7),  # "called Bob"
                ],
                'exclude': {'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday',
                           'January', 'February', 'March', 'April', 'May', 'June', 'July', 'August',
                           'September', 'October', 'November', 'December', 'Google', 'Microsoft', 'Apple'}
            },
            'organization': {
                'patterns': [
                    (r'\b[A-Z][a-zA-Z\s&]{2,30}(?:Inc|Corp|Corporation|LLC|Ltd|Co|Company)\.?\b', 0.9),
                    (r'\b(?:Google|Microsoft|Apple|Amazon|Facebook|Tesla|Netflix|Uber|Airbnb)\b', 0.95),
                    (r'\bwork(?:s|ing)?\s+(?:at|for)\s+([A-Z][a-zA-Z\s&]{2,20})\b', 0.8),
                    (r'\b([A-Z][a-zA-Z\s&]{2,20})\s+(?:company|corporation|inc)\b', 0.7),
                ],
                'exclude': set()
            },
            'location': {
                'patterns': [
                    (r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*,?\s+[A-Z]{2}\b', 0.9),  # City, State
                    (r'\blive(?:s)?\s+in\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b', 0.85),
                    (r'\bfrom\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b', 0.7),
                    (r'\b(?:San Francisco|New York|Los Angeles|Chicago|Boston|Seattle|Denver|Austin|Miami|Dallas)\b', 0.95),
                    (r'\b[A-Z][a-z]+\s+(?:Street|St|Avenue|Ave|Road|Rd|Drive|Dr|Boulevard|Blvd)\b', 0.8),
                ],
                'exclude': set()
            },
            'skill': {
                'patterns': [
                    (r'\b(?:proficient|skilled|expert|experienced)\s+(?:in|with|at)\s+([A-Za-z\s+#.]{2,20})\b', 0.9),
                    (r'\bknow(?:s)?\s+([A-Z][a-zA-Z\s+#.]{2,15})\b', 0.6),
                    (r'\bcan\s+([a-z\s]{3,20})\b', 0.5),
                    (r'\b(?:Python|JavaScript|Java|C\+\+|React|Angular|Node\.js|SQL|HTML|CSS)\b', 0.9),
                    (r'\blearning\s+([A-Za-z\s+#.]{2,20})\b', 0.7),
                ],
                'exclude': {'very', 'really', 'quite', 'pretty', 'being', 'doing', 'getting'}
            },
            'temporal': {
                'patterns': [
                    (r'\b(?:yesterday|today|tomorrow|tonight)\b', 0.95),
                    (r'\b(?:last|next|this)\s+(?:week|month|year|weekend|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\b', 0.9),
                    (r'\b\d{1,2}[:/]\d{1,2}(?:[:/]\d{2,4})?\b', 0.8),  # Times and dates
                    (r'\b\d{1,2}:\d{2}(?:\s?[ap]m)?\b', 0.85),  # Times
                    (r'\b(?:at|on|in)\s+\d{1,2}(?::\d{2})?\s?(?:am|pm)\b', 0.9),
                    (r'\b\d+\s+(?:days?|weeks?|months?|years?)\s+(?:ago|from now)\b', 0.85),
                ],
                'exclude': set()
            },
            'technology': {
                'patterns': [
                    (r'\b(?:Python|JavaScript|Java|C\+\+|C#|PHP|Ruby|Go|Rust|Swift|Kotlin)\b', 0.9),
                    (r'\b(?:React|Angular|Vue|Node\.js|Django|Flask|Spring|Laravel)\b', 0.9),
                    (r'\b(?:AWS|Azure|GCP|Docker|Kubernetes|Git|GitHub|GitLab)\b', 0.9),
                    (r'\b(?:SQL|MySQL|PostgreSQL|MongoDB|Redis|Elasticsearch)\b', 0.9),
                    (r'\b(?:AI|ML|machine learning|deep learning|neural network)\b', 0.8),
                ],
                'exclude': set()
            },
            'food': {
                'patterns': [
                    (r'\b(?:pizza|pasta|sushi|burger|sandwich|salad|soup|steak|chicken|fish)\b', 0.8),
                    (r'\b(?:Italian|Chinese|Japanese|Mexican|Indian|Thai|French|American)\s+food\b', 0.9),
                    (r'\b(?:restaurant|cafe|diner|bistro|eatery)\b', 0.7),
                    (r'\b(?:love|like|enjoy|hate|dislike)\s+([a-z\s]{3,15}food|[a-z]{3,15})\b', 0.6),
                ],
                'exclude': {'good', 'bad', 'great', 'terrible', 'nice', 'awful'}
            },
            'hobby': {
                'patterns': [
                    (r'\b(?:reading|writing|drawing|painting|photography|music|guitar|piano|singing)\b', 0.8),
                    (r'\b(?:hiking|running|cycling|swimming|yoga|dancing|cooking|gardening)\b', 0.8),
                    (r'\b(?:gaming|games|video games|board games|chess|poker)\b', 0.7),
                    (r'\bplay(?:s|ing)?\s+([a-z\s]{3,15})\b', 0.6),
                    (r'\bhobby|hobbies\b', 0.5),
                ],
                'exclude': {'music', 'games', 'video', 'board', 'very', 'really', 'quite'}
            },
            'financial': {
                'patterns': [
                    (r'\$\d{1,3}(?:,\d{3})*(?:\.\d{2})?\b', 0.9),  # Dollar amounts
                    (r'\b\d+(?:\.\d+)?%\b', 0.8),  # Percentages
                    (r'\b(?:salary|income|revenue|profit|budget|cost|price|expense)\b', 0.7),
                    (r'\b(?:million|billion|thousand|M|B|K)\b', 0.6),
                ],
                'exclude': set()
            }
        }
        
        # Relationship patterns
        self.relationship_patterns = {
            'family': [
                r'\bmy\s+(mother|father|mom|dad|sister|brother|son|daughter|wife|husband|parent|child)\b',
                r'\b(mother|father|mom|dad|sister|brother|son|daughter|wife|husband)\s+([A-Z][a-z]+)\b'
            ],
            'friend': [
                r'\bmy\s+(?:best\s+)?friend\s+([A-Z][a-z]+)\b',
                r'\bfriend(?:s)?\s+([A-Z][a-z]+(?:\s+and\s+[A-Z][a-z]+)*)\b'
            ],
            'colleague': [
                r'\bcolleague\s+([A-Z][a-z]+)\b',
                r'\bwork(?:s)?\s+with\s+([A-Z][a-z]+)\b',
                r'\bteam(?:mate)?\s+([A-Z][a-z]+)\b'
            ],
            'manager': [
                r'\bmy\s+(?:manager|boss|supervisor)\s+([A-Z][a-z]+)\b',
                r'\bmanager\s+([A-Z][a-z]+)\b'
            ]
        }
    
    def extract_entities(self, text: str, focus_types: Optional[List[str]] = None) -> List[ExtractedEntity]:
        """
        Extract entities from text.
        
        Args:
            text: Text to extract entities from
            focus_types: Optional list of entity types to focus on
            
        Returns:
            List of extracted entities
        """
        if not text or not text.strip():
            return []
        
        entities = []
        types_to_process = focus_types if focus_types else list(self.entity_patterns.keys())
        
        for entity_type in types_to_process:
            if entity_type in self.entity_patterns:
                entities.extend(self._extract_type_entities(text, entity_type))
        
        # Remove duplicates and overlaps
        entities = self._deduplicate_entities(entities)
        
        # Sort by position
        entities.sort(key=lambda e: e.start_position)
        
        self.logger.debug(f"Extracted {len(entities)} entities from text")
        return entities
    
    def _extract_type_entities(self, text: str, entity_type: str) -> List[ExtractedEntity]:
        """Extract entities of a specific type."""
        entities = []
        type_config = self.entity_patterns[entity_type]
        
        for pattern, base_confidence in type_config['patterns']:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                entity_text = match.group(1) if match.groups() else match.group(0)
                entity_text = entity_text.strip()
                
                # Skip if in exclusion list
                if entity_text in type_config['exclude']:
                    continue
                
                # Skip very short entities
                if len(entity_text) < 2:
                    continue
                
                # Calculate confidence
                confidence = self._calculate_entity_confidence(entity_text, entity_type, text, base_confidence)
                
                # Skip low confidence entities
                if confidence < 0.3:
                    continue
                
                # Extract context
                context = self._extract_context(text, match.start(), match.end())
                
                entity = ExtractedEntity(
                    text=entity_text,
                    entity_type=entity_type,
                    confidence=confidence,
                    start_position=match.start(),
                    end_position=match.end(),
                    context=context,
                    metadata={
                        'pattern_matched': pattern,
                        'extraction_method': 'regex'
                    }
                )
                entities.append(entity)
        
        return entities
    
    def _calculate_entity_confidence(self, entity_text: str, entity_type: str, 
                                   full_text: str, base_confidence: float) -> float:
        """Calculate confidence score for an entity."""
        confidence = base_confidence
        
        # Adjust based on entity length
        if len(entity_text) < 3:
            confidence *= 0.7
        elif len(entity_text) > 20:
            confidence *= 0.8
        
        # Adjust based on capitalization for names
        if entity_type in ['person', 'organization', 'location']:
            if entity_text.istitle():
                confidence *= 1.1
            elif entity_text.islower():
                confidence *= 0.7
        
        # Adjust based on context
        context_lower = full_text.lower()
        if entity_type == 'person':
            if any(indicator in context_lower for indicator in ['my name', 'i am', 'i\'m', 'called']):
                confidence *= 1.2
        elif entity_type == 'organization':
            if any(indicator in context_lower for indicator in ['work at', 'work for', 'company', 'job']):
                confidence *= 1.1
        elif entity_type == 'location':
            if any(indicator in context_lower for indicator in ['live in', 'from', 'located', 'city']):
                confidence *= 1.1
        
        return min(confidence, 1.0)
    
    def _extract_context(self, text: str, start: int, end: int, window: int = 20) -> str:
        """Extract context around an entity."""
        context_start = max(0, start - window)
        context_end = min(len(text), end + window)
        
        context = text[context_start:context_end].strip()
        
        # Add ellipsis if we truncated
        if context_start > 0:
            context = "..." + context
        if context_end < len(text):
            context = context + "..."
        
        return context
    
    def _deduplicate_entities(self, entities: List[ExtractedEntity]) -> List[ExtractedEntity]:
        """Remove duplicate and overlapping entities."""
        if not entities:
            return entities
        
        # Sort by position
        entities.sort(key=lambda e: (e.start_position, e.end_position))
        
        deduplicated = []
        for entity in entities:
            # Check for overlaps with existing entities
            overlaps = False
            for existing in deduplicated:
                if self._entities_overlap(entity, existing):
                    # Keep the entity with higher confidence
                    if entity.confidence > existing.confidence:
                        deduplicated.remove(existing)
                        break
                    else:
                        overlaps = True
                        break
            
            if not overlaps:
                deduplicated.append(entity)
        
        return deduplicated
    
    def _entities_overlap(self, entity1: ExtractedEntity, entity2: ExtractedEntity) -> bool:
        """Check if two entities overlap."""
        return not (entity1.end_position <= entity2.start_position or 
                   entity2.end_position <= entity1.start_position)
    
    def extract_relationships(self, text: str, entities: List[ExtractedEntity]) -> List[Dict[str, Any]]:
        """
        Extract relationships between entities.
        
        Args:
            text: Original text
            entities: Extracted entities
            
        Returns:
            List of relationship dictionaries
        """
        relationships = []
        
        # Extract explicit relationships using patterns
        for rel_type, patterns in self.relationship_patterns.items():
            for pattern in patterns:
                for match in re.finditer(pattern, text, re.IGNORECASE):
                    relationship = {
                        'type': rel_type,
                        'entities': [match.group(1)] if match.groups() else [],
                        'context': self._extract_context(text, match.start(), match.end()),
                        'confidence': 0.8,
                        'extraction_method': 'pattern'
                    }
                    relationships.append(relationship)
        
        # Extract implicit relationships based on proximity
        person_entities = [e for e in entities if e.entity_type == 'person']
        for i, person1 in enumerate(person_entities):
            for person2 in person_entities[i+1:]:
                # If two people are mentioned close together, they might be related
                distance = abs(person1.start_position - person2.start_position)
                if distance < 50:  # Within 50 characters
                    relationship = {
                        'type': 'mentioned_together',
                        'entities': [person1.text, person2.text],
                        'context': f"Mentioned within {distance} characters",
                        'confidence': max(0.3, 0.8 - distance/100),
                        'extraction_method': 'proximity'
                    }
                    relationships.append(relationship)
        
        return relationships
    
    def categorize_entities(self, entities: List[ExtractedEntity]) -> Dict[str, List[ExtractedEntity]]:
        """Categorize entities by type."""
        categorized = {}
        
        for entity in entities:
            if entity.entity_type not in categorized:
                categorized[entity.entity_type] = []
            categorized[entity.entity_type].append(entity)
        
        # Sort each category by confidence
        for entity_type in categorized:
            categorized[entity_type].sort(key=lambda e: e.confidence, reverse=True)
        
        return categorized
    
    def get_entity_summary(self, entities: List[ExtractedEntity]) -> Dict[str, Any]:
        """Get summary statistics about extracted entities."""
        if not entities:
            return {
                'total_entities': 0,
                'entity_types': [],
                'avg_confidence': 0.0,
                'high_confidence_count': 0
            }
        
        categorized = self.categorize_entities(entities)
        
        return {
            'total_entities': len(entities),
            'entity_types': list(categorized.keys()),
            'type_counts': {t: len(ents) for t, ents in categorized.items()},
            'avg_confidence': sum(e.confidence for e in entities) / len(entities),
            'high_confidence_count': sum(1 for e in entities if e.confidence > 0.8),
            'most_confident_entity': max(entities, key=lambda e: e.confidence).text if entities else None
        }