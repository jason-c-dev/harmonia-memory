"""
Memory Manager - Core CRUD operations with conflict resolution and validation.

This module provides the main interface for memory operations, integrating:
- Database CRUD operations
- Conflict detection and resolution
- Memory validation
- Caching and performance optimization
- Batch processing
- Transaction management
"""
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional, Union, Tuple
from dataclasses import dataclass, field
from enum import Enum

from models.memory import Memory
from db.manager import DatabaseManager, DatabaseError
from processing.conflict_detector import ConflictDetector, Conflict
from processing.conflict_resolver import ConflictResolver, Resolution, ResolutionAction, UserPreferences
from processing.temporal_resolver import TemporalResolver
from processing.memory_processor import MemoryProcessor, ProcessingResult
from core.logging import get_logger

logger = get_logger(__name__)


class MemoryOperationError(Exception):
    """Base exception for memory operations."""
    pass


class ValidationError(MemoryOperationError):
    """Exception for memory validation failures."""
    pass


class ConflictError(MemoryOperationError):
    """Exception for unresolvable conflicts."""
    pass


class StorageResult(Enum):
    """Result types for memory storage operations."""
    CREATED = "created"
    UPDATED = "updated" 
    MERGED = "merged"
    REPLACED = "replaced"
    CONFLICT_DETECTED = "conflict_detected"
    NO_CHANGE = "no_change"
    BATCH_CREATED = "batch_created"
    ERROR = "error"


@dataclass
class MemoryOperationResult:
    """Result of a memory operation."""
    result: StorageResult
    memory: Optional[Memory] = None
    affected_memories: List[Memory] = field(default_factory=list)
    conflicts_resolved: List[Resolution] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            'result': self.result.value,
            'memory': self.memory.to_dict() if self.memory else None,
            'affected_memory_ids': [m.memory_id for m in self.affected_memories],
            'conflicts_resolved': len(self.conflicts_resolved),
            'resolution_details': [r.to_dict() for r in self.conflicts_resolved],
            'metadata': self.metadata,
            'error_message': self.error_message
        }


@dataclass 
class BatchOperationResult:
    """Result of batch memory operations."""
    total_operations: int
    successful_operations: int
    failed_operations: int
    results: List[MemoryOperationResult] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_operations == 0:
            return 1.0
        return self.successful_operations / self.total_operations
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            'total_operations': self.total_operations,
            'successful_operations': self.successful_operations,
            'failed_operations': self.failed_operations,
            'success_rate': self.success_rate,
            'results': [r.to_dict() for r in self.results],
            'errors': self.errors
        }


