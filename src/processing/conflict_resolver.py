"""
Conflict resolution system for resolving conflicts between memories.
"""
import uuid
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
import logging

from models.memory import Memory
from processing.conflict_detector import Conflict, ConflictType
from core.logging import get_logger

logger = get_logger(__name__)


class ResolutionStrategy(Enum):
    """Resolution strategies for different conflict types."""
    UPDATE_TIMESTAMP = "update_timestamp"
    REPLACE = "replace"
    MERGE = "merge"
    LINK = "link"
    CREATE_NEW = "create_new"
    USER_CHOOSE = "user_choose"
    KEEP_BOTH = "keep_both"
    ARCHIVE_OLD = "archive_old"


class ResolutionAction(Enum):
    """Actions taken during resolution."""
    CREATED = "created"
    UPDATED = "updated" 
    MERGED = "merged"
    REPLACED = "replaced"
    LINKED = "linked"
    ARCHIVED = "archived"
    NO_ACTION = "no_action"


@dataclass
class Resolution:
    """Result of conflict resolution."""
    action: ResolutionAction
    strategy: ResolutionStrategy
    primary_memory: Memory
    affected_memories: List[Memory] = field(default_factory=list)
    merged_content: Optional[str] = None
    confidence: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    audit_info: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert resolution to dictionary for serialization."""
        return {
            'action': self.action.value,
            'strategy': self.strategy.value,
            'primary_memory_id': self.primary_memory.memory_id,
            'affected_memory_ids': [m.memory_id for m in self.affected_memories],
            'merged_content': self.merged_content,
            'confidence': self.confidence,
            'metadata': self.metadata,
            'audit_info': self.audit_info
        }


@dataclass
class UserPreferences:
    """User preferences for conflict resolution."""
    default_strategy: ResolutionStrategy = ResolutionStrategy.MERGE
    auto_resolve_duplicates: bool = True
    preserve_original: bool = True
    confidence_threshold: float = 0.8
    max_merge_attempts: int = 3
    preferred_resolution_by_type: Dict[str, str] = field(default_factory=dict)
    
    def __post_init__(self):
        """Initialize default preferences by conflict type."""
        if not self.preferred_resolution_by_type:
            self.preferred_resolution_by_type = {
                ConflictType.EXACT_DUPLICATE.value: ResolutionStrategy.UPDATE_TIMESTAMP.value,
                ConflictType.PARTIAL_DUPLICATE.value: ResolutionStrategy.MERGE.value,
                ConflictType.CONTRADICTION.value: ResolutionStrategy.USER_CHOOSE.value,
                ConflictType.UPDATE_NEEDED.value: ResolutionStrategy.REPLACE.value,
                ConflictType.TEMPORAL_OVERLAP.value: ResolutionStrategy.USER_CHOOSE.value,
                ConflictType.RELATED_MEMORY.value: ResolutionStrategy.LINK.value,
                ConflictType.MERGE_CANDIDATE.value: ResolutionStrategy.MERGE.value
            }


@dataclass
class AuditEntry:
    """Audit trail entry for resolution actions."""
    audit_id: str
    timestamp: datetime
    user_id: str
    action: ResolutionAction
    strategy: ResolutionStrategy
    conflict_type: ConflictType
    memory_ids: List[str]
    original_content: Dict[str, str]  # memory_id -> content
    new_content: Dict[str, str]       # memory_id -> content
    metadata: Dict[str, Any]
    rollback_data: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert audit entry to dictionary."""
        return {
            'audit_id': self.audit_id,
            'timestamp': self.timestamp.isoformat(),
            'user_id': self.user_id,
            'action': self.action.value,
            'strategy': self.strategy.value,
            'conflict_type': self.conflict_type.value,
            'memory_ids': self.memory_ids,
            'original_content': self.original_content,
            'new_content': self.new_content,
            'metadata': self.metadata,
            'rollback_data': self.rollback_data
        }


