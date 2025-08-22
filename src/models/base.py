"""
Base model class with validation and serialization capabilities.
"""
import json
import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional, Type, Union, get_type_hints

from core.logging import get_logger

logger = get_logger(__name__)


class ValidationError(Exception):
    """Exception raised when model validation fails."""
    pass


class BaseModel(ABC):
    """
    Base model class providing validation, serialization, and common functionality.
    """
    
    # Define required fields that must be provided (override in subclasses)
    REQUIRED_FIELDS: List[str] = []
    
    # Define field types for validation (override in subclasses)
    FIELD_TYPES: Dict[str, Type] = {}
    
    # Define default values (override in subclasses)
    DEFAULTS: Dict[str, Any] = {}
    
    def __init__(self, **kwargs):
        """
        Initialize model with field validation.
        
        Args:
            **kwargs: Field values for the model
            
        Raises:
            ValidationError: If validation fails
        """
        # Apply defaults first
        for field, default_value in self.DEFAULTS.items():
            if field not in kwargs:
                if callable(default_value):
                    kwargs[field] = default_value()
                else:
                    kwargs[field] = default_value
        
        # Validate and set fields
        self._fields = {}
        self._validate_and_set_fields(kwargs)
    
    def _validate_and_set_fields(self, fields: Dict[str, Any]) -> None:
        """
        Validate and set model fields.
        
        Args:
            fields: Dictionary of field names and values
            
        Raises:
            ValidationError: If validation fails
        """
        # Check required fields
        missing_fields = []
        for field in self.REQUIRED_FIELDS:
            if field not in fields or fields[field] is None:
                missing_fields.append(field)
        
        if missing_fields:
            raise ValidationError(f"Missing required fields: {missing_fields}")
        
        # Set all fields from FIELD_TYPES with None defaults for optional fields
        for field, field_type in self.FIELD_TYPES.items():
            if field not in fields:
                # Check if field is Optional (Union with None)
                if hasattr(field_type, '__origin__') and field_type.__origin__ is Union:
                    if type(None) in field_type.__args__:
                        fields[field] = None
        
        # Validate field types and set values
        for field, value in fields.items():
            if field in self.FIELD_TYPES:
                expected_type = self.FIELD_TYPES[field]
                if value is not None and not self._is_valid_type(value, expected_type):
                    raise ValidationError(
                        f"Field '{field}' expected {expected_type.__name__}, got {type(value).__name__}"
                    )
            
            # Custom field validation
            validated_value = self._validate_field(field, value)
            self._fields[field] = validated_value
    
    def _is_valid_type(self, value: Any, expected_type: Type) -> bool:
        """
        Check if value matches expected type, handling special cases.
        
        Args:
            value: Value to check
            expected_type: Expected type
            
        Returns:
            True if value is valid type
        """
        # Handle Union types (e.g., Optional[str] = Union[str, None])
        if hasattr(expected_type, '__origin__'):
            if expected_type.__origin__ is Union:
                return any(self._is_valid_type(value, arg) for arg in expected_type.__args__)
        
        # Handle datetime strings
        if expected_type is datetime and isinstance(value, str):
            try:
                datetime.fromisoformat(value.replace('Z', '+00:00'))
                return True
            except ValueError:
                return False
        
        # Handle JSON fields (dict/list stored as strings)
        if expected_type in (dict, list) and isinstance(value, str):
            try:
                json.loads(value)
                return True
            except (json.JSONDecodeError, TypeError):
                return False
        
        return isinstance(value, expected_type)
    
    def _validate_field(self, field: str, value: Any) -> Any:
        """
        Custom field validation. Override in subclasses for specific validation.
        
        Args:
            field: Field name
            value: Field value
            
        Returns:
            Validated and possibly transformed value
            
        Raises:
            ValidationError: If validation fails
        """
        # Convert datetime strings to datetime objects
        if field.endswith('_at') or field == 'timestamp':
            if isinstance(value, str) and value:
                try:
                    return datetime.fromisoformat(value.replace('Z', '+00:00'))
                except ValueError as e:
                    raise ValidationError(f"Invalid datetime format for {field}: {value}")
        
        # Parse JSON fields
        if field in ('metadata', 'settings') and isinstance(value, str):
            try:
                return json.loads(value) if value else {}
            except json.JSONDecodeError as e:
                raise ValidationError(f"Invalid JSON for {field}: {value}")
        
        return value
    
    def __getattr__(self, name: str) -> Any:
        """Get field value."""
        if name in self._fields:
            return self._fields[name]
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")
    
    def __setattr__(self, name: str, value: Any) -> None:
        """Set field value with validation."""
        if name.startswith('_') or name in ('REQUIRED_FIELDS', 'FIELD_TYPES', 'DEFAULTS'):
            super().__setattr__(name, value)
        else:
            if not hasattr(self, '_fields'):
                super().__setattr__(name, value)
            else:
                # Validate single field update
                if name in self.FIELD_TYPES:
                    expected_type = self.FIELD_TYPES[name]
                    if value is not None and not self._is_valid_type(value, expected_type):
                        raise ValidationError(
                            f"Field '{name}' expected {expected_type.__name__}, got {type(value).__name__}"
                        )
                
                validated_value = self._validate_field(name, value)
                self._fields[name] = validated_value
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert model to dictionary.
        
        Returns:
            Dictionary representation of the model
        """
        result = {}
        for field, value in self._fields.items():
            if isinstance(value, datetime):
                result[field] = value.isoformat()
            elif isinstance(value, (dict, list)):
                result[field] = value
            else:
                result[field] = value
        return result
    
    def to_json(self) -> str:
        """
        Convert model to JSON string.
        
        Returns:
            JSON string representation of the model
        """
        return json.dumps(self.to_dict(), default=str, ensure_ascii=False)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BaseModel':
        """
        Create model instance from dictionary.
        
        Args:
            data: Dictionary with model data
            
        Returns:
            Model instance
        """
        return cls(**data)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'BaseModel':
        """
        Create model instance from JSON string.
        
        Args:
            json_str: JSON string with model data
            
        Returns:
            Model instance
            
        Raises:
            ValidationError: If JSON parsing fails
        """
        try:
            data = json.loads(json_str)
            return cls.from_dict(data)
        except json.JSONDecodeError as e:
            raise ValidationError(f"Invalid JSON: {e}")
    
    def update(self, **kwargs) -> None:
        """
        Update model fields with validation.
        
        Args:
            **kwargs: Fields to update
            
        Raises:
            ValidationError: If validation fails
        """
        # Create updated fields dict
        updated_fields = self._fields.copy()
        updated_fields.update(kwargs)
        
        # Validate all fields together
        self._validate_and_set_fields(updated_fields)
    
    def validate(self) -> bool:
        """
        Validate current model state.
        
        Returns:
            True if model is valid
            
        Raises:
            ValidationError: If validation fails
        """
        self._validate_and_set_fields(self._fields)
        return True
    
    def __repr__(self) -> str:
        """String representation of the model."""
        class_name = self.__class__.__name__
        fields = ', '.join(f'{k}={repr(v)}' for k, v in self._fields.items())
        return f'{class_name}({fields})'
    
    def __eq__(self, other) -> bool:
        """Check equality with another model."""
        if not isinstance(other, self.__class__):
            return False
        return self._fields == other._fields
    
    @abstractmethod
    def get_primary_key(self) -> str:
        """
        Get the primary key value for this model.
        
        Returns:
            Primary key value
        """
        pass