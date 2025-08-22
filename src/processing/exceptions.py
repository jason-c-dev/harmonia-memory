"""
Exception classes for memory processing operations.

This module defines custom exceptions for different error conditions
that can occur during memory processing, conflict resolution, and storage.
"""


class HarmoniaException(Exception):
    """Base exception class for Harmonia-specific errors."""
    pass


class ValidationError(HarmoniaException):
    """Raised when input validation fails."""
    pass


class MemoryProcessingError(HarmoniaException):
    """Raised when memory processing fails."""
    pass


class ConflictResolutionError(HarmoniaException):
    """Raised when conflict resolution fails."""
    pass


class MemoryNotFoundError(HarmoniaException):
    """Raised when a requested memory is not found."""
    pass


class UserNotFoundError(HarmoniaException):
    """Raised when a user is not found."""
    pass


class DatabaseError(HarmoniaException):
    """Raised when database operations fail."""
    pass


class LLMServiceError(HarmoniaException):
    """Raised when LLM service operations fail."""
    pass


class SearchEngineError(HarmoniaException):
    """Raised when search engine operations fail."""
    pass


class ConfigurationError(HarmoniaException):
    """Raised when configuration is invalid or missing."""
    pass


class PermissionError(HarmoniaException):
    """Raised when user lacks permission for an operation."""
    pass


class RateLimitError(HarmoniaException):
    """Raised when rate limits are exceeded."""
    pass


class ExportError(HarmoniaException):
    """Raised when memory export operations fail."""
    pass


class TemporalResolutionError(HarmoniaException):
    """Raised when temporal reference resolution fails."""
    pass


class EntityExtractionError(HarmoniaException):
    """Raised when entity extraction fails."""
    pass


class ConfidenceScoringError(HarmoniaException):
    """Raised when confidence scoring fails."""
    pass