"""
Session model for the Harmonia Memory Storage System.
"""
import uuid
from datetime import datetime
from typing import Dict, Optional

from .base import BaseModel, ValidationError


class Session(BaseModel):
    """
    Session model representing a user chat session.
    
    Attributes:
        session_id: Unique identifier for the session
        user_id: ID of the user who owns this session
        started_at: When the session was started
        ended_at: When the session ended (None if still active)
        message_count: Number of messages in this session
        memories_created: Number of memories created during this session
        metadata: Additional session metadata (JSON)
    """
    
    REQUIRED_FIELDS = ['session_id', 'user_id']
    
    FIELD_TYPES = {
        'session_id': str,
        'user_id': str,
        'started_at': datetime,
        'ended_at': Optional[datetime],
        'message_count': int,
        'memories_created': int,
        'metadata': dict
    }
    
    DEFAULTS = {
        'started_at': datetime.now,
        'message_count': 0,
        'memories_created': 0,
        'metadata': dict
    }
    
    def _validate_field(self, field: str, value):
        """Custom validation for Session fields."""
        # Call parent validation first
        value = super()._validate_field(field, value)
        
        # Session ID validation
        if field == 'session_id':
            if not value or not isinstance(value, str):
                raise ValidationError("session_id must be a non-empty string")
            if len(value) > 255:
                raise ValidationError("session_id must be 255 characters or less")
        
        # User ID validation
        elif field == 'user_id':
            if not value or not isinstance(value, str):
                raise ValidationError("user_id must be a non-empty string")
            if len(value) > 255:
                raise ValidationError("user_id must be 255 characters or less")
        
        # Message count validation
        elif field == 'message_count':
            if value is not None and (not isinstance(value, int) or value < 0):
                raise ValidationError("message_count must be a non-negative integer")
        
        # Memories created validation
        elif field == 'memories_created':
            if value is not None and (not isinstance(value, int) or value < 0):
                raise ValidationError("memories_created must be a non-negative integer")
        
        # Metadata validation
        elif field == 'metadata':
            if value is not None and not isinstance(value, dict):
                raise ValidationError("metadata must be a dictionary")
        
        # Date logic validation
        elif field == 'ended_at':
            if value is not None and hasattr(self, 'started_at') and self.started_at:
                if value < self.started_at:
                    raise ValidationError("ended_at cannot be before started_at")
        
        return value
    
    def get_primary_key(self) -> str:
        """Get the primary key value (session_id)."""
        return self.session_id
    
    @classmethod
    def create_new(cls, user_id: str, metadata: Optional[Dict] = None) -> 'Session':
        """
        Create a new session with generated ID.
        
        Args:
            user_id: ID of the user who owns this session
            metadata: Optional session metadata
            
        Returns:
            New Session instance
        """
        session_id = cls.generate_id()
        return cls(
            session_id=session_id,
            user_id=user_id,
            metadata=metadata or {}
        )
    
    @classmethod
    def generate_id(cls) -> str:
        """
        Generate a new unique session ID.
        
        Returns:
            Generated session ID
        """
        return f"sess_{uuid.uuid4().hex[:10]}"
    
    def is_active(self) -> bool:
        """
        Check if session is currently active.
        
        Returns:
            True if session is active (not ended)
        """
        return self.ended_at is None
    
    def end_session(self, ended_at: Optional[datetime] = None) -> None:
        """
        End the session.
        
        Args:
            ended_at: When the session ended (defaults to now)
        """
        self.ended_at = ended_at or datetime.now()
    
    def add_message(self) -> None:
        """Increment the message count."""
        self.message_count += 1
    
    def add_memory(self) -> None:
        """Increment the memories created count."""
        self.memories_created += 1
    
    def get_duration_minutes(self) -> Optional[float]:
        """
        Get session duration in minutes.
        
        Returns:
            Duration in minutes, or None if session is still active
        """
        if not self.ended_at:
            return None
        
        delta = self.ended_at - self.started_at
        return delta.total_seconds() / 60.0
    
    def get_current_duration_minutes(self) -> float:
        """
        Get current session duration in minutes (even if still active).
        
        Returns:
            Duration in minutes from start to now or end time
        """
        end_time = self.ended_at or datetime.now()
        delta = end_time - self.started_at
        return delta.total_seconds() / 60.0
    
    def update_metadata(self, **metadata) -> None:
        """
        Update session metadata.
        
        Args:
            **metadata: Metadata to update
        """
        current_metadata = self.metadata.copy()
        current_metadata.update(metadata)
        self.metadata = current_metadata
    
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
    
    def get_memories_per_message_ratio(self) -> float:
        """
        Get the ratio of memories created per message.
        
        Returns:
            Ratio of memories to messages (0.0 if no messages)
        """
        if self.message_count == 0:
            return 0.0
        return self.memories_created / self.message_count
    
    def get_summary(self) -> Dict[str, any]:
        """
        Get a summary of the session.
        
        Returns:
            Dictionary with session summary
        """
        return {
            'session_id': self.session_id,
            'user_id': self.user_id,
            'is_active': self.is_active(),
            'duration_minutes': self.get_current_duration_minutes(),
            'message_count': self.message_count,
            'memories_created': self.memories_created,
            'memory_ratio': self.get_memories_per_message_ratio(),
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'ended_at': self.ended_at.isoformat() if self.ended_at else None
        }