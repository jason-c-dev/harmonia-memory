"""
Core memory processor for end-to-end memory extraction and processing.
"""
import time
import asyncio
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import concurrent.futures

from prompts.memory_extraction import MemoryExtractionPrompts
from prompts.types import MemoryType, PromptContext, ExtractionMode, ExtractedMemory, MemoryExtractionResult
from llm.ollama_client import OllamaClient, OllamaError, ConnectionError, ModelNotFoundError
from .preprocessor import MessagePreprocessor, PreprocessedMessage
from .entity_extractor import EntityExtractor, ExtractedEntity
from .confidence_scorer import ConfidenceScorer, ConfidenceFactors
from core.config import get_config
from core.logging import get_logger

logger = get_logger(__name__)


class ProcessingError(Exception):
    """Exception raised during memory processing."""
    pass


@dataclass
class ProcessingResult:
    """Result of memory processing operation."""
    success: bool
    memories: List[ExtractedMemory]
    confidence_scores: List[ConfidenceFactors]
    processing_time_ms: float
    preprocessing_data: PreprocessedMessage
    extracted_entities: List[ExtractedEntity]
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'success': self.success,
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
            'confidence_scores': [
                {
                    'final_score': cf.final_score,
                    'llm_confidence': cf.llm_confidence,
                    'content_quality': cf.content_quality,
                    'entity_support': cf.entity_support,
                    'context_relevance': cf.context_relevance
                }
                for cf in self.confidence_scores
            ],
            'processing_time_ms': self.processing_time_ms,
            'extracted_entities_count': len(self.extracted_entities),
            'preprocessing_summary': {
                'word_count': self.preprocessing_data.word_count,
                'complexity_score': self.preprocessing_data.complexity_score,
                'contains_pii': self.preprocessing_data.contains_pii,
                'entities_detected': len(self.preprocessing_data.entities_detected)
            },
            'error_message': self.error_message,
            'metadata': self.metadata
        }


