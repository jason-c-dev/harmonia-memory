"""
Rate limiting middleware for FastAPI application.

This module provides rate limiting to prevent API abuse.
"""
import time
import logging
from typing import Callable, Dict, Optional
from collections import defaultdict
from fastapi import Request, Response, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware


logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware for rate limiting HTTP requests.
    
    Uses a simple in-memory sliding window algorithm.
    For production, consider using Redis or similar external store.
    """
    
    def __init__(self, app, rate_limit: int = 100, window_seconds: int = 60):
        """
        Initialize the rate limiting middleware.
        
        Args:
            app: The FastAPI application
            rate_limit: Number of requests allowed per window
            window_seconds: Time window in seconds
        """
        super().__init__(app)
        self.rate_limit = rate_limit
        self.window_seconds = window_seconds
        self.requests: Dict[str, list] = defaultdict(list)
        self.public_paths = {
            "/docs", "/redoc", "/openapi.json",
            "/api/v1/health", "/api/v1/health/"
        }
    
    def _get_client_id(self, request: Request) -> str:
        """
        Get client identifier for rate limiting.
        
        Args:
            request: The incoming request
            
        Returns:
            str: Client identifier (IP address)
        """
        # Use API key if available for more accurate identification
        api_key = getattr(request.state, 'api_key', None)
        if api_key:
            return f"api_key:{api_key}"
        
        # Fall back to IP address
        client_ip = request.client.host if request.client else "unknown"
        return f"ip:{client_ip}"
    
    def _is_public_path(self, path: str) -> bool:
        """
        Check if the path should be rate limited.
        
        Args:
            path: The request path
            
        Returns:
            bool: True if path is public (not rate limited)
        """
        return any(path.startswith(public) for public in self.public_paths)
    
    def _cleanup_old_requests(self, client_requests: list, current_time: float):
        """
        Remove old requests outside the time window.
        
        Args:
            client_requests: List of request timestamps for a client
            current_time: Current timestamp
        """
        window_start = current_time - self.window_seconds
        while client_requests and client_requests[0] < window_start:
            client_requests.pop(0)
    
    def _is_rate_limited(self, client_id: str, current_time: float) -> bool:
        """
        Check if client has exceeded rate limit.
        
        Args:
            client_id: Client identifier
            current_time: Current timestamp
            
        Returns:
            bool: True if rate limited
        """
        client_requests = self.requests[client_id]
        
        # Clean up old requests
        self._cleanup_old_requests(client_requests, current_time)
        
        # Check if rate limit exceeded
        if len(client_requests) >= self.rate_limit:
            return True
        
        # Add current request
        client_requests.append(current_time)
        return False
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Apply rate limiting to the request.
        
        Args:
            request: The incoming request
            call_next: The next middleware/endpoint
            
        Returns:
            Response: The response from downstream
        """
        # Skip rate limiting for public paths
        if self._is_public_path(request.url.path):
            return await call_next(request)
        
        current_time = time.time()
        client_id = self._get_client_id(request)
        
        # Check rate limit
        if self._is_rate_limited(client_id, current_time):
            logger.warning(f"Rate limit exceeded for client {client_id}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Maximum {self.rate_limit} requests per {self.window_seconds} seconds",
                headers={
                    "Retry-After": str(self.window_seconds),
                    "X-RateLimit-Limit": str(self.rate_limit),
                    "X-RateLimit-Window": str(self.window_seconds)
                }
            )
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        client_requests = self.requests[client_id]
        remaining = max(0, self.rate_limit - len(client_requests))
        
        response.headers["X-RateLimit-Limit"] = str(self.rate_limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(current_time + self.window_seconds))
        
        return response