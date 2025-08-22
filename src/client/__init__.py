"""
Python client library for Harmonia Memory Storage API.

This package provides a convenient Python interface for interacting
with the Harmonia Memory Storage System API.
"""

from .harmonia_client import HarmoniaClient, HarmoniaResponse
from .exceptions import (
    HarmoniaClientError, AuthenticationError, RateLimitError,
    ValidationError, NotFoundError, ServerError
)

__all__ = [
    'HarmoniaClient',
    'HarmoniaResponse',
    'HarmoniaClientError',
    'AuthenticationError', 
    'RateLimitError',
    'ValidationError',
    'NotFoundError',
    'ServerError'
]

__version__ = '1.0.0'