"""
Category model for the Harmonia Memory Storage System.
"""
import uuid
from datetime import datetime
from typing import Optional

from .base import BaseModel, ValidationError


class Category(BaseModel):
    """
    Category model representing a memory category.
    
    Attributes:
        category_id: Unique identifier for the category
        name: Human-readable category name
        description: Description of the category
        parent_category_id: ID of parent category (for hierarchical categories)
        created_at: When the category was created
    """
    
    REQUIRED_FIELDS = ['category_id', 'name']
    
    FIELD_TYPES = {
        'category_id': str,
        'name': str,
        'description': Optional[str],
        'parent_category_id': Optional[str],
        'created_at': datetime
    }
    
    DEFAULTS = {
        'created_at': datetime.now
    }
    
    def _validate_field(self, field: str, value):
        """Custom validation for Category fields."""
        # Call parent validation first
        value = super()._validate_field(field, value)
        
        # Category ID validation
        if field == 'category_id':
            if not value or not isinstance(value, str):
                raise ValidationError("category_id must be a non-empty string")
            if len(value) > 100:
                raise ValidationError("category_id must be 100 characters or less")
            # Category IDs should be URL-safe
            if not value.replace('_', '').replace('-', '').isalnum():
                raise ValidationError("category_id must contain only letters, numbers, hyphens, and underscores")
        
        # Name validation
        elif field == 'name':
            if not value or not isinstance(value, str):
                raise ValidationError("name must be a non-empty string")
            if len(value) > 200:
                raise ValidationError("name must be 200 characters or less")
        
        # Description validation
        elif field == 'description':
            if value is not None and len(value) > 1000:
                raise ValidationError("description must be 1000 characters or less")
        
        # Parent category validation
        elif field == 'parent_category_id':
            if value is not None:
                if not isinstance(value, str) or len(value) > 100:
                    raise ValidationError("parent_category_id must be a string of 100 characters or less")
                # Prevent self-reference
                if hasattr(self, 'category_id') and value == self.category_id:
                    raise ValidationError("category cannot be its own parent")
        
        return value
    
    def get_primary_key(self) -> str:
        """Get the primary key value (category_id)."""
        return self.category_id
    
    @classmethod
    def create_new(cls, name: str, description: Optional[str] = None,
                   parent_category_id: Optional[str] = None) -> 'Category':
        """
        Create a new category with generated ID.
        
        Args:
            name: Human-readable category name
            description: Description of the category
            parent_category_id: ID of parent category
            
        Returns:
            New Category instance
        """
        category_id = cls.generate_id_from_name(name)
        return cls(
            category_id=category_id,
            name=name,
            description=description,
            parent_category_id=parent_category_id
        )
    
    @classmethod
    def generate_id_from_name(cls, name: str) -> str:
        """
        Generate a category ID from the name.
        
        Args:
            name: Category name
            
        Returns:
            Generated category ID
        """
        # Convert name to lowercase, replace spaces and special chars with underscores
        category_id = name.lower()
        # Replace spaces and special characters with underscores
        import re
        category_id = re.sub(r'[^a-z0-9_-]', '_', category_id)
        # Replace multiple underscores with single underscore
        category_id = re.sub(r'_+', '_', category_id)
        # Remove leading/trailing underscores
        category_id = category_id.strip('_')
        
        # Ensure it's not empty and not too long
        if not category_id:
            category_id = f"category_{uuid.uuid4().hex[:8]}"
        elif len(category_id) > 80:
            category_id = category_id[:80]
        
        return category_id
    
    @classmethod
    def generate_id(cls) -> str:
        """
        Generate a new unique category ID.
        
        Returns:
            Generated category ID
        """
        return f"cat_{uuid.uuid4().hex[:8]}"
    
    def is_root_category(self) -> bool:
        """
        Check if this is a root category (no parent).
        
        Returns:
            True if this is a root category
        """
        return self.parent_category_id is None
    
    def is_child_of(self, parent_id: str) -> bool:
        """
        Check if this category is a child of the specified parent.
        
        Args:
            parent_id: Parent category ID to check
            
        Returns:
            True if this category is a child of the specified parent
        """
        return self.parent_category_id == parent_id
    
    def set_parent(self, parent_category_id: Optional[str]) -> None:
        """
        Set the parent category.
        
        Args:
            parent_category_id: ID of the parent category (None for root)
            
        Raises:
            ValidationError: If trying to set self as parent
        """
        if parent_category_id == self.category_id:
            raise ValidationError("category cannot be its own parent")
        self.parent_category_id = parent_category_id
    
    def update_description(self, description: Optional[str]) -> None:
        """
        Update the category description.
        
        Args:
            description: New description
        """
        self.description = description
    
    def get_display_name(self) -> str:
        """
        Get the display name for the category.
        
        Returns:
            Category name formatted for display
        """
        return self.name
    
    def get_path_separator(self) -> str:
        """
        Get the separator used for category paths.
        
        Returns:
            Path separator string
        """
        return " > "
    
    @classmethod
    def create_default_categories(cls):
        """
        Create default system categories.
        
        Returns:
            List of default Category instances
        """
        categories = [
            cls(category_id='personal', name='Personal', 
                description='Personal information, preferences, and experiences'),
            cls(category_id='work', name='Work', 
                description='Work-related information and professional activities'),
            cls(category_id='preferences', name='Preferences', 
                description='User preferences and settings'),
            cls(category_id='facts', name='Facts', 
                description='Factual information and knowledge'),
            cls(category_id='goals', name='Goals', 
                description='Personal and professional goals'),
            cls(category_id='events', name='Events', 
                description='Important events and dates'),
            cls(category_id='relationships', name='Relationships', 
                description='Information about people and relationships'),
            cls(category_id='other', name='Other', 
                description='Miscellaneous information that doesn\'t fit other categories')
        ]
        return categories