class MemoryManager:
    """
    Core memory management system with CRUD operations, conflict resolution, and validation.
    
    This class provides the main interface for memory operations, combining:
    - Database CRUD operations via DatabaseManager
    - Conflict detection and resolution
    - Memory validation and normalization
    - Batch processing capabilities
    - Transaction management
    """
    
    def __init__(self, db_manager: Optional[DatabaseManager] = None,
                 conflict_detector: Optional[ConflictDetector] = None,
                 conflict_resolver: Optional[ConflictResolver] = None,
                 temporal_resolver: Optional[TemporalResolver] = None,
                 memory_processor: Optional[MemoryProcessor] = None):
        """
        Initialize MemoryManager.
        
        Args:
            db_manager: Database manager instance (creates new if None)
            conflict_detector: Conflict detector instance (creates new if None)
            conflict_resolver: Conflict resolver instance (creates new if None)
            temporal_resolver: Temporal resolver instance (creates new if None)
            memory_processor: Memory processor for LLM extraction (creates new if None)
        """
        self.db_manager = db_manager or DatabaseManager()
        self.conflict_detector = conflict_detector or ConflictDetector()
        self.conflict_resolver = conflict_resolver or ConflictResolver()
        self.temporal_resolver = temporal_resolver or TemporalResolver()
        self.memory_processor = memory_processor or MemoryProcessor()
        
        # Performance tracking
        self._operation_count = 0
        self._error_count = 0
        
        logger.info("MemoryManager initialized")
    
    def validate_memory(self, memory: Memory) -> None:
        """
        Validate memory object.
        
        Args:
            memory: Memory object to validate
            
        Raises:
            ValidationError: If validation fails
        """
        try:
            # Memory object already validates fields in its constructor,
            # but we can add additional business logic validation here
            
            # Additional business rule validations (beyond model validation)
            if memory.content and len(memory.content.strip()) == 0:
                raise ValidationError("content cannot be only whitespace")
                
        except ValidationError:
            raise
        except Exception as e:
            raise ValidationError(f"Validation error: {e}")
    
    def store_memory(self, memory: Memory, user_preferences: Optional[UserPreferences] = None,
                    detect_conflicts: bool = True) -> MemoryOperationResult:
        """
        Store a memory with conflict detection and resolution.
        
        Args:
            memory: Memory object to store
            user_preferences: User preferences for conflict resolution
            detect_conflicts: Whether to perform conflict detection
            
        Returns:
            MemoryOperationResult with operation details
            
        Raises:
            MemoryOperationError: If operation fails
        """
        try:
            self._operation_count += 1
            
            # Validate memory
            self.validate_memory(memory)
            
            # Ensure user exists (auto-create if needed)
            self._ensure_user_exists(memory.user_id)
            
            # Check if memory already exists
            existing = self.get_memory(memory.memory_id)
            if existing:
                logger.warning(f"Memory {memory.memory_id} already exists")
                return MemoryOperationResult(
                    result=StorageResult.ERROR,
                    error_message="Memory with this ID already exists"
                )
            
            conflicts_resolved = []
            affected_memories = []
            
            if detect_conflicts:
                # Find potential conflicts
                similar_memories = self._find_similar_memories(memory)
                
                if similar_memories:
                    conflicts = self.conflict_detector.detect_conflicts(memory, similar_memories)
                    
                    if conflicts:
                        logger.info(f"Detected {len(conflicts)} conflicts for memory {memory.memory_id}")
                        
                        # Resolve conflicts
                        resolutions = self.conflict_resolver.resolve_conflicts(conflicts, user_preferences)
                        conflicts_resolved = resolutions
                        
                        # Apply resolutions
                        for resolution in resolutions:
                            if resolution.action == ResolutionAction.REPLACED:
                                # Archive the existing memory
                                for affected in resolution.affected_memories:
                                    affected.is_active = False
                                    self._update_memory_in_db(affected)
                                    affected_memories.append(affected)
                                
                            elif resolution.action == ResolutionAction.MERGED:
                                # Update the existing memory with merged content
                                for affected in resolution.affected_memories:
                                    affected_memories.append(affected)
                                
                                # Use merged memory instead of original
                                memory = resolution.primary_memory
                                
                            elif resolution.action == ResolutionAction.LINKED:
                                # Update related memories
                                for affected in resolution.affected_memories:
                                    self._update_memory_in_db(affected)
                                    affected_memories.append(affected)
                            
                            elif resolution.action == ResolutionAction.NO_ACTION:
                                # User intervention required
                                return MemoryOperationResult(
                                    result=StorageResult.CONFLICT_DETECTED,
                                    memory=memory,
                                    conflicts_resolved=conflicts_resolved,
                                    metadata={
                                        'conflicts': [c.to_dict() for c in conflicts],
                                        'requires_user_intervention': True
                                    }
                                )
            
            # Store memory in database
            success = self.db_manager.create_memory(
                memory_id=memory.memory_id,
                user_id=memory.user_id,
                content=memory.content,
                original_message=memory.original_message,
                category=memory.category,
                confidence_score=memory.confidence_score,
                timestamp=memory.timestamp,
                metadata=memory.metadata,
                embedding=memory.embedding
            )
            
            if not success:
                raise MemoryOperationError("Failed to store memory in database")
            
            # Determine result type based on resolutions
            result_type = StorageResult.CREATED
            if conflicts_resolved:
                if any(r.action == ResolutionAction.MERGED for r in conflicts_resolved):
                    result_type = StorageResult.MERGED
                elif any(r.action == ResolutionAction.REPLACED for r in conflicts_resolved):
                    result_type = StorageResult.REPLACED
                else:
                    result_type = StorageResult.UPDATED
            
            logger.info(f"Memory {memory.memory_id} stored successfully with result: {result_type.value}")
            
            return MemoryOperationResult(
                result=result_type,
                memory=memory,
                affected_memories=affected_memories,
                conflicts_resolved=conflicts_resolved,
                metadata={
                    'conflicts_detected': len(conflicts_resolved),
                    'operation_id': str(uuid.uuid4())
                }
            )
            
        except ValidationError as e:
            self._error_count += 1
            logger.error(f"Validation error storing memory: {e}")
            return MemoryOperationResult(
                result=StorageResult.ERROR,
                error_message=f"Validation error: {e}"
            )
        except Exception as e:
            self._error_count += 1
            logger.error(f"Error storing memory {memory.memory_id}: {e}")
            raise MemoryOperationError(f"Failed to store memory: {e}")
    
    def process_and_store_memory(self, user_id: str, message: str, session_id: str = "default",
                                user_preferences: Optional[UserPreferences] = None,
                                detect_conflicts: bool = True) -> MemoryOperationResult:
        """
        Process a raw message using LLM extraction and store the resulting memories.
        
        This is the main method for intelligent memory storage that:
        1. Uses MemoryProcessor for LLM-based memory extraction
        2. Converts extracted memories to Memory objects
        3. Stores them with conflict detection and resolution
        
        Args:
            user_id: ID of the user
            message: Raw message text to process
            session_id: Session identifier for context
            user_preferences: User preferences for conflict resolution
            detect_conflicts: Whether to detect and resolve conflicts
            
        Returns:
            MemoryOperationResult: Result of processing and storage operations
        """
        start_time = datetime.now()
        
        try:
            logger.info(f"Processing and storing memory for user {user_id}")
            
            # Ensure user exists
            self._ensure_user_exists(user_id)
            
            # Get previous memories for context
            existing_memories = self.list_memories(user_id, limit=20)
            previous_memories = [
                {
                    'content': mem.content,
                    'timestamp': mem.timestamp.isoformat() if mem.timestamp else None,
                    'category': mem.category
                }
                for mem in existing_memories
            ]
            
            # Process message using LLM
            logger.info(f"Using LLM to extract memories from message")
            processing_result = self.memory_processor.process_message(
                user_id=user_id,
                session_id=session_id,
                message_text=message,
                previous_memories=previous_memories
            )
            
            if not processing_result.success:
                logger.warning(f"Memory processing failed: {processing_result.error_message}")
                return MemoryOperationResult(
                    result=StorageResult.ERROR,
                    error_message=processing_result.error_message or "Memory processing failed"
                )
            
            if not processing_result.memories:
                logger.info("No memories extracted from message")
                return MemoryOperationResult(
                    result=StorageResult.NO_CHANGE,
                    metadata={
                        'processing_result': processing_result.to_dict(),
                        'memories_extracted': 0,
                        'total_processing_time_ms': int((datetime.now() - start_time).total_seconds() * 1000)
                    }
                )
            
            # Convert extracted memories to Memory objects and store them
            stored_memories = []
            all_conflicts_resolved = []
            
            for extracted_memory in processing_result.memories:
                # Create Memory object from extracted memory
                memory = Memory(
                    memory_id=str(uuid.uuid4()),
                    user_id=user_id,
                    content=extracted_memory.content,
                    original_message=message,
                    category=extracted_memory.memory_type.value if extracted_memory.memory_type else None,
                    confidence_score=extracted_memory.confidence,
                    timestamp=datetime.now(),
                    metadata={
                        'extraction_context': extracted_memory.context or {},
                        'processing_metadata': processing_result.metadata,
                        'extracted_entities': [e.__dict__ for e in processing_result.extracted_entities],
                        'entities': extracted_memory.entities or [],
                        'temporal_info': extracted_memory.temporal_info,
                        'relationships': extracted_memory.relationships or []
                    }
                )
                
                # Store individual memory
                store_result = self.store_memory(
                    memory=memory,
                    user_preferences=user_preferences,
                    detect_conflicts=detect_conflicts
                )
                
                if store_result.result == StorageResult.CREATED or store_result.result == StorageResult.UPDATED:
                    stored_memories.append(store_result.memory)
                    if store_result.conflicts_resolved:
                        all_conflicts_resolved.extend(store_result.conflicts_resolved)
                else:
                    logger.warning(f"Failed to store extracted memory: {store_result.error_message}")
            
            if not stored_memories:
                return MemoryOperationResult(
                    result=StorageResult.ERROR,
                    error_message="No memories could be stored",
                    metadata={
                        'total_processing_time_ms': int((datetime.now() - start_time).total_seconds() * 1000)
                    }
                )
            
            # Return success with the primary memory (first one)
            primary_memory = stored_memories[0]
            result_type = StorageResult.CREATED if len(processing_result.memories) == 1 else StorageResult.BATCH_CREATED
            
            processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
            
            logger.info(f"Successfully processed and stored {len(stored_memories)} memories from message")
            
            return MemoryOperationResult(
                result=result_type,
                memory=primary_memory,
                conflicts_resolved=all_conflicts_resolved,
                metadata={
                    'processing_result': processing_result.to_dict(),
                    'memories_extracted': len(processing_result.memories),
                    'memories_stored': len(stored_memories),
                    'llm_processing_time_ms': processing_result.processing_time_ms,
                    'total_processing_time_ms': processing_time,
                    'confidence_scores': [mem.confidence_score for mem in stored_memories]
                }
            )
            
        except Exception as e:
            self._error_count += 1
            processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
            logger.error(f"Error processing and storing memory: {e}")
            raise MemoryOperationError(f"Failed to process and store memory: {e}")
    
    def get_memory(self, memory_id: str) -> Optional[Memory]:
        """
        Get memory by ID.
        
        Args:
            memory_id: ID of memory to retrieve
            
        Returns:
            Memory object or None if not found
            
        Raises:
            MemoryOperationError: If operation fails
        """
        try:
            memory_dict = self.db_manager.get_memory(memory_id)
            if memory_dict:
                return Memory(**memory_dict)
            return None
            
        except Exception as e:
            self._error_count += 1
            logger.error(f"Error retrieving memory {memory_id}: {e}")
            raise MemoryOperationError(f"Failed to get memory: {e}")
    
    def update_memory(self, memory_id: str, updates: Dict[str, Any],
                     user_preferences: Optional[UserPreferences] = None) -> MemoryOperationResult:
        """
        Update an existing memory.
        
        Args:
            memory_id: ID of memory to update
            updates: Dictionary of fields to update
            user_preferences: User preferences for conflict resolution
            
        Returns:
            MemoryOperationResult with operation details
            
        Raises:
            MemoryOperationError: If operation fails
        """
        try:
            self._operation_count += 1
            
            # Get existing memory
            existing_memory = self.get_memory(memory_id)
            if not existing_memory:
                return MemoryOperationResult(
                    result=StorageResult.ERROR,
                    error_message="Memory not found"
                )
            
            # Apply updates to memory object
            updated_memory = Memory(**existing_memory.to_dict())
            for field, value in updates.items():
                if hasattr(updated_memory, field):
                    setattr(updated_memory, field, value)
                else:
                    logger.warning(f"Unknown field in update: {field}")
            
            # Update timestamp
            updated_memory.updated_at = datetime.now()
            
            # Validate updated memory
            self.validate_memory(updated_memory)
            
            # Update in database
            success = self.db_manager.update_memory(
                memory_id=memory_id,
                content=updates.get('content'),
                category=updates.get('category'),
                confidence_score=updates.get('confidence_score'),
                metadata=updates.get('metadata')
            )
            
            if not success:
                raise MemoryOperationError("Failed to update memory in database")
            
            logger.info(f"Memory {memory_id} updated successfully")
            
            return MemoryOperationResult(
                result=StorageResult.UPDATED,
                memory=updated_memory,
                metadata={'operation_id': str(uuid.uuid4())}
            )
            
        except ValidationError as e:
            self._error_count += 1
            logger.error(f"Validation error updating memory: {e}")
            return MemoryOperationResult(
                result=StorageResult.ERROR,
                error_message=f"Validation error: {e}"
            )
        except Exception as e:
            self._error_count += 1
            logger.error(f"Error updating memory {memory_id}: {e}")
            raise MemoryOperationError(f"Failed to update memory: {e}")
    
    def delete_memory(self, memory_id: str, soft_delete: bool = True) -> bool:
        """
        Delete a memory.
        
        Args:
            memory_id: ID of memory to delete
            soft_delete: Whether to perform soft delete (default) or hard delete
            
        Returns:
            True if successful, False otherwise
            
        Raises:
            MemoryOperationError: If operation fails
        """
        try:
            self._operation_count += 1
            
            success = self.db_manager.delete_memory(memory_id, soft_delete=soft_delete)
            
            if success:
                logger.info(f"Memory {memory_id} {'soft' if soft_delete else 'hard'} deleted successfully")
            else:
                logger.warning(f"Memory {memory_id} not found for deletion")
            
            return success
            
        except Exception as e:
            self._error_count += 1
            logger.error(f"Error deleting memory {memory_id}: {e}")
            raise MemoryOperationError(f"Failed to delete memory: {e}")
    
    def list_memories(self, user_id: str, category: Optional[str] = None,
                     limit: int = 100, offset: int = 0) -> List[Memory]:
        """
        List memories for a user.
        
        Args:
            user_id: User ID
            category: Optional category filter
            limit: Maximum number of memories to return
            offset: Offset for pagination
            
        Returns:
            List of Memory objects
            
        Raises:
            MemoryOperationError: If operation fails
        """
        try:
            memories_data = self.db_manager.list_memories(
                user_id=user_id,
                category=category,
                limit=limit,
                offset=offset
            )
            
            memories = [Memory(**data) for data in memories_data]
            logger.debug(f"Retrieved {len(memories)} memories for user {user_id}")
            
            return memories
            
        except Exception as e:
            self._error_count += 1
            logger.error(f"Error listing memories for user {user_id}: {e}")
            raise MemoryOperationError(f"Failed to list memories: {e}")
    
    def search_memories(self, user_id: str, query: str, limit: int = 50) -> List[Memory]:
        """
        Search memories using full-text search.
        
        Args:
            user_id: User ID
            query: Search query
            limit: Maximum number of results
            
        Returns:
            List of Memory objects matching the query
            
        Raises:
            MemoryOperationError: If operation fails
        """
        try:
            memories_data = self.db_manager.search_memories(
                user_id=user_id,
                query=query,
                limit=limit
            )
            
            memories = [Memory(**data) for data in memories_data]
            logger.debug(f"Found {len(memories)} memories matching query '{query}' for user {user_id}")
            
            return memories
            
        except Exception as e:
            self._error_count += 1
            logger.error(f"Error searching memories for user {user_id}: {e}")
            raise MemoryOperationError(f"Failed to search memories: {e}")
    
    def store_memories_batch(self, memories: List[Memory], 
                           user_preferences: Optional[UserPreferences] = None,
                           detect_conflicts: bool = True) -> BatchOperationResult:
        """
        Store multiple memories in batch.
        
        Args:
            memories: List of Memory objects to store
            user_preferences: User preferences for conflict resolution
            detect_conflicts: Whether to perform conflict detection
            
        Returns:
            BatchOperationResult with detailed results
        """
        results = []
        errors = []
        successful = 0
        
        logger.info(f"Starting batch storage of {len(memories)} memories")
        
        try:
            with self.db_manager.transaction() as conn:
                for i, memory in enumerate(memories):
                    try:
                        result = self.store_memory(
                            memory=memory,
                            user_preferences=user_preferences,
                            detect_conflicts=detect_conflicts
                        )
                        results.append(result)
                        
                        if result.result != StorageResult.ERROR:
                            successful += 1
                        else:
                            errors.append(f"Memory {i}: {result.error_message}")
                            
                    except Exception as e:
                        error_msg = f"Memory {i} ({memory.memory_id}): {e}"
                        errors.append(error_msg)
                        results.append(MemoryOperationResult(
                            result=StorageResult.ERROR,
                            error_message=str(e)
                        ))
                        logger.error(f"Error in batch operation: {error_msg}")
                
                logger.info(f"Batch operation completed: {successful}/{len(memories)} successful")
                
                return BatchOperationResult(
                    total_operations=len(memories),
                    successful_operations=successful,
                    failed_operations=len(memories) - successful,
                    results=results,
                    errors=errors
                )
                
        except Exception as e:
            logger.error(f"Batch operation failed: {e}")
            raise MemoryOperationError(f"Batch operation failed: {e}")
    
    def _find_similar_memories(self, memory: Memory, limit: int = 10) -> List[Memory]:
        """
        Find memories similar to the given memory for conflict detection.
        
        Args:
            memory: Memory to find similar memories for
            limit: Maximum number of similar memories to return
            
        Returns:
            List of similar Memory objects
        """
        try:
            # Extract simple keywords from content for FTS search
            # Remove problematic characters that can cause FTS5 syntax errors
            content_words = memory.content[:100].replace("'", "").replace('"', '').replace(",", " ").replace("(", "").replace(")", "").strip()
            
            # If content is too short or empty after cleaning, return empty list
            if len(content_words) < 3:
                return []
            
            # Search for similar memories by content
            similar_memories = self.search_memories(
                user_id=memory.user_id,
                query=content_words,
                limit=limit
            )
            
            # Filter out exact matches and inactive memories
            similar_memories = [
                m for m in similar_memories 
                if m.memory_id != memory.memory_id and m.is_active
            ]
            
            return similar_memories
            
        except Exception as e:
            logger.warning(f"Error finding similar memories, skipping conflict detection: {e}")
            # Return empty list to skip conflict detection rather than failing the entire operation
            return []
    
    def _update_memory_in_db(self, memory: Memory) -> bool:
        """
        Update memory object in database.
        
        Args:
            memory: Memory object to update
            
        Returns:
            True if successful, False otherwise
        """
        try:
            return self.db_manager.update_memory(
                memory_id=memory.memory_id,
                content=memory.content,
                category=memory.category,
                confidence_score=memory.confidence_score,
                metadata=memory.metadata
            )
        except Exception as e:
            logger.error(f"Error updating memory {memory.memory_id} in database: {e}")
            return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get memory manager statistics.
        
        Returns:
            Dictionary with statistics
        """
        try:
            # Get database health
            db_health = self.db_manager.health_check()
            
            # Get conflict resolver statistics
            resolution_stats = self.conflict_resolver.get_resolution_statistics()
            
            # Get audit trail statistics
            audit_entries = self.conflict_resolver.get_audit_trail(limit=1000)
            
            return {
                'memory_manager': {
                    'operations_count': self._operation_count,
                    'error_count': self._error_count,
                    'error_rate': self._error_count / max(self._operation_count, 1)
                },
                'database': {
                    'status': db_health.get('status'),
                    'checks': db_health.get('checks', {}),
                    'stats': db_health.get('stats', {})
                },
                'conflict_resolution': resolution_stats,
                'audit_trail': {
                    'total_entries': len(audit_entries),
                    'recent_entries': audit_entries[:5] if audit_entries else []
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            return {
                'error': str(e),
                'memory_manager': {
                    'operations_count': self._operation_count,
                    'error_count': self._error_count
                }
            }
    
    def health_check(self) -> Dict[str, Any]:
        """
        Perform comprehensive health check.
        
        Returns:
            Health check results
        """
        health = {
            'status': 'healthy',
            'components': {},
            'timestamp': datetime.now().isoformat()
        }
        
        try:
            # Check database
            db_health = self.db_manager.health_check()
            health['components']['database'] = db_health
            
            # Check conflict detector
            try:
                # Create test memories for conflict detection
                test_mem1 = Memory.create_new("test_user", "Test content for health check")
                test_mem2 = Memory.create_new("test_user", "Test content for health check validation")
                
                conflicts = self.conflict_detector.detect_conflicts(test_mem1, [test_mem2])
                health['components']['conflict_detector'] = {
                    'status': 'healthy',
                    'test_passed': True
                }
            except Exception as e:
                health['components']['conflict_detector'] = {
                    'status': 'unhealthy',
                    'error': str(e)
                }
            
            # Check conflict resolver
            try:
                stats = self.conflict_resolver.get_resolution_statistics()
                health['components']['conflict_resolver'] = {
                    'status': 'healthy',
                    'statistics_available': bool(stats)
                }
            except Exception as e:
                health['components']['conflict_resolver'] = {
                    'status': 'unhealthy',
                    'error': str(e)
                }
            
            # Determine overall status
            component_statuses = [
                comp.get('status', 'unknown') 
                for comp in health['components'].values()
            ]
            
            if 'unhealthy' in component_statuses:
                health['status'] = 'unhealthy'
            elif 'degraded' in component_statuses:
                health['status'] = 'degraded'
                
        except Exception as e:
            health['status'] = 'unhealthy'
            health['error'] = str(e)
            logger.error(f"Health check failed: {e}")
        
        return health
    
    def _ensure_user_exists(self, user_id: str) -> None:
        """
        Ensure user exists in database, create if missing.
        
        Args:
            user_id: User ID to check/create
            
        Raises:
            MemoryOperationError: If user creation fails
        """
        try:
            # Check if user exists
            existing_user = self.db_manager.get_user(user_id)
            if existing_user:
                return
                
            # Create new user with minimal required data
            # Store user in database with minimal data
            self.db_manager.create_user(
                user_id=user_id,
                settings=None,  # No specific settings
                metadata={"auto_created": True}  # Mark as auto-created
            )
            logger.info(f"Auto-created user: {user_id}")
            
        except Exception as e:
            logger.error(f"Failed to ensure user {user_id} exists: {e}")
            raise MemoryOperationError(f"Failed to create user {user_id}: {e}")
    
    def close(self):
        """Close memory manager and cleanup resources."""
        try:
            self.db_manager.close()
            logger.info("MemoryManager closed")
        except Exception as e:
            logger.error(f"Error closing MemoryManager: {e}")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()