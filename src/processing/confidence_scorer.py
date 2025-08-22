"""
Confidence scoring for extracted memories.
"""
import math
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from prompts.types import ExtractedMemory, MemoryType
from core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ConfidenceFactors:
    """Factors contributing to confidence score."""
    llm_confidence: float
    content_quality: float
    entity_support: float
    context_relevance: float
    temporal_consistency: float
    source_reliability: float
    complexity_bonus: float
    length_penalty: float
    final_score: float


class ConfidenceScorer:
    """Scores confidence of extracted memories using multiple factors."""
    
    def __init__(self):
        """Initialize confidence scorer."""
        self.logger = logger
        
        # Memory type confidence baselines
        self.type_baselines = {
            MemoryType.PERSONAL: 0.8,      # High baseline - usually explicit
            MemoryType.FACTUAL: 0.85,      # High baseline - objective facts
            MemoryType.TEMPORAL: 0.9,      # Very high - usually specific
            MemoryType.PREFERENCE: 0.75,   # Good baseline - often clear
            MemoryType.SKILL: 0.8,         # High baseline - usually explicit
            MemoryType.EMOTIONAL: 0.7,     # Moderate - more subjective
            MemoryType.EPISODIC: 0.75,     # Good baseline - specific events
            MemoryType.RELATIONAL: 0.7,    # Moderate - can be implicit
            MemoryType.PROCEDURAL: 0.8,    # High - usually step-by-step
            MemoryType.GOAL: 0.75          # Good baseline - often explicit
        }
        
        # Quality indicators by content type
        self.quality_indicators = {
            'positive': [
                'specific names', 'exact numbers', 'precise dates', 'detailed descriptions',
                'explicit statements', 'clear relationships', 'concrete actions'
            ],
            'negative': [
                'vague terms', 'maybe', 'perhaps', 'might', 'could be', 'not sure',
                'unclear', 'ambiguous', 'contradictory'
            ]
        }
        
        # Confidence thresholds
        self.thresholds = {
            'high': 0.8,
            'medium': 0.6,
            'low': 0.4,
            'unreliable': 0.2
        }
    
    def score_memory(self, memory: ExtractedMemory, context: Dict[str, Any]) -> ConfidenceFactors:
        """
        Score confidence for a memory using multiple factors.
        
        Args:
            memory: Extracted memory to score
            context: Additional context for scoring
            
        Returns:
            ConfidenceFactors with detailed scoring breakdown
        """
        # Get baseline confidence from LLM
        llm_confidence = memory.confidence
        
        # Calculate individual factors
        content_quality = self._score_content_quality(memory, context)
        entity_support = self._score_entity_support(memory, context)
        context_relevance = self._score_context_relevance(memory, context)
        temporal_consistency = self._score_temporal_consistency(memory, context)
        source_reliability = self._score_source_reliability(memory, context)
        complexity_bonus = self._calculate_complexity_bonus(memory, context)
        length_penalty = self._calculate_length_penalty(memory)
        
        # Combine factors with weights
        final_score = self._combine_factors(
            llm_confidence=llm_confidence,
            content_quality=content_quality,
            entity_support=entity_support,
            context_relevance=context_relevance,
            temporal_consistency=temporal_consistency,
            source_reliability=source_reliability,
            complexity_bonus=complexity_bonus,
            length_penalty=length_penalty,
            memory_type=memory.memory_type
        )
        
        factors = ConfidenceFactors(
            llm_confidence=llm_confidence,
            content_quality=content_quality,
            entity_support=entity_support,
            context_relevance=context_relevance,
            temporal_consistency=temporal_consistency,
            source_reliability=source_reliability,
            complexity_bonus=complexity_bonus,
            length_penalty=length_penalty,
            final_score=final_score
        )
        
        self.logger.debug(f"Memory confidence: {final_score:.3f} (LLM: {llm_confidence:.3f})")
        return factors
    
    def _score_content_quality(self, memory: ExtractedMemory, context: Dict[str, Any]) -> float:
        """Score the quality of memory content."""
        content = memory.content.lower()
        quality_score = 0.5  # Base score
        
        # Positive quality indicators
        positive_count = 0
        for indicator in self.quality_indicators['positive']:
            if any(word in content for word in indicator.split()):
                positive_count += 1
        
        # Negative quality indicators
        negative_count = 0
        for indicator in self.quality_indicators['negative']:
            if any(word in content for word in indicator.split()):
                negative_count += 1
        
        # Adjust score based on indicators
        quality_score += positive_count * 0.1
        quality_score -= negative_count * 0.15
        
        # Check for specificity
        if memory.entities and len(memory.entities) > 0:
            quality_score += 0.1  # Bonus for having entities
        
        if memory.temporal_info:
            quality_score += 0.1  # Bonus for temporal information
        
        # Check content length and detail
        word_count = len(memory.content.split())
        if 5 <= word_count <= 20:
            quality_score += 0.1  # Optimal length
        elif word_count < 3:
            quality_score -= 0.2  # Too short
        elif word_count > 30:
            quality_score -= 0.1  # Might be too verbose
        
        return max(0.0, min(1.0, quality_score))
    
    def _score_entity_support(self, memory: ExtractedMemory, context: Dict[str, Any]) -> float:
        """Score based on entity support and recognition."""
        if not memory.entities:
            return 0.3  # Low score for no entities
        
        entity_score = 0.0
        entity_count = len(memory.entities)
        
        # Base score for having entities
        entity_score = min(0.4 + entity_count * 0.1, 0.8)
        
        # Bonus for specific entity types in context
        extracted_entities = context.get('extracted_entities', [])
        if extracted_entities:
            # Check if memory entities match extracted entities
            memory_entity_texts = [e.lower() for e in memory.entities]
            extracted_entity_texts = [e.text.lower() for e in extracted_entities]
            
            matches = sum(1 for me in memory_entity_texts 
                         if any(me in ee for ee in extracted_entity_texts))
            
            if matches > 0:
                entity_score += matches * 0.1  # Bonus for entity confirmation
        
        return min(1.0, entity_score)
    
    def _score_context_relevance(self, memory: ExtractedMemory, context: Dict[str, Any]) -> float:
        """Score relevance to original message context."""
        original_message = context.get('original_message', '').lower()
        memory_content = memory.content.lower()
        
        if not original_message:
            return 0.5  # Neutral if no context
        
        # Calculate word overlap
        message_words = set(original_message.split())
        memory_words = set(memory_content.split())
        
        if not message_words or not memory_words:
            return 0.2
        
        overlap = len(message_words.intersection(memory_words))
        overlap_ratio = overlap / len(message_words.union(memory_words))
        
        # Base score from overlap
        relevance_score = min(overlap_ratio * 2, 0.9)  # Scale up to max 0.9
        
        # Bonus for exact phrase matches
        if memory_content.strip() in original_message:
            relevance_score += 0.1
        
        return min(1.0, relevance_score)
    
    def _score_temporal_consistency(self, memory: ExtractedMemory, context: Dict[str, Any]) -> float:
        """Score temporal consistency and validity."""
        if not memory.temporal_info:
            return 0.7  # Neutral score for non-temporal memories
        
        temporal_info = memory.temporal_info.lower()
        consistency_score = 0.5
        
        # Check for specific temporal markers
        specific_markers = ['yesterday', 'today', 'tomorrow', 'monday', 'tuesday', 
                          'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
        
        if any(marker in temporal_info for marker in specific_markers):
            consistency_score += 0.3
        
        # Check for date patterns
        import re
        date_patterns = [
            r'\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4}',
            r'\d{1,2}:\d{2}',
            r'\b\d+\s+(?:days?|weeks?|months?|years?)\b'
        ]
        
        for pattern in date_patterns:
            if re.search(pattern, temporal_info):
                consistency_score += 0.2
                break
        
        return min(1.0, consistency_score)
    
    def _score_source_reliability(self, memory: ExtractedMemory, context: Dict[str, Any]) -> float:
        """Score based on source reliability factors."""
        reliability_score = 0.7  # Base reliability
        
        # Check preprocessing quality
        preprocessing_data = context.get('preprocessing_data')
        if preprocessing_data:
            # Bonus for high-quality preprocessing
            if preprocessing_data.complexity_score > 0.6:
                reliability_score += 0.1
            
            # Penalty for PII detection (might indicate confusion)
            if preprocessing_data.contains_pii:
                reliability_score -= 0.1
            
            # Bonus for good word count
            if 5 <= preprocessing_data.word_count <= 50:
                reliability_score += 0.1
        
        # Check for user context
        user_context = context.get('user_context', {})
        if user_context:
            # Bonus for established user
            if user_context.get('message_count', 0) > 10:
                reliability_score += 0.1
        
        return max(0.2, min(1.0, reliability_score))
    
    def _calculate_complexity_bonus(self, memory: ExtractedMemory, context: Dict[str, Any]) -> float:
        """Calculate bonus for memory complexity."""
        complexity_bonus = 0.0
        
        # Bonus for multiple entities
        if memory.entities and len(memory.entities) > 1:
            complexity_bonus += 0.05
        
        # Bonus for relationships
        if memory.relationships and len(memory.relationships) > 0:
            complexity_bonus += 0.05
        
        # Bonus for context information
        if memory.context and len(memory.context) > 10:
            complexity_bonus += 0.05
        
        # Bonus for temporal information
        if memory.temporal_info:
            complexity_bonus += 0.05
        
        return min(0.2, complexity_bonus)  # Cap at 0.2
    
    def _calculate_length_penalty(self, memory: ExtractedMemory) -> float:
        """Calculate penalty for inappropriate content length."""
        content_length = len(memory.content)
        word_count = len(memory.content.split())
        
        penalty = 0.0
        
        # Penalty for very short content (likely incomplete)
        if word_count < 3:
            penalty += 0.2
        elif word_count < 5:
            penalty += 0.1
        
        # Penalty for very long content (likely too verbose)
        if word_count > 40:
            penalty += 0.1
        elif word_count > 60:
            penalty += 0.2
        
        # Penalty for character length issues
        if content_length < 10:
            penalty += 0.1
        elif content_length > 300:
            penalty += 0.1
        
        return min(0.4, penalty)  # Cap penalty at 0.4
    
    def _combine_factors(self, llm_confidence: float, content_quality: float,
                        entity_support: float, context_relevance: float,
                        temporal_consistency: float, source_reliability: float,
                        complexity_bonus: float, length_penalty: float,
                        memory_type: MemoryType) -> float:
        """Combine all factors into final confidence score."""
        
        # Get type-specific baseline
        type_baseline = self.type_baselines.get(memory_type, 0.7)
        
        # Weighted combination of factors
        weights = {
            'llm_confidence': 0.3,
            'content_quality': 0.2,
            'entity_support': 0.15,
            'context_relevance': 0.15,
            'temporal_consistency': 0.1,
            'source_reliability': 0.1
        }
        
        weighted_score = (
            llm_confidence * weights['llm_confidence'] +
            content_quality * weights['content_quality'] +
            entity_support * weights['entity_support'] +
            context_relevance * weights['context_relevance'] +
            temporal_consistency * weights['temporal_consistency'] +
            source_reliability * weights['source_reliability']
        )
        
        # Apply type baseline influence (20% weight)
        final_score = weighted_score * 0.8 + type_baseline * 0.2
        
        # Apply complexity bonus
        final_score += complexity_bonus
        
        # Apply length penalty
        final_score -= length_penalty
        
        # Ensure score is in valid range
        final_score = max(0.0, min(1.0, final_score))
        
        return final_score
    
    def score_multiple_memories(self, memories: List[ExtractedMemory], 
                              context: Dict[str, Any]) -> List[ConfidenceFactors]:
        """Score multiple memories and return sorted by confidence."""
        scored_memories = []
        
        for memory in memories:
            factors = self.score_memory(memory, context)
            scored_memories.append(factors)
        
        # Sort by final confidence score
        scored_memories.sort(key=lambda f: f.final_score, reverse=True)
        
        return scored_memories
    
    def filter_by_threshold(self, scored_memories: List[ConfidenceFactors], 
                           threshold: float = 0.6) -> List[ConfidenceFactors]:
        """Filter memories by confidence threshold."""
        return [factors for factors in scored_memories if factors.final_score >= threshold]
    
    def get_confidence_level(self, score: float) -> str:
        """Get confidence level description."""
        if score >= self.thresholds['high']:
            return 'high'
        elif score >= self.thresholds['medium']:
            return 'medium'
        elif score >= self.thresholds['low']:
            return 'low'
        else:
            return 'unreliable'
    
    def get_scoring_summary(self, scored_memories: List[ConfidenceFactors]) -> Dict[str, Any]:
        """Get summary statistics for scored memories."""
        if not scored_memories:
            return {
                'total_memories': 0,
                'avg_confidence': 0.0,
                'confidence_distribution': {},
                'high_confidence_count': 0
            }
        
        scores = [f.final_score for f in scored_memories]
        
        # Calculate distribution
        distribution = {
            'high': sum(1 for s in scores if s >= self.thresholds['high']),
            'medium': sum(1 for s in scores if self.thresholds['medium'] <= s < self.thresholds['high']),
            'low': sum(1 for s in scores if self.thresholds['low'] <= s < self.thresholds['medium']),
            'unreliable': sum(1 for s in scores if s < self.thresholds['low'])
        }
        
        return {
            'total_memories': len(scored_memories),
            'avg_confidence': sum(scores) / len(scores),
            'max_confidence': max(scores),
            'min_confidence': min(scores),
            'confidence_distribution': distribution,
            'high_confidence_count': distribution['high'],
            'reliable_count': distribution['high'] + distribution['medium']
        }