"""
Message preprocessing for memory extraction.
"""
import re
import string
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass

from core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class PreprocessedMessage:
    """Preprocessed message data."""
    original_text: str
    cleaned_text: str
    word_count: int
    char_count: int
    language: str
    entities_detected: List[str]
    contains_pii: bool
    sentiment_indicators: Dict[str, float]
    temporal_markers: List[str]
    complexity_score: float
    preprocessing_metadata: Dict[str, Any]


class MessagePreprocessor:
    """Preprocesses user messages for memory extraction."""
    
    def __init__(self):
        """Initialize message preprocessor."""
        self.logger = logger
        
        # Common PII patterns
        self.pii_patterns = {
            'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            'phone': r'\b(?:\+?1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b',
            'ssn': r'\b\d{3}-?\d{2}-?\d{4}\b',
            'credit_card': r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b'
        }
        
        # Temporal markers
        self.temporal_patterns = [
            r'\b(?:yesterday|today|tomorrow|tonight)\b',
            r'\b(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b',
            r'\b(?:january|february|march|april|may|june|july|august|september|october|november|december)\b',
            r'\b\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4}\b',
            r'\b\d{1,2}:\d{2}(?:\s?[ap]m)?\b',
            r'\b(?:last|next|this)\s+(?:week|month|year|weekend)\b',
            r'\b\d+\s+(?:days?|weeks?|months?|years?)\s+(?:ago|from now)\b'
        ]
        
        # Sentiment indicators
        self.positive_words = {
            'love', 'like', 'enjoy', 'happy', 'excited', 'amazing', 'great', 'wonderful',
            'fantastic', 'excellent', 'awesome', 'brilliant', 'perfect', 'beautiful'
        }
        
        self.negative_words = {
            'hate', 'dislike', 'angry', 'sad', 'frustrated', 'terrible', 'awful',
            'horrible', 'disgusting', 'annoying', 'boring', 'stupid', 'worst'
        }
        
        # Entity patterns
        self.entity_patterns = {
            'person': r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b',
            'organization': r'\b[A-Z][a-zA-Z]*(?:\s+[A-Z][a-zA-Z]*)*(?:\s+(?:Inc|Corp|LLC|Ltd|Co)\.?)\b',
            'location': r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*(?:\s+(?:Street|St|Avenue|Ave|Road|Rd|Drive|Dr|Boulevard|Blvd|City|State))\b',
            'money': r'\$\d+(?:,\d{3})*(?:\.\d{2})?',
            'percentage': r'\d+(?:\.\d+)?%',
            'number': r'\b\d+(?:,\d{3})*(?:\.\d+)?\b'
        }
    
    def preprocess(self, message_text: str, user_context: Optional[Dict[str, Any]] = None) -> PreprocessedMessage:
        """
        Preprocess a message for memory extraction.
        
        Args:
            message_text: Raw message text
            user_context: Optional user context for personalized preprocessing
            
        Returns:
            PreprocessedMessage with analysis results
        """
        if not message_text or not message_text.strip():
            return self._create_empty_result(message_text)
        
        original_text = message_text
        
        # Basic cleaning
        cleaned_text = self._clean_text(message_text)
        
        # Calculate basic metrics
        word_count = len(cleaned_text.split())
        char_count = len(cleaned_text)
        
        # Detect language (simple heuristic)
        language = self._detect_language(cleaned_text)
        
        # Extract entities
        entities_detected = self._extract_entities(cleaned_text)
        
        # Check for PII
        contains_pii = self._detect_pii(cleaned_text)
        
        # Analyze sentiment indicators
        sentiment_indicators = self._analyze_sentiment(cleaned_text)
        
        # Find temporal markers
        temporal_markers = self._find_temporal_markers(cleaned_text)
        
        # Calculate complexity score
        complexity_score = self._calculate_complexity(cleaned_text, word_count, entities_detected)
        
        # Metadata
        preprocessing_metadata = {
            'processed_at': datetime.now().isoformat(),
            'has_user_context': user_context is not None,
            'preprocessing_version': '1.0'
        }
        
        result = PreprocessedMessage(
            original_text=original_text,
            cleaned_text=cleaned_text,
            word_count=word_count,
            char_count=char_count,
            language=language,
            entities_detected=entities_detected,
            contains_pii=contains_pii,
            sentiment_indicators=sentiment_indicators,
            temporal_markers=temporal_markers,
            complexity_score=complexity_score,
            preprocessing_metadata=preprocessing_metadata
        )
        
        self.logger.debug(f"Preprocessed message: {word_count} words, complexity: {complexity_score:.2f}")
        return result
    
    def _create_empty_result(self, original_text: str) -> PreprocessedMessage:
        """Create result for empty or invalid messages."""
        return PreprocessedMessage(
            original_text=original_text or "",
            cleaned_text="",
            word_count=0,
            char_count=0,
            language="unknown",
            entities_detected=[],
            contains_pii=False,
            sentiment_indicators={'positive': 0.0, 'negative': 0.0, 'neutral': 1.0},
            temporal_markers=[],
            complexity_score=0.0,
            preprocessing_metadata={
                'processed_at': datetime.now().isoformat(),
                'has_user_context': False,
                'preprocessing_version': '1.0',
                'empty_message': True
            }
        )
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text."""
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text.strip())
        
        # Normalize quotes
        text = re.sub(r'[""''`]', '"', text)
        
        # Remove excessive punctuation
        text = re.sub(r'[!]{2,}', '!', text)
        text = re.sub(r'[?]{2,}', '?', text)
        text = re.sub(r'[.]{3,}', '...', text)
        
        return text
    
    def _detect_language(self, text: str) -> str:
        """Detect language using simple heuristics."""
        # Very basic language detection - in production, use proper library
        if not text:
            return "unknown"
        
        # Count ASCII vs non-ASCII characters
        ascii_chars = sum(1 for c in text if ord(c) < 128)
        total_chars = len(text)
        
        if total_chars == 0:
            return "unknown"
        
        ascii_ratio = ascii_chars / total_chars
        
        if ascii_ratio > 0.9:
            return "en"  # Likely English
        else:
            return "other"  # Non-English
    
    def _extract_entities(self, text: str) -> List[str]:
        """Extract basic entities from text."""
        entities = []
        
        for entity_type, pattern in self.entity_patterns.items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                entities.append(f"{entity_type}:{match}")
        
        return entities
    
    def _detect_pii(self, text: str) -> bool:
        """Detect potential PII in text."""
        for pii_type, pattern in self.pii_patterns.items():
            if re.search(pattern, text, re.IGNORECASE):
                self.logger.warning(f"Potential PII detected: {pii_type}")
                return True
        return False
    
    def _analyze_sentiment(self, text: str) -> Dict[str, float]:
        """Analyze sentiment indicators in text."""
        words = set(text.lower().split())
        
        positive_count = len(words.intersection(self.positive_words))
        negative_count = len(words.intersection(self.negative_words))
        total_sentiment_words = positive_count + negative_count
        
        if total_sentiment_words == 0:
            return {'positive': 0.0, 'negative': 0.0, 'neutral': 1.0}
        
        positive_ratio = positive_count / total_sentiment_words
        negative_ratio = negative_count / total_sentiment_words
        neutral_ratio = 1.0 - (positive_ratio + negative_ratio)
        
        return {
            'positive': positive_ratio,
            'negative': negative_ratio, 
            'neutral': max(0.0, neutral_ratio)
        }
    
    def _find_temporal_markers(self, text: str) -> List[str]:
        """Find temporal markers in text."""
        markers = []
        
        for pattern in self.temporal_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            markers.extend(matches)
        
        return list(set(markers))  # Remove duplicates
    
    def _calculate_complexity(self, text: str, word_count: int, entities: List[str]) -> float:
        """Calculate message complexity score (0.0 - 1.0)."""
        if word_count == 0:
            return 0.0
        
        # Factors contributing to complexity
        avg_word_length = sum(len(word) for word in text.split()) / word_count
        entity_density = len(entities) / word_count
        punctuation_density = sum(1 for c in text if c in string.punctuation) / len(text)
        
        # Normalize and combine factors
        word_length_score = min(avg_word_length / 10.0, 1.0)  # Normalize to 0-1
        entity_score = min(entity_density * 5.0, 1.0)  # Scale entity density
        punctuation_score = min(punctuation_density * 10.0, 1.0)  # Scale punctuation
        
        # Weighted combination
        complexity = (
            word_length_score * 0.3 +
            entity_score * 0.4 +
            punctuation_score * 0.3
        )
        
        return min(complexity, 1.0)
    
    def should_extract_memories(self, preprocessed: PreprocessedMessage) -> bool:
        """
        Determine if message should undergo memory extraction.
        
        Args:
            preprocessed: Preprocessed message data
            
        Returns:
            True if message is suitable for memory extraction
        """
        # Skip empty messages
        if preprocessed.word_count == 0:
            return False
        
        # Skip very short messages (likely greetings or responses)
        if preprocessed.word_count < 3:
            return False
        
        # Skip messages that are mostly punctuation
        if preprocessed.char_count > 0:
            punctuation_ratio = sum(1 for c in preprocessed.cleaned_text if c in string.punctuation) / preprocessed.char_count
            if punctuation_ratio > 0.5:
                return False
        
        # Skip messages with very low complexity (likely simple responses)
        if preprocessed.complexity_score < 0.1:
            return False
        
        return True
    
    def get_extraction_hints(self, preprocessed: PreprocessedMessage) -> Dict[str, Any]:
        """
        Get hints for memory extraction based on preprocessing results.
        
        Args:
            preprocessed: Preprocessed message data
            
        Returns:
            Dictionary of extraction hints
        """
        hints = {
            'suggested_memory_types': [],
            'extraction_mode': 'moderate',
            'focus_areas': [],
            'confidence_adjustment': 0.0
        }
        
        # Suggest memory types based on content
        if preprocessed.temporal_markers:
            hints['suggested_memory_types'].append('temporal')
        
        if preprocessed.sentiment_indicators['positive'] > 0.3 or preprocessed.sentiment_indicators['negative'] > 0.3:
            hints['suggested_memory_types'].append('emotional')
            hints['suggested_memory_types'].append('preference')
        
        if any('person:' in entity for entity in preprocessed.entities_detected):
            hints['suggested_memory_types'].append('relational')
        
        if preprocessed.complexity_score > 0.7:
            hints['suggested_memory_types'].extend(['factual', 'procedural'])
        
        # Adjust extraction mode based on complexity
        if preprocessed.complexity_score > 0.8:
            hints['extraction_mode'] = 'permissive'
        elif preprocessed.complexity_score < 0.3:
            hints['extraction_mode'] = 'strict'
        
        # Focus areas
        if preprocessed.contains_pii:
            hints['focus_areas'].append('handle_pii_carefully')
        
        if preprocessed.temporal_markers:
            hints['focus_areas'].append('temporal_information')
        
        if preprocessed.entities_detected:
            hints['focus_areas'].append('entity_relationships')
        
        # Confidence adjustments
        if preprocessed.word_count < 5:
            hints['confidence_adjustment'] = -0.1  # Lower confidence for very short messages
        elif preprocessed.complexity_score > 0.8:
            hints['confidence_adjustment'] = 0.1   # Higher confidence for complex messages
        
        return hints