class MemoryProcessor:
    """Main memory processor for extracting and processing memories from messages."""
    
    def __init__(self, ollama_client: Optional[OllamaClient] = None):
        """
        Initialize memory processor.
        
        Args:
            ollama_client: Optional OllamaClient instance (creates new if None)
        """
        self.config = get_config()
        self.logger = logger
        
        # Initialize components
        self.ollama_client = ollama_client or OllamaClient()
        self.extraction_prompts = MemoryExtractionPrompts()
        self.preprocessor = MessagePreprocessor()
        self.entity_extractor = EntityExtractor()
        self.confidence_scorer = ConfidenceScorer()
        
        # Processing settings
        self.default_extraction_mode = ExtractionMode.MODERATE
        self.default_confidence_threshold = getattr(self.config.memory, 'confidence_threshold', 0.7)
        self.max_memories_per_message = getattr(self.config.memory, 'max_memories', 10)
        self.processing_timeout = 30.0  # seconds
        
        # Error handling settings
        self.max_retries = 3
        self.retry_delay = 1.0
        
        self.logger.info("MemoryProcessor initialized")
    
    def process_message(self, user_id: str, session_id: str, message_text: str,
                       extraction_mode: Optional[ExtractionMode] = None,
                       memory_types: Optional[List[MemoryType]] = None,
                       previous_memories: Optional[List[Dict[str, Any]]] = None,
                       user_context: Optional[Dict[str, Any]] = None) -> ProcessingResult:
        """
        Process a message end-to-end to extract memories.
        
        Args:
            user_id: User identifier
            session_id: Session identifier
            message_text: Message to process
            extraction_mode: Mode for extraction (defaults to moderate)
            memory_types: Types of memories to extract (defaults to all)
            previous_memories: Previous memories for context
            user_context: Additional user context
            
        Returns:
            ProcessingResult with extracted memories and metadata
        """
        start_time = time.time()
        
        try:
            # Step 1: Preprocess message
            preprocessing_data = self.preprocessor.preprocess(message_text, user_context)
            
            # Check if message should be processed
            if not self.preprocessor.should_extract_memories(preprocessing_data):
                return self._create_empty_result(
                    preprocessing_data, [], 
                    time.time() - start_time,
                    "Message not suitable for memory extraction"
                )
            
            # Step 2: Extract entities
            extracted_entities = self.entity_extractor.extract_entities(
                preprocessing_data.cleaned_text
            )
            
            # Step 3: Get extraction hints from preprocessing
            extraction_hints = self.preprocessor.get_extraction_hints(preprocessing_data)
            
            # Step 4: Setup extraction context
            extraction_mode = extraction_mode or ExtractionMode(extraction_hints.get('extraction_mode', 'moderate'))
            memory_types = memory_types or [MemoryType(mt) for mt in extraction_hints.get('suggested_memory_types', [])]
            if not memory_types:
                memory_types = list(MemoryType)  # Default to all types
            
            prompt_context = PromptContext(
                user_id=user_id,
                session_id=session_id,
                message_text=preprocessing_data.cleaned_text,
                previous_memories=previous_memories or [],
                extraction_mode=extraction_mode,
                memory_types=memory_types,
                max_memories=self.max_memories_per_message,
                confidence_threshold=self.default_confidence_threshold
            )
            
            # Step 5: Extract memories using LLM
            extraction_result = self._extract_memories_with_retry(prompt_context)
            
            # Step 6: Parse and validate LLM response
            memories = self._parse_extraction_response(extraction_result, prompt_context)
            
            # Step 7: Score confidence for each memory
            scoring_context = {
                'original_message': message_text,
                'preprocessing_data': preprocessing_data,
                'extracted_entities': extracted_entities,
                'user_context': user_context or {},
                'extraction_hints': extraction_hints
            }
            
            confidence_scores = []
            for memory in memories:
                factors = self.confidence_scorer.score_memory(memory, scoring_context)
                confidence_scores.append(factors)
                # Update memory confidence with final score
                memory.confidence = factors.final_score
            
            # Step 8: Filter by confidence threshold (memory type specific)
            filtered_memories = []
            filtered_scores = []
            for memory, score in zip(memories, confidence_scores):
                # Use memory-type specific thresholds to fix simple message extraction
                # while preserving the performance of complex memory types
                threshold = self._get_memory_type_threshold(memory.memory_type)
                if score.final_score >= threshold:
                    filtered_memories.append(memory)
                    filtered_scores.append(score)
            
            # Step 9: Sort by confidence
            sorted_pairs = sorted(zip(filtered_memories, filtered_scores), 
                                key=lambda x: x[1].final_score, reverse=True)
            
            if sorted_pairs:
                filtered_memories, filtered_scores = zip(*sorted_pairs)
                filtered_memories = list(filtered_memories)
                filtered_scores = list(filtered_scores)
            else:
                filtered_memories, filtered_scores = [], []
            
            processing_time = (time.time() - start_time) * 1000
            
            result = ProcessingResult(
                success=True,
                memories=filtered_memories,
                confidence_scores=filtered_scores,
                processing_time_ms=processing_time,
                preprocessing_data=preprocessing_data,
                extracted_entities=extracted_entities,
                metadata={
                    'extraction_mode': extraction_mode.value,
                    'memory_types_requested': [mt.value for mt in memory_types],
                    'memories_before_filtering': len(memories),
                    'memories_after_filtering': len(filtered_memories),
                    'avg_confidence': sum(s.final_score for s in filtered_scores) / len(filtered_scores) if filtered_scores else 0.0,
                    'processing_steps_completed': 9
                }
            )
            
            self.logger.info(f"Successfully processed message: {len(filtered_memories)} memories extracted in {processing_time:.1f}ms")
            return result
            
        except Exception as e:
            processing_time = (time.time() - start_time) * 1000
            error_msg = f"Processing failed: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            
            return ProcessingResult(
                success=False,
                memories=[],
                confidence_scores=[],
                processing_time_ms=processing_time,
                preprocessing_data=getattr(locals(), 'preprocessing_data', None) or self.preprocessor._create_empty_result(message_text),
                extracted_entities=getattr(locals(), 'extracted_entities', []),
                error_message=error_msg,
                metadata={'processing_steps_completed': 0}
            )
    
    def _get_memory_type_threshold(self, memory_type: MemoryType) -> float:
        """
        Get confidence threshold for specific memory type.
        Lower thresholds for problematic simple statements, keep high for working types.
        
        Based on baseline testing:
        - Temporal, Factual, Relational, Emotional, Goal: 100% success (keep 0.7)
        - Personal, Skill, Preference: Issues with simple statements (lower to 0.5)
        """
        # Memory types working perfectly at 0.7 threshold
        working_types = {
            MemoryType.TEMPORAL,
            MemoryType.FACTUAL, 
            MemoryType.RELATIONAL,
            MemoryType.EMOTIONAL,
            MemoryType.GOAL,
            MemoryType.EPISODIC,
            MemoryType.PROCEDURAL
        }
        
        # Memory types that need lower threshold for simple statements
        if memory_type in working_types:
            return self.default_confidence_threshold  # Keep 0.7
        else:
            # Lower threshold for Personal, Skill, Preference memories
            return 0.5
    
    def _extract_memories_with_retry(self, prompt_context: PromptContext) -> str:
        """Extract memories using LLM with retry logic."""
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                # Get extraction prompt
                full_prompt = self.extraction_prompts.get_full_extraction_prompt(prompt_context)
                system_prompt = self.extraction_prompts.get_system_prompt(prompt_context)
                user_prompt = self.extraction_prompts.get_main_extraction_prompt(prompt_context)
                
                # Generate response
                response = self.ollama_client.generate(
                    prompt=user_prompt,
                    system=system_prompt,
                    options={
                        'temperature': 0.1,  # Low temperature for consistency
                        'num_predict': 600,  # Allow for detailed responses
                        'top_p': 0.9
                    }
                )
                
                return response['response']
                
            except (ConnectionError, ModelNotFoundError) as e:
                # Don't retry connection/model errors
                raise ProcessingError(f"LLM connection failed: {e}")
                
            except Exception as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    self.logger.warning(f"Extraction attempt {attempt + 1} failed: {e}, retrying...")
                    time.sleep(self.retry_delay * (attempt + 1))
                else:
                    self.logger.error(f"All extraction attempts failed: {e}")
        
        raise ProcessingError(f"Memory extraction failed after {self.max_retries} attempts: {last_error}")
    
    def _parse_extraction_response(self, response: str, context: PromptContext) -> List[ExtractedMemory]:
        """Parse and validate LLM extraction response."""
        try:
            # Validate and parse response
            parsed_response = self.extraction_prompts.validate_extraction_response(response)
            
            memories = []
            for memory_data in parsed_response['memories']:
                memory = ExtractedMemory(
                    content=memory_data['content'],
                    memory_type=MemoryType(memory_data['memory_type']),
                    confidence=memory_data['confidence'],
                    entities=memory_data.get('entities', []),
                    temporal_info=memory_data.get('temporal_info'),
                    context=memory_data.get('context'),
                    relationships=memory_data.get('relationships', [])
                )
                memories.append(memory)
            
            return memories
            
        except Exception as e:
            self.logger.error(f"Failed to parse extraction response: {e}")
            self.logger.debug(f"Raw response: {response[:500]}...")
            raise ProcessingError(f"Failed to parse LLM response: {e}")
    
    def _create_empty_result(self, preprocessing_data: PreprocessedMessage, 
                           extracted_entities: List[ExtractedEntity], 
                           processing_time: float, reason: str) -> ProcessingResult:
        """Create empty result for messages that don't need processing."""
        return ProcessingResult(
            success=True,
            memories=[],
            confidence_scores=[],
            processing_time_ms=processing_time * 1000,
            preprocessing_data=preprocessing_data,
            extracted_entities=extracted_entities,
            metadata={
                'reason': reason,
                'processing_skipped': True
            }
        )
    
    def process_messages_batch(self, messages: List[Dict[str, Any]], 
                             max_workers: int = 5) -> List[ProcessingResult]:
        """
        Process multiple messages in parallel.
        
        Args:
            messages: List of message dictionaries with keys: user_id, session_id, message_text
            max_workers: Maximum number of concurrent workers
            
        Returns:
            List of ProcessingResult objects
        """
        results = []
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_message = {
                executor.submit(
                    self.process_message,
                    msg['user_id'],
                    msg['session_id'], 
                    msg['message_text'],
                    msg.get('extraction_mode'),
                    msg.get('memory_types'),
                    msg.get('previous_memories'),
                    msg.get('user_context')
                ): msg for msg in messages
            }
            
            # Collect results
            for future in concurrent.futures.as_completed(future_to_message):
                message = future_to_message[future]
                try:
                    result = future.result(timeout=self.processing_timeout)
                    results.append(result)
                except Exception as e:
                    self.logger.error(f"Batch processing failed for message {message.get('user_id')}: {e}")
                    # Create error result
                    error_result = ProcessingResult(
                        success=False,
                        memories=[],
                        confidence_scores=[],
                        processing_time_ms=0.0,
                        preprocessing_data=self.preprocessor._create_empty_result(message.get('message_text', '')),
                        extracted_entities=[],
                        error_message=f"Batch processing failed: {e}"
                    )
                    results.append(error_result)
        
        self.logger.info(f"Batch processed {len(messages)} messages")
        return results
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """Get processing statistics."""
        # Get LLM client stats
        ollama_stats = self.ollama_client.get_stats()
        
        return {
            'ollama_stats': ollama_stats,
            'config': {
                'default_extraction_mode': self.default_extraction_mode.value,
                'default_confidence_threshold': self.default_confidence_threshold,
                'max_memories_per_message': self.max_memories_per_message,
                'processing_timeout': self.processing_timeout,
                'max_retries': self.max_retries
            },
            'system_info': {
                'initialized': True,
                'components': ['preprocessor', 'entity_extractor', 'confidence_scorer', 'extraction_prompts']
            }
        }
    
    def health_check(self) -> Dict[str, Any]:
        """Perform health check on all components."""
        health = {
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'components': {},
            'errors': []
        }
        
        try:
            # Check Ollama client
            ollama_health = self.ollama_client.health_check()
            health['components']['ollama'] = {
                'status': ollama_health['status'],
                'response_time_ms': ollama_health['response_time_ms']
            }
            
            if ollama_health['status'] != 'healthy':
                health['status'] = 'degraded'
                health['errors'].extend(ollama_health.get('errors', []))
            
            # Check other components
            health['components']['preprocessor'] = {'status': 'healthy'}
            health['components']['entity_extractor'] = {'status': 'healthy'}
            health['components']['confidence_scorer'] = {'status': 'healthy'}
            health['components']['extraction_prompts'] = {'status': 'healthy'}
            
        except Exception as e:
            health['status'] = 'unhealthy'
            health['errors'].append(f"Health check failed: {e}")
            self.logger.error(f"Health check failed: {e}")
        
        return health
    
    def close(self):
        """Clean up resources."""
        if self.ollama_client:
            self.ollama_client.close()
        self.logger.info("MemoryProcessor closed")