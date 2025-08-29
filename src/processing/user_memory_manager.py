"""
User-specific Memory Manager for per-user database architecture.

This module provides a memory manager that works with per-user databases,
adapting the original MemoryManager interface to remove user_id dependencies.
"""
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple

from models.memory import Memory
from db.user_db_manager import UserDatabaseManager
from processing.memory_processor import MemoryProcessor, ProcessingResult
from processing.conflict_detector import ConflictDetector, Conflict
from processing.conflict_resolver import ConflictResolver, Resolution, ResolutionAction
from processing.temporal_resolver import TemporalResolver
from processing.exceptions import (
    MemoryProcessingError, ConflictResolutionError, 
    MemoryNotFoundError, ValidationError
)
from core.logging import get_logger

logger = get_logger(__name__)


class UserMemoryManager:
    """
    Memory manager for a specific user's database.
    
    This class provides all memory operations for a single user,
    working with a user-specific database that doesn't require
    user_id parameters since data isolation is physical.
    """
    
    def __init__(self, 
                 user_db_manager: UserDatabaseManager,
                 memory_processor: MemoryProcessor,
                 conflict_detector: ConflictDetector,
                 conflict_resolver: ConflictResolver,
                 temporal_resolver: TemporalResolver):
        """
        Initialize user memory manager.
        
        Args:
            user_db_manager: User-specific database manager
            memory_processor: Memory processing pipeline
            conflict_detector: Conflict detection service
            conflict_resolver: Conflict resolution service
            temporal_resolver: Temporal processing service
        """
        self.db_manager = user_db_manager
        self.memory_processor = memory_processor
        self.conflict_detector = conflict_detector
        self.conflict_resolver = conflict_resolver
        self.temporal_resolver = temporal_resolver
        
    def store_memory(self, 
                    message: str,
                    session_id: Optional[str] = None,
                    metadata: Optional[Dict[str, Any]] = None,
                    resolution_strategy: str = "auto") -> Dict[str, Any]:
        """
        Store a memory from a natural language message.
        
        Args:
            message: Natural language message to process
            session_id: Optional session identifier
            metadata: Additional metadata
            resolution_strategy: Conflict resolution strategy
            
        Returns:
            Dict containing storage results and metadata
        """
        start_time = datetime.now()
        
        try:
            # Process the message to extract memories
            processing_result = self.memory_processor.process_message(message)
            
            if not processing_result.success:
                raise MemoryProcessingError(f"Memory processing failed: {processing_result.error}")
            
            if not processing_result.memories:
                logger.info("No memories extracted from message")
                return {
                    'success': True,
                    'action': 'no_memories_extracted',
                    'message': message,
                    'processing_time_ms': (datetime.now() - start_time).total_seconds() * 1000,
                    'memories_processed': 0
                }
            
            # Process each extracted memory
            results = []
            for extracted_memory in processing_result.memories:
                try:
                    result = self._store_single_memory(
                        extracted_memory, 
                        message, 
                        session_id, 
                        metadata, 
                        resolution_strategy
                    )
                    results.append(result)
                except Exception as e:
                    logger.error(f"Failed to store memory: {e}")
                    results.append({
                        'success': False,
                        'error': str(e),
                        'content': extracted_memory.get('content', 'Unknown')
                    })
            
            # Return summary result
            successful_results = [r for r in results if r.get('success', False)]
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            
            return {
                'success': len(successful_results) > 0,
                'message': message,
                'processing_time_ms': processing_time,
                'memories_processed': len(results),
                'memories_stored': len(successful_results),
                'results': results,
                'primary_result': successful_results[0] if successful_results else results[0] if results else None
            }
            
        except Exception as e:
            logger.error(f"Memory storage failed: {e}")
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            return {
                'success': False,
                'message': message,
                'error': str(e),
                'processing_time_ms': processing_time,
                'memories_processed': 0,
                'memories_stored': 0
            }
    
    def _store_single_memory(self,
                           extracted_memory: Dict[str, Any],
                           original_message: str,
                           session_id: Optional[str],
                           metadata: Optional[Dict[str, Any]],
                           resolution_strategy: str) -> Dict[str, Any]:
        """
        Store a single extracted memory with conflict resolution.
        
        Args:
            extracted_memory: Memory data from processing pipeline
            original_message: Original message text
            session_id: Session identifier
            metadata: Additional metadata
            resolution_strategy: Conflict resolution strategy
            
        Returns:
            Dict containing storage result details
        """
        memory_id = str(uuid.uuid4())
        content = extracted_memory.get('content', '')
        category = extracted_memory.get('memory_type', 'other')
        confidence = extracted_memory.get('confidence', 0.0)
        
        # Resolve temporal information
        timestamp = None
        if 'temporal_info' in extracted_memory:
            timestamp = self.temporal_resolver.resolve_temporal_reference(
                extracted_memory['temporal_info'],
                datetime.now()
            )
        
        # Prepare memory object
        memory_data = {
            'memory_id': memory_id,
            'content': content,
            'original_message': original_message,
            'category': category,
            'confidence_score': confidence,
            'timestamp': timestamp,
            'metadata': {
                **(metadata or {}),
                'entities': extracted_memory.get('entities', []),
                'extraction_confidence': confidence,
                'session_id': session_id
            }
        }
        
        # Check for conflicts
        existing_memories = self._find_similar_memories(content, category)
        
        if existing_memories:
            # Handle conflicts
            conflicts = []
            for existing in existing_memories:
                conflict = self.conflict_detector.detect_conflict(
                    content, existing['content']
                )
                if conflict:
                    conflicts.append((existing, conflict))
            
            if conflicts:
                return self._resolve_conflicts(
                    memory_data, conflicts, resolution_strategy
                )
        
        # No conflicts, store new memory
        success = self.db_manager.create_memory(
            memory_id=memory_id,
            content=content,
            original_message=original_message,
            category=category,
            confidence_score=confidence,
            timestamp=timestamp,
            metadata=memory_data['metadata']
        )
        
        if success:
            return {
                'success': True,
                'memory_id': memory_id,
                'action': 'created',
                'content': content,
                'category': category,
                'confidence': confidence,
                'conflicts_resolved': 0
            }
        else:
            raise MemoryProcessingError("Failed to store memory in database")
    
    def _find_similar_memories(self, content: str, category: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Find memories similar to the given content."""
        try:
            # First try category-specific search
            results = self.db_manager.search_memories(
                query=content[:100],  # Limit query length
                limit=limit,
                category=category
            )
            
            # If no category-specific results, try broader search
            if not results:
                results = self.db_manager.search_memories(
                    query=content[:100],
                    limit=limit
                )
            
            return results
            
        except Exception as e:
            logger.warning(f"Error finding similar memories: {e}")
            return []
    
    def _resolve_conflicts(self,
                          new_memory: Dict[str, Any],
                          conflicts: List[Tuple[Dict[str, Any], Conflict]],
                          resolution_strategy: str) -> Dict[str, Any]:
        """
        Resolve conflicts between new memory and existing memories.
        
        Args:
            new_memory: New memory data
            conflicts: List of (existing_memory, conflict) tuples
            resolution_strategy: Resolution strategy to use
            
        Returns:
            Dict containing resolution results
        """
        try:
            # For simplicity, resolve against the first (most similar) conflict
            existing_memory, conflict = conflicts[0]
            
            resolution = self.conflict_resolver.resolve_conflict(
                existing_content=existing_memory['content'],
                new_content=new_memory['content'],
                conflict=conflict,
                strategy=resolution_strategy,
                context={
                    'existing_confidence': existing_memory.get('confidence_score', 0.0),
                    'new_confidence': new_memory.get('confidence_score', 0.0),
                    'existing_timestamp': existing_memory.get('created_at'),
                    'category': new_memory.get('category')
                }
            )
            
            return self._apply_resolution(new_memory, existing_memory, resolution)
            
        except Exception as e:
            logger.error(f"Conflict resolution failed: {e}")
            # Fallback: store as new memory
            memory_id = new_memory['memory_id']
            success = self.db_manager.create_memory(**new_memory)
            
            return {
                'success': success,
                'memory_id': memory_id,
                'action': 'created_with_conflict',
                'content': new_memory['content'],
                'conflicts_resolved': 0,
                'resolution_error': str(e)
            }
    
    def _apply_resolution(self,
                         new_memory: Dict[str, Any],
                         existing_memory: Dict[str, Any],
                         resolution: Resolution) -> Dict[str, Any]:
        """Apply a conflict resolution action."""
        try:
            if resolution.action == ResolutionAction.UPDATE:
                # Update existing memory
                success = self.db_manager.update_memory(
                    memory_id=existing_memory['memory_id'],
                    content=resolution.resolved_content,
                    confidence_score=resolution.confidence,
                    metadata=new_memory.get('metadata', {})
                )
                
                return {
                    'success': success,
                    'memory_id': existing_memory['memory_id'],
                    'action': 'updated',
                    'content': resolution.resolved_content,
                    'confidence': resolution.confidence,
                    'conflicts_resolved': 1,
                    'resolution_strategy': resolution.action.value
                }
            
            elif resolution.action == ResolutionAction.CREATE_NEW:
                # Store as new memory
                memory_id = new_memory['memory_id']
                success = self.db_manager.create_memory(**new_memory)
                
                return {
                    'success': success,
                    'memory_id': memory_id,
                    'action': 'created',
                    'content': new_memory['content'],
                    'conflicts_resolved': 1,
                    'resolution_strategy': resolution.action.value
                }
            
            elif resolution.action == ResolutionAction.MERGE:
                # Update existing with merged content
                merged_metadata = {
                    **existing_memory.get('metadata', {}),
                    **new_memory.get('metadata', {}),
                    'merged_from': [existing_memory['memory_id'], new_memory['memory_id']]
                }
                
                success = self.db_manager.update_memory(
                    memory_id=existing_memory['memory_id'],
                    content=resolution.resolved_content,
                    confidence_score=resolution.confidence,
                    metadata=merged_metadata
                )
                
                return {
                    'success': success,
                    'memory_id': existing_memory['memory_id'],
                    'action': 'merged',
                    'content': resolution.resolved_content,
                    'confidence': resolution.confidence,
                    'conflicts_resolved': 1,
                    'resolution_strategy': resolution.action.value
                }
            
            else:  # IGNORE or other
                return {
                    'success': True,
                    'memory_id': existing_memory['memory_id'],
                    'action': 'ignored',
                    'content': existing_memory['content'],
                    'conflicts_resolved': 1,
                    'resolution_strategy': resolution.action.value
                }
                
        except Exception as e:
            logger.error(f"Failed to apply resolution {resolution.action}: {e}")
            raise ConflictResolutionError(f"Resolution application failed: {e}")
    
    # Memory retrieval methods
    def get_memory(self, memory_id: str) -> Optional[Dict[str, Any]]:
        """Get a memory by ID."""
        return self.db_manager.get_memory(memory_id)
    
    def list_memories(self,
                     category: Optional[str] = None,
                     limit: int = 50,
                     offset: int = 0,
                     sort_by: str = "created_at",
                     sort_order: str = "desc",
                     from_date: Optional[datetime] = None,
                     to_date: Optional[datetime] = None,
                     min_confidence: Optional[float] = None,
                     max_confidence: Optional[float] = None) -> Dict[str, Any]:
        """List memories with filtering and pagination."""
        try:
            memories = self.db_manager.list_memories(
                category=category,
                limit=limit,
                offset=offset,
                sort_by=sort_by,
                sort_order=sort_order,
                from_date=from_date,
                to_date=to_date,
                min_confidence=min_confidence,
                max_confidence=max_confidence
            )
            
            total_count = self.db_manager.count_memories(
                category=category,
                from_date=from_date,
                to_date=to_date,
                min_confidence=min_confidence,
                max_confidence=max_confidence
            )
            
            return {
                'memories': memories,
                'pagination': {
                    'total_count': total_count,
                    'limit': limit,
                    'offset': offset,
                    'has_more': offset + len(memories) < total_count
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to list memories: {e}")
            raise MemoryProcessingError(f"Memory listing failed: {e}")
    
    def search_memories(self,
                       query: str,
                       limit: int = 50,
                       offset: int = 0,
                       category: Optional[str] = None,
                       min_confidence: Optional[float] = None) -> Dict[str, Any]:
        """Search memories with full-text search."""
        try:
            memories = self.db_manager.search_memories(
                query=query,
                limit=limit,
                offset=offset,
                category=category,
                min_confidence=min_confidence
            )
            
            # Add relevance scores (simplified)
            for i, memory in enumerate(memories):
                memory['relevance_score'] = max(0.1, 1.0 - (i * 0.05))  # Simple scoring
            
            return {
                'results': memories,
                'query': query,
                'total_results': len(memories)  # Simplified - FTS doesn't easily give total counts
            }
            
        except Exception as e:
            logger.error(f"Memory search failed: {e}")
            raise MemoryProcessingError(f"Memory search failed: {e}")
    
    def delete_memory(self, memory_id: str, soft_delete: bool = True) -> bool:
        """Delete a memory."""
        try:
            return self.db_manager.delete_memory(memory_id, soft_delete=soft_delete)
        except Exception as e:
            logger.error(f"Failed to delete memory {memory_id}: {e}")
            raise MemoryProcessingError(f"Memory deletion failed: {e}")
    
    def export_memories(self,
                       format: str = "json",
                       category: Optional[str] = None,
                       from_date: Optional[datetime] = None,
                       to_date: Optional[datetime] = None,
                       min_confidence: Optional[float] = None,
                       max_memories: Optional[int] = None) -> Dict[str, Any]:
        """Export memories in various formats."""
        try:
            # Get memories for export
            limit = max_memories or 10000  # Default limit
            memories = self.db_manager.list_memories(
                category=category,
                limit=limit,
                offset=0,
                from_date=from_date,
                to_date=to_date,
                min_confidence=min_confidence
            )
            
            export_data = {
                'exported_at': datetime.now().isoformat(),
                'format': format,
                'memory_count': len(memories),
                'filters': {
                    'category': category,
                    'from_date': from_date.isoformat() if from_date else None,
                    'to_date': to_date.isoformat() if to_date else None,
                    'min_confidence': min_confidence
                }
            }
            
            if format == "json":
                export_data['data'] = memories
            elif format == "csv":
                # Simple CSV format
                if memories:
                    header = "memory_id,content,category,confidence_score,created_at\n"
                    rows = []
                    for memory in memories:
                        row = f'"{memory["memory_id"]}","{memory["content"][:100]}","{memory.get("category", "")}",{memory.get("confidence_score", 0.0)},"{memory["created_at"]}"'
                        rows.append(row)
                    export_data['data'] = header + "\n".join(rows)
                else:
                    export_data['data'] = "memory_id,content,category,confidence_score,created_at\n"
            else:
                # Default to JSON
                export_data['data'] = memories
            
            return export_data
            
        except Exception as e:
            logger.error(f"Memory export failed: {e}")
            raise MemoryProcessingError(f"Memory export failed: {e}")
    
    # Health and utility methods
    def health_check(self) -> Dict[str, Any]:
        """Perform health check on user's memory system."""
        return self.db_manager.health_check()
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get user memory statistics."""
        try:
            total_memories = self.db_manager.count_memories()
            active_memories = self.db_manager.count_memories(include_inactive=False)
            
            # Get category breakdown
            categories = {}
            all_memories = self.db_manager.list_memories(limit=10000)  # Large limit for stats
            for memory in all_memories:
                category = memory.get('category', 'unknown')
                categories[category] = categories.get(category, 0) + 1
            
            return {
                'total_memories': total_memories,
                'active_memories': active_memories,
                'inactive_memories': total_memories - active_memories,
                'categories': categories,
                'database_path': self.db_manager.db_path
            }
            
        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
            return {'error': str(e)}
    
    def close(self):
        """Close database connections."""
        self.db_manager.close()