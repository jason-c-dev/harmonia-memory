"""
Authentication middleware for FastAPI application.

This module provides API key validation and user authentication.
"""
import logging
from typing import Callable, Optional
from fastapi import Request, Response, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware


logger = logging.getLogger(__name__)


class AuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware for API key authentication.
    """
    
    def __init__(self, app, api_keys: Optional[set] = None):
        """
        Initialize the authentication middleware.
        
        Args:
            app: The FastAPI application
            api_keys: Set of valid API keys (if None, uses environment)
        """
        super().__init__(app)
        self.api_keys = api_keys or self._load_api_keys()
        self.public_paths = {
            "/docs", "/redoc", "/openapi.json", 
            "/api/v1/health", "/api/v1/health/"
        }
    
    def _load_api_keys(self) -> set:
        """
        Load API keys from environment or configuration.
        
        Returns:
            set: Set of valid API keys
        """
        import os
        
        # For development, allow bypassing authentication
        if os.getenv("HARMONIA_ENV") == "development":
            return {"dev-key-123"}
        
        # Load from environment variable
        api_keys_str = os.getenv("HARMONIA_API_KEYS", "")
        if api_keys_str:
            return set(api_keys_str.split(","))
        
        # Default development key
        return {"harmonia-default-key"}
    
    def _is_public_path(self, path: str) -> bool:
        """
        Check if the path is publicly accessible.
        
        Args:
            path: The request path
            
        Returns:
            bool: True if path is public
        """
        return any(path.startswith(public) for public in self.public_paths)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Authenticate request using API key.
        
        Args:
            request: The incoming request
            call_next: The next middleware/endpoint
            
        Returns:
            Response: The response from downstream
        """
        # Skip authentication for public paths
        if self._is_public_path(request.url.path):
            return await call_next(request)
        
        # Extract API key from header
        api_key = request.headers.get("X-API-Key") or request.headers.get("Authorization")
        
        if api_key and api_key.startswith("Bearer "):
            api_key = api_key[7:]  # Remove "Bearer " prefix
        
        # Validate API key
        if not api_key:
            logger.warning(f"Missing API key for request to {request.url.path}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API key required",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        if api_key not in self.api_keys:
            logger.warning(f"Invalid API key for request to {request.url.path}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        # Add API key to request state for downstream use
        request.state.api_key = api_key
        
        logger.debug(f"Authenticated request to {request.url.path}")
        
        return await call_next(request)