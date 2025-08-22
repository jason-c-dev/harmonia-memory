"""
Memory model for the Harmonia Memory Storage System.
"""
import uuid
from datetime import datetime
from typing import Dict, Optional

from .base import BaseModel, ValidationError


class Memory(BaseModel):
    """
    Memory model representing a stored memory.
    
    Attributes:
        memory_id: Unique identifier for the memory
        user_id: ID of the user who owns this memory
        content: The processed memory content
        original_message: The original message that generated this memory
        category: Memory category
        confidence_score: Confidence score for the memory extraction
        timestamp: When the memory event occurred
        created_at: When the memory was created in the system
        updated_at: When the memory was last updated
        metadata: Additional memory metadata (JSON)
        embedding: Vector embedding for semantic search (BLOB)
        is_active: Whether the memory is active (not soft-deleted)
    """
    
    REQUIRED_FIELDS = ['memory_id', 'user_id', 'content']
    
    FIELD_TYPES = {
        'memory_id': str,
        'user_id': str,
        'content': str,
        'original_message': Optional[str],
        'category': Optional[str],
        'confidence_score': Optional[float],
        'timestamp': Optional[datetime],
        'created_at': datetime,
        'updated_at': datetime,
        'metadata': dict,
        'embedding': Optional[bytes],
        'is_active': bool
    }
    
    DEFAULTS = {
        'created_at': datetime.now,
        'updated_at': datetime.now,
        'metadata': dict,
        'is_active': True
    }
    
    def _validate_field(self, field: str, value):
        """Custom validation for Memory fields."""
        # Call parent validation first
        value = super()._validate_field(field, value)
        
        # Memory ID validation
        if field == 'memory_id':
            if not value or not isinstance(value, str):
                raise ValidationError("memory_id must be a non-empty string")
            if len(value) > 255:
                raise ValidationError("memory_id must be 255 characters or less")
        
        # User ID validation
        elif field == 'user_id':
            if not value or not isinstance(value, str):
                raise ValidationError("user_id must be a non-empty string")
            if len(value) > 255:
                raise ValidationError("user_id must be 255 characters or less")
        
        # Content validation
        elif field == 'content':
            if not value or not isinstance(value, str):
                raise ValidationError("content must be a non-empty string")
            if len(value) > 10000:  # Reasonable limit for memory content
                raise ValidationError("content must be 10000 characters or less")
        
        # Category validation
        elif field == 'category':
            if value is not None and (not isinstance(value, str) or len(value) > 100):
                raise ValidationError("category must be a string of 100 characters or less")
        
        # Confidence score validation
        elif field == 'confidence_score':
            if value is not None:
                if not isinstance(value, (int, float)):
                    raise ValidationError("confidence_score must be a number")
                if not 0.0 <= value <= 1.0:
                    raise ValidationError("confidence_score must be between 0.0 and 1.0")
        
        # Original message validation
        elif field == 'original_message':
            if value is not None and len(value) > 50000:  # Large limit for original messages
                raise ValidationError("original_message must be 50000 characters or less")
        
        # Metadata validation
        elif field == 'metadata':
            if value is not None and not isinstance(value, dict):
                raise ValidationError("metadata must be a dictionary")
        
        # Boolean validation
        elif field == 'is_active':
            if value is not None and not isinstance(value, bool):
                raise ValidationError("is_active must be a boolean")
        
        return value
    
    def get_primary_key(self) -> str:
        """Get the primary key value (memory_id)."""
        return self.memory_id
    
    @classmethod
    def create_new(cls, user_id: str, content: str, original_message: Optional[str] = None,
                   category: Optional[str] = None, confidence_score: Optional[float] = None,
                   timestamp: Optional[datetime] = None, metadata: Optional[Dict] = None,
                   embedding: Optional[bytes] = None) -> 'Memory':
        """
        Create a new memory with generated ID.
        
        Args:
            user_id: ID of the user who owns this memory
            content: The processed memory content
            original_message: The original message that generated this memory
            category: Memory category
            confidence_score: Confidence score for the memory extraction
            timestamp: When the memory event occurred
            metadata: Additional memory metadata
            embedding: Vector embedding for semantic search
            
        Returns:
            New Memory instance
        """
        memory_id = cls.generate_id()
        return cls(
            memory_id=memory_id,
            user_id=user_id,
            content=content,
            original_message=original_message,
            category=category,
            confidence_score=confidence_score,
            timestamp=timestamp,
            metadata=metadata or {},
            embedding=embedding
        )
    
    @classmethod
    def generate_id(cls) -> str:
        """
        Generate a new unique memory ID.
        
        Returns:
            Generated memory ID
        """
        return f"mem_{uuid.uuid4().hex[:12]}"
    
    def update_content(self, content: str, confidence_score: Optional[float] = None) -> None:
        """
        Update memory content and confidence score.
        
        Args:
            content: New content
            confidence_score: New confidence score
        """
        self.content = content
        if confidence_score is not None:
            self.confidence_score = confidence_score
        self.updated_at = datetime.now()
    
    def update_metadata(self, **metadata) -> None:
        """
        Update memory metadata.
        
        Args:
            **metadata: Metadata to update
        """
        current_metadata = self.metadata.copy()
        current_metadata.update(metadata)
        self.metadata = current_metadata
        self.updated_at = datetime.now()
    
    def get_metadata(self, key: str, default=None):
        """
        Get a specific metadata value.
        
        Args:
            key: Metadata key
            default: Default value if key not found
            
        Returns:
            Metadata value or default
        """
        return self.metadata.get(key, default)
    
    def soft_delete(self) -> None:
        """Mark memory as inactive (soft delete)."""
        self.is_active = False
        self.updated_at = datetime.now()
    
    def restore(self) -> None:
        """Restore soft-deleted memory."""
        self.is_active = True
        self.updated_at = datetime.now()
    
    def set_category(self, category: Optional[str]) -> None:
        """
        Set the memory category.
        
        Args:
            category: Category to set
        """
        self.category = category
        self.updated_at = datetime.now()
    
    def get_age_days(self) -> int:
        """
        Get the age of the memory in days.
        
        Returns:
            Age in days since creation
        """
        if not self.created_at:
            return 0
        delta = datetime.now() - self.created_at
        return delta.days
    
    def is_recent(self, days: int = 7) -> bool:
        """
        Check if memory is recent (within specified days).
        
        Args:
            days: Number of days to consider recent
            
        Returns:
            True if memory is recent
        """
        return self.get_age_days() <= days