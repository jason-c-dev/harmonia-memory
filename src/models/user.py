"""
User model for the Harmonia Memory Storage System.
"""
import uuid
from datetime import datetime
from typing import Dict, Optional

from .base import BaseModel, ValidationError


class User(BaseModel):
    """
    User model representing a system user.
    
    Attributes:
        user_id: Unique identifier for the user
        created_at: When the user was created
        updated_at: When the user was last updated
        settings: User-specific settings (JSON)
        metadata: Additional user metadata (JSON)
    """
    
    REQUIRED_FIELDS = ['user_id']
    
    FIELD_TYPES = {
        'user_id': str,
        'created_at': datetime,
        'updated_at': datetime,
        'settings': dict,
        'metadata': dict
    }
    
    DEFAULTS = {
        'created_at': datetime.now,
        'updated_at': datetime.now,
        'settings': dict,
        'metadata': dict
    }
    
    def _validate_field(self, field: str, value):
        """Custom validation for User fields."""
        # Call parent validation first
        value = super()._validate_field(field, value)
        
        # User ID validation
        if field == 'user_id':
            if not value or not isinstance(value, str):
                raise ValidationError("user_id must be a non-empty string")
            if len(value) > 255:
                raise ValidationError("user_id must be 255 characters or less")
        
        # Settings validation
        elif field == 'settings':
            if value is not None and not isinstance(value, dict):
                raise ValidationError("settings must be a dictionary")
        
        # Metadata validation
        elif field == 'metadata':
            if value is not None and not isinstance(value, dict):
                raise ValidationError("metadata must be a dictionary")
        
        return value
    
    def get_primary_key(self) -> str:
        """Get the primary key value (user_id)."""
        return self.user_id
    
    @classmethod
    def create_new(cls, user_id: str, settings: Optional[Dict] = None, 
                   metadata: Optional[Dict] = None) -> 'User':
        """
        Create a new user with default values.
        
        Args:
            user_id: Unique identifier for the user
            settings: Optional user settings
            metadata: Optional user metadata
            
        Returns:
            New User instance
        """
        return cls(
            user_id=user_id,
            settings=settings or {},
            metadata=metadata or {}
        )
    
    @classmethod
    def generate_id(cls) -> str:
        """
        Generate a new unique user ID.
        
        Returns:
            Generated user ID
        """
        return f"user_{uuid.uuid4().hex[:8]}"
    
    def update_settings(self, **settings) -> None:
        """
        Update user settings.
        
        Args:
            **settings: Settings to update
        """
        current_settings = self.settings.copy()
        current_settings.update(settings)
        self.settings = current_settings
        self.updated_at = datetime.now()
    
    def update_metadata(self, **metadata) -> None:
        """
        Update user metadata.
        
        Args:
            **metadata: Metadata to update
        """
        current_metadata = self.metadata.copy()
        current_metadata.update(metadata)
        self.metadata = current_metadata
        self.updated_at = datetime.now()
    
    def get_setting(self, key: str, default=None):
        """
        Get a specific setting value.
        
        Args:
            key: Setting key
            default: Default value if key not found
            
        Returns:
            Setting value or default
        """
        return self.settings.get(key, default)
    
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