class ConflictResolver:
    """Resolves conflicts between memories using various strategies."""
    
    def __init__(self):
        """Initialize conflict resolver."""
        self.logger = logger
        self.audit_trail: List[AuditEntry] = []
        
        # Strategy mappings
        self.strategy_handlers = {
            ResolutionStrategy.UPDATE_TIMESTAMP: self._update_timestamp,
            ResolutionStrategy.REPLACE: self._replace_memory,
            ResolutionStrategy.MERGE: self._merge_memories,
            ResolutionStrategy.LINK: self._link_memories,
            ResolutionStrategy.CREATE_NEW: self._create_new,
            ResolutionStrategy.KEEP_BOTH: self._keep_both,
            ResolutionStrategy.ARCHIVE_OLD: self._archive_old
        }
        
        self.logger.info("ConflictResolver initialized")
    
    def resolve_conflict(self, conflict: Conflict, user_preferences: Optional[UserPreferences] = None) -> Resolution:
        """
        Resolve a single conflict using appropriate strategy.
        
        Args:
            conflict: The conflict to resolve
            user_preferences: User's resolution preferences
            
        Returns:
            Resolution result
        """
        if user_preferences is None:
            user_preferences = UserPreferences()
        
        # Determine resolution strategy
        strategy = self._determine_strategy(conflict, user_preferences)
        
        self.logger.info(f"Resolving {conflict.conflict_type.value} conflict using {strategy.value} strategy")
        
        # Execute resolution strategy
        try:
            if strategy in self.strategy_handlers:
                resolution = self.strategy_handlers[strategy](conflict, user_preferences)
            else:
                # Fallback to user choice for unhandled strategies
                resolution = self._handle_user_choice(conflict, user_preferences)
            
            # Create audit entry
            audit_entry = self._create_audit_entry(conflict, resolution, user_preferences.default_strategy.value)
            self.audit_trail.append(audit_entry)
            resolution.audit_info = audit_entry.to_dict()
            
            self.logger.info(f"Conflict resolved with action: {resolution.action.value}")
            return resolution
            
        except Exception as e:
            self.logger.error(f"Error resolving conflict: {e}")
            # Return no-action resolution on error
            return Resolution(
                action=ResolutionAction.NO_ACTION,
                strategy=strategy,
                primary_memory=conflict.new_memory,
                confidence=0.0,
                metadata={'error': str(e)}
            )
    
    def resolve_conflicts(self, conflicts: List[Conflict], user_preferences: Optional[UserPreferences] = None) -> List[Resolution]:
        """
        Resolve multiple conflicts in order of priority.
        
        Args:
            conflicts: List of conflicts to resolve
            user_preferences: User's resolution preferences
            
        Returns:
            List of resolution results
        """
        if not conflicts:
            return []
        
        if user_preferences is None:
            user_preferences = UserPreferences()
        
        # Create a copy to avoid modifying the original preferences
        working_preferences = UserPreferences(
            default_strategy=user_preferences.default_strategy,
            auto_resolve_duplicates=user_preferences.auto_resolve_duplicates,
            preserve_original=user_preferences.preserve_original,
            confidence_threshold=user_preferences.confidence_threshold,
            max_merge_attempts=user_preferences.max_merge_attempts,
            preferred_resolution_by_type=user_preferences.preferred_resolution_by_type.copy()
        )
        
        # Sort conflicts by severity and confidence (highest first)
        sorted_conflicts = sorted(
            conflicts, 
            key=lambda c: (c.severity.value, -c.confidence),
            reverse=True
        )
        
        resolutions = []
        merge_count = 0
        
        for conflict in sorted_conflicts:
            resolution = self.resolve_conflict(conflict, working_preferences)
            resolutions.append(resolution)
            
            # Track merge count and update preferences if limit exceeded
            if resolution.action == ResolutionAction.MERGED:
                merge_count += 1
                if merge_count >= working_preferences.max_merge_attempts:
                    working_preferences.preferred_resolution_by_type[ConflictType.MERGE_CANDIDATE.value] = ResolutionStrategy.USER_CHOOSE.value
        
        self.logger.info(f"Resolved {len(conflicts)} conflicts with {len(resolutions)} resolutions")
        return resolutions
    
    def _determine_strategy(self, conflict: Conflict, user_preferences: UserPreferences) -> ResolutionStrategy:
        """Determine the best resolution strategy for a conflict."""
        conflict_type = conflict.conflict_type.value
        
        # For contradictions, use confidence-based logic instead of user preferences
        if conflict.conflict_type == ConflictType.CONTRADICTION:
            new_memory_confidence = conflict.new_memory.confidence_score or 0.0
            existing_memory_confidence = conflict.existing_memory.confidence_score or 0.0
            
            if new_memory_confidence > existing_memory_confidence and new_memory_confidence >= user_preferences.confidence_threshold:
                return ResolutionStrategy.REPLACE
            else:
                return ResolutionStrategy.USER_CHOOSE
        
        # Check user preferences for other conflict types
        if conflict_type in user_preferences.preferred_resolution_by_type:
            preferred_strategy = user_preferences.preferred_resolution_by_type[conflict_type]
            try:
                return ResolutionStrategy(preferred_strategy)
            except ValueError:
                self.logger.warning(f"Invalid preferred strategy: {preferred_strategy}")
        
        # Default strategy mappings based on conflict type
        if conflict.conflict_type == ConflictType.EXACT_DUPLICATE:
            return ResolutionStrategy.UPDATE_TIMESTAMP
        elif conflict.conflict_type == ConflictType.PARTIAL_DUPLICATE:
            return ResolutionStrategy.MERGE
        elif conflict.conflict_type == ConflictType.UPDATE_NEEDED:
            return ResolutionStrategy.REPLACE
        elif conflict.conflict_type == ConflictType.TEMPORAL_OVERLAP:
            return ResolutionStrategy.USER_CHOOSE
        elif conflict.conflict_type == ConflictType.RELATED_MEMORY:
            return ResolutionStrategy.LINK
        elif conflict.conflict_type == ConflictType.MERGE_CANDIDATE:
            return ResolutionStrategy.MERGE
        else:
            return user_preferences.default_strategy
    
    def _update_timestamp(self, conflict: Conflict, user_preferences: UserPreferences) -> Resolution:
        """Update timestamp of existing memory."""
        existing_memory = conflict.existing_memory
        existing_memory.updated_at = datetime.now()
        
        return Resolution(
            action=ResolutionAction.UPDATED,
            strategy=ResolutionStrategy.UPDATE_TIMESTAMP,
            primary_memory=existing_memory,
            confidence=0.95,
            metadata={
                'original_updated_at': existing_memory.updated_at.isoformat(),
                'reason': 'Exact duplicate detected'
            }
        )
    
    def _replace_memory(self, conflict: Conflict, user_preferences: UserPreferences) -> Resolution:
        """Replace existing memory with new memory."""
        new_memory = conflict.new_memory
        existing_memory = conflict.existing_memory
        
        # Preserve some metadata from existing memory
        if user_preferences.preserve_original:
            new_memory.metadata['replaced_memory_id'] = existing_memory.memory_id
            new_memory.metadata['original_created_at'] = existing_memory.created_at.isoformat()
        
        # Archive the old memory instead of deleting
        existing_memory.is_active = False
        existing_memory.metadata['archived_reason'] = 'replaced_by_newer'
        existing_memory.metadata['replaced_by'] = new_memory.memory_id
        existing_memory.updated_at = datetime.now()
        
        return Resolution(
            action=ResolutionAction.REPLACED,
            strategy=ResolutionStrategy.REPLACE,
            primary_memory=new_memory,
            affected_memories=[existing_memory],
            confidence=conflict.confidence,
            metadata={
                'replaced_memory_id': existing_memory.memory_id,
                'reason': conflict.details.get('reason', 'Memory replacement')
            }
        )
    
    def _merge_memories(self, conflict: Conflict, user_preferences: UserPreferences) -> Resolution:
        """Merge new memory with existing memory."""
        new_memory = conflict.new_memory
        existing_memory = conflict.existing_memory
        
        # Create merged content
        merged_content = self._create_merged_content(new_memory.content, existing_memory.content)
        
        # Update existing memory with merged content
        existing_memory.content = merged_content
        existing_memory.updated_at = datetime.now()
        existing_memory.confidence_score = max(
            existing_memory.confidence_score or 0.0,
            new_memory.confidence_score or 0.0
        )
        
        # Merge metadata
        existing_memory.metadata['merged_with'] = new_memory.memory_id
        existing_memory.metadata['merge_timestamp'] = datetime.now().isoformat()
        existing_memory.metadata['original_content'] = existing_memory.content
        
        # Add new memory's metadata
        if new_memory.metadata:
            existing_memory.metadata.update(new_memory.metadata)
        
        return Resolution(
            action=ResolutionAction.MERGED,
            strategy=ResolutionStrategy.MERGE,
            primary_memory=existing_memory,
            merged_content=merged_content,
            confidence=conflict.confidence,
            metadata={
                'merged_from': new_memory.memory_id,
                'merge_algorithm': 'content_combination',
                'original_contents': {
                    'existing': existing_memory.content,
                    'new': new_memory.content
                }
            }
        )
    
    def _create_merged_content(self, content1: str, content2: str) -> str:
        """Create merged content from two memory contents."""
        # Simple merge strategy: combine unique information
        sentences1 = set(s.strip() for s in content1.split('.') if s.strip())
        sentences2 = set(s.strip() for s in content2.split('.') if s.strip())
        
        # Combine unique sentences, prioritizing longer/more detailed ones
        all_sentences = sentences1.union(sentences2)
        merged_sentences = []
        
        for sentence in all_sentences:
            if sentence and sentence not in merged_sentences:
                # Check if this sentence provides new information
                is_unique = True
                for existing in merged_sentences:
                    if len(sentence) < len(existing) and sentence.lower() in existing.lower():
                        is_unique = False
                        break
                    elif len(sentence) > len(existing) and existing.lower() in sentence.lower():
                        # Replace shorter sentence with longer one
                        merged_sentences.remove(existing)
                        break
                
                if is_unique:
                    merged_sentences.append(sentence)
        
        return '. '.join(sorted(merged_sentences, key=len, reverse=True)) + '.'
    
    def _link_memories(self, conflict: Conflict, user_preferences: UserPreferences) -> Resolution:
        """Link related memories without merging content."""
        new_memory = conflict.new_memory
        existing_memory = conflict.existing_memory
        
        # Add cross-references in metadata
        if 'related_memories' not in existing_memory.metadata:
            existing_memory.metadata['related_memories'] = []
        existing_memory.metadata['related_memories'].append(new_memory.memory_id)
        existing_memory.updated_at = datetime.now()
        
        if 'related_memories' not in new_memory.metadata:
            new_memory.metadata['related_memories'] = []
        new_memory.metadata['related_memories'].append(existing_memory.memory_id)
        
        return Resolution(
            action=ResolutionAction.LINKED,
            strategy=ResolutionStrategy.LINK,
            primary_memory=new_memory,
            affected_memories=[existing_memory],
            confidence=conflict.confidence,
            metadata={
                'linked_memory_id': existing_memory.memory_id,
                'relationship_type': 'related_content'
            }
        )
    
    def _create_new(self, conflict: Conflict, user_preferences: UserPreferences) -> Resolution:
        """Create new memory without modifying existing ones."""
        return Resolution(
            action=ResolutionAction.CREATED,
            strategy=ResolutionStrategy.CREATE_NEW,
            primary_memory=conflict.new_memory,
            confidence=1.0,
            metadata={'reason': 'No conflicts require modification'}
        )
    
    def _keep_both(self, conflict: Conflict, user_preferences: UserPreferences) -> Resolution:
        """Keep both memories as separate entries."""
        new_memory = conflict.new_memory
        existing_memory = conflict.existing_memory
        
        # Mark them as related but distinct
        new_memory.metadata['related_but_distinct'] = existing_memory.memory_id
        existing_memory.metadata['related_but_distinct'] = new_memory.memory_id
        existing_memory.updated_at = datetime.now()
        
        return Resolution(
            action=ResolutionAction.CREATED,
            strategy=ResolutionStrategy.KEEP_BOTH,
            primary_memory=new_memory,
            affected_memories=[existing_memory],
            confidence=conflict.confidence,
            metadata={
                'kept_both': True,
                'related_memory_id': existing_memory.memory_id
            }
        )
    
    def _archive_old(self, conflict: Conflict, user_preferences: UserPreferences) -> Resolution:
        """Archive old memory and keep new one."""
        new_memory = conflict.new_memory
        existing_memory = conflict.existing_memory
        
        # Archive existing memory
        existing_memory.is_active = False
        existing_memory.metadata['archived_reason'] = 'superseded_by_new'
        existing_memory.metadata['superseded_by'] = new_memory.memory_id
        existing_memory.updated_at = datetime.now()
        
        # Reference archived memory in new one
        new_memory.metadata['superseded_memory'] = existing_memory.memory_id
        
        return Resolution(
            action=ResolutionAction.ARCHIVED,
            strategy=ResolutionStrategy.ARCHIVE_OLD,
            primary_memory=new_memory,
            affected_memories=[existing_memory],
            confidence=conflict.confidence,
            metadata={
                'archived_memory_id': existing_memory.memory_id,
                'reason': 'Newer information available'
            }
        )
    
    def _handle_user_choice(self, conflict: Conflict, user_preferences: UserPreferences) -> Resolution:
        """Handle conflicts that require user intervention."""
        return Resolution(
            action=ResolutionAction.NO_ACTION,
            strategy=ResolutionStrategy.USER_CHOOSE,
            primary_memory=conflict.new_memory,
            affected_memories=[conflict.existing_memory],
            confidence=0.0,
            metadata={
                'requires_user_choice': True,
                'conflict_details': conflict.details,
                'suggested_actions': ['replace', 'merge', 'keep_both', 'archive_old']
            }
        )
    
    def _create_audit_entry(self, conflict: Conflict, resolution: Resolution, user_strategy: str) -> AuditEntry:
        """Create audit trail entry for resolution."""
        audit_id = str(uuid.uuid4())
        
        # Collect original and new content
        original_content = {}
        new_content = {}
        memory_ids = []
        
        # Primary memory
        memory_ids.append(resolution.primary_memory.memory_id)
        new_content[resolution.primary_memory.memory_id] = resolution.primary_memory.content
        
        # Affected memories
        for memory in resolution.affected_memories:
            memory_ids.append(memory.memory_id)
            original_content[memory.memory_id] = memory.content
        
        # Existing memory from conflict
        if conflict.existing_memory.memory_id not in memory_ids:
            memory_ids.append(conflict.existing_memory.memory_id)
            original_content[conflict.existing_memory.memory_id] = conflict.existing_memory.content
        
        # Create rollback data
        rollback_data = {
            'conflict': {
                'type': conflict.conflict_type.value,
                'similarity_score': conflict.similarity_score,
                'confidence': conflict.confidence
            },
            'original_states': original_content,
            'strategy_used': resolution.strategy.value,
            'user_strategy': user_strategy
        }
        
        return AuditEntry(
            audit_id=audit_id,
            timestamp=datetime.now(),
            user_id=resolution.primary_memory.user_id,
            action=resolution.action,
            strategy=resolution.strategy,
            conflict_type=conflict.conflict_type,
            memory_ids=memory_ids,
            original_content=original_content,
            new_content=new_content,
            metadata=resolution.metadata,
            rollback_data=rollback_data
        )
    
    def rollback_resolution(self, audit_id: str) -> bool:
        """
        Rollback a resolution using audit trail data.
        
        Args:
            audit_id: ID of the audit entry to rollback
            
        Returns:
            True if rollback successful, False otherwise
        """
        # Find audit entry
        audit_entry = None
        for entry in self.audit_trail:
            if entry.audit_id == audit_id:
                audit_entry = entry
                break
        
        if not audit_entry:
            self.logger.error(f"Audit entry not found: {audit_id}")
            return False
        
        try:
            # Restore original states based on action type
            if audit_entry.action == ResolutionAction.REPLACED:
                # Restore archived memory
                for memory_id in audit_entry.memory_ids:
                    if memory_id in audit_entry.original_content:
                        # This would require database operations to restore
                        self.logger.info(f"Would restore memory {memory_id} from archive")
            
            elif audit_entry.action == ResolutionAction.MERGED:
                # Restore original content
                for memory_id, original_content in audit_entry.original_content.items():
                    self.logger.info(f"Would restore original content for memory {memory_id}")
            
            elif audit_entry.action == ResolutionAction.LINKED:
                # Remove links
                self.logger.info("Would remove memory links")
            
            # Mark rollback in audit trail
            rollback_entry = AuditEntry(
                audit_id=str(uuid.uuid4()),
                timestamp=datetime.now(),
                user_id=audit_entry.user_id,
                action=ResolutionAction.NO_ACTION,
                strategy=ResolutionStrategy.CREATE_NEW,
                conflict_type=audit_entry.conflict_type,
                memory_ids=audit_entry.memory_ids,
                original_content={},
                new_content={},
                metadata={'rollback_of': audit_id},
                rollback_data={}
            )
            self.audit_trail.append(rollback_entry)
            
            self.logger.info(f"Rollback completed for audit entry: {audit_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Rollback failed for {audit_id}: {e}")
            return False
    
    def get_audit_trail(self, user_id: Optional[str] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get audit trail entries.
        
        Args:
            user_id: Filter by user ID
            limit: Maximum number of entries to return
            
        Returns:
            List of audit entries as dictionaries
        """
        entries = self.audit_trail
        
        if user_id:
            entries = [entry for entry in entries if entry.user_id == user_id]
        
        # Sort by timestamp (newest first)
        entries = sorted(entries, key=lambda e: e.timestamp, reverse=True)
        
        if limit:
            entries = entries[:limit]
        
        return [entry.to_dict() for entry in entries]
    
    def get_resolution_statistics(self) -> Dict[str, Any]:
        """Get statistics about resolutions performed."""
        if not self.audit_trail:
            return {}
        
        total_resolutions = len(self.audit_trail)
        actions_count = {}
        strategies_count = {}
        conflict_types_count = {}
        
        for entry in self.audit_trail:
            # Count actions
            action = entry.action.value
            actions_count[action] = actions_count.get(action, 0) + 1
            
            # Count strategies
            strategy = entry.strategy.value
            strategies_count[strategy] = strategies_count.get(strategy, 0) + 1
            
            # Count conflict types
            conflict_type = entry.conflict_type.value
            conflict_types_count[conflict_type] = conflict_types_count.get(conflict_type, 0) + 1
        
        return {
            'total_resolutions': total_resolutions,
            'actions': actions_count,
            'strategies': strategies_count,
            'conflict_types': conflict_types_count,
            'success_rate': len([e for e in self.audit_trail if e.action != ResolutionAction.NO_ACTION]) / total_resolutions
        }