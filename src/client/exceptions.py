"""
Exception classes for the Harmonia Python client.

This module defines client-specific exceptions for different error
conditions that can occur when interacting with the API.
"""


class HarmoniaClientError(Exception):
    """Base exception class for Harmonia client errors."""
    
    def __init__(self, message: str, status_code: int = None, response: dict = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.response = response


class AuthenticationError(HarmoniaClientError):
    """Raised when authentication fails."""
    pass


class RateLimitError(HarmoniaClientError):
    """Raised when rate limits are exceeded."""
    
    def __init__(self, message: str, retry_after: int = None, **kwargs):
        super().__init__(message, **kwargs)
        self.retry_after = retry_after


class ValidationError(HarmoniaClientError):
    """Raised when request validation fails."""
    pass


class NotFoundError(HarmoniaClientError):
    """Raised when a resource is not found."""
    pass


class ServerError(HarmoniaClientError):
    """Raised when the server returns an error."""
    pass


class NetworkError(HarmoniaClientError):
    """Raised when network operations fail."""
    pass


class TimeoutError(HarmoniaClientError):
    """Raised when requests timeout."""
    pass