"""
Main Harmonia client implementation.

This module provides the HarmoniaClient class for interacting with
the Harmonia Memory Storage API.
"""
import time
import logging
from typing import Optional, Dict, Any, List, Union
from datetime import datetime
from urllib.parse import urljoin, urlencode
import json

try:
    import requests
except ImportError:
    raise ImportError("The 'requests' library is required. Install with: pip install requests")

from .exceptions import (
    HarmoniaClientError, AuthenticationError, RateLimitError,
    ValidationError, NotFoundError, ServerError, NetworkError, TimeoutError
)


logger = logging.getLogger(__name__)


class HarmoniaResponse:
    """
    Wrapper for API responses with convenient access methods.
    """
    
    def __init__(self, response: requests.Response):
        self.status_code = response.status_code
        self.headers = response.headers
        self.raw_response = response
        
        try:
            self.data = response.json()
        except ValueError:
            self.data = response.text
    
    @property
    def success(self) -> bool:
        """Check if the response indicates success."""
        return self.data.get('success', False) if isinstance(self.data, dict) else False
    
    @property
    def error(self) -> Optional[str]:
        """Get error message if response failed."""
        if isinstance(self.data, dict) and not self.success:
            return self.data.get('message') or self.data.get('error')
        return None


class HarmoniaClient:
    """
    Python client for the Harmonia Memory Storage API.
    
    This client provides convenient methods for storing, searching,
    and managing memories through the Harmonia API.
    """
    
    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        api_key: Optional[str] = None,
        timeout: int = 30,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        verify_ssl: bool = True
    ):
        """
        Initialize the Harmonia client.
        
        Args:
            base_url: Base URL of the Harmonia API server
            api_key: API key for authentication (if required)
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            retry_delay: Delay between retries in seconds
            verify_ssl: Whether to verify SSL certificates
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
        self.session = requests.Session()
        self.session.verify = verify_ssl
        
        # Set default headers
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'harmonia-python-client/1.0.0'
        })
        
        # Add API key to headers if provided
        if api_key:
            self.session.headers['X-API-Key'] = api_key
    
    def _make_url(self, endpoint: str) -> str:
        """
        Construct full URL for an endpoint.
        
        Args:
            endpoint: API endpoint path
            
        Returns:
            str: Full URL
        """
        return urljoin(self.base_url + '/', endpoint.lstrip('/'))
    
    def _handle_response(self, response: requests.Response) -> HarmoniaResponse:
        """
        Handle API response and raise appropriate exceptions.
        
        Args:
            response: Raw HTTP response
            
        Returns:
            HarmoniaResponse: Wrapped response
            
        Raises:
            Various HarmoniaClientError subclasses based on status code
        """
        harmonia_response = HarmoniaResponse(response)
        
        if response.status_code == 200:
            return harmonia_response
        
        # Extract error message
        error_msg = "Unknown error"
        if isinstance(harmonia_response.data, dict):
            error_msg = (
                harmonia_response.data.get('message') or
                harmonia_response.data.get('detail') or
                harmonia_response.data.get('error') or
                error_msg
            )
        elif isinstance(harmonia_response.data, str):
            error_msg = harmonia_response.data
        
        # Raise appropriate exception based on status code
        if response.status_code == 401:
            raise AuthenticationError(error_msg, response.status_code, harmonia_response.data)
        elif response.status_code == 404:
            raise NotFoundError(error_msg, response.status_code, harmonia_response.data)
        elif response.status_code == 400:
            raise ValidationError(error_msg, response.status_code, harmonia_response.data)
        elif response.status_code == 429:
            retry_after = response.headers.get('Retry-After')
            retry_after = int(retry_after) if retry_after else None
            raise RateLimitError(error_msg, retry_after, status_code=response.status_code, response=harmonia_response.data)
        elif 500 <= response.status_code < 600:
            raise ServerError(error_msg, response.status_code, harmonia_response.data)
        else:
            raise HarmoniaClientError(error_msg, response.status_code, harmonia_response.data)
    
    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> HarmoniaResponse:
        """
        Make HTTP request with retry logic.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint
            params: Query parameters
            data: Request body data
            **kwargs: Additional requests parameters
            
        Returns:
            HarmoniaResponse: API response
        """
        url = self._make_url(endpoint)
        
        # Prepare request parameters
        request_kwargs = {
            'timeout': self.timeout,
            'params': params,
            **kwargs
        }
        
        if data is not None:
            request_kwargs['json'] = data
        
        # Retry loop
        last_exception = None
        for attempt in range(self.max_retries + 1):
            try:
                logger.debug(f"Making {method} request to {url} (attempt {attempt + 1})")
                
                response = self.session.request(method, url, **request_kwargs)
                return self._handle_response(response)
                
            except requests.exceptions.Timeout as e:
                last_exception = TimeoutError(f"Request timed out after {self.timeout} seconds")
            except requests.exceptions.ConnectionError as e:
                last_exception = NetworkError(f"Connection error: {str(e)}")
            except requests.exceptions.RequestException as e:
                last_exception = NetworkError(f"Request error: {str(e)}")
            except RateLimitError as e:
                # Don't retry rate limit errors immediately
                if e.retry_after:
                    logger.warning(f"Rate limited, waiting {e.retry_after} seconds")
                    time.sleep(e.retry_after)
                raise
            except (AuthenticationError, ValidationError, NotFoundError):
                # Don't retry these errors
                raise
            
            # Wait before retry (except on last attempt)
            if attempt < self.max_retries:
                wait_time = self.retry_delay * (2 ** attempt)  # Exponential backoff
                logger.warning(f"Request failed, retrying in {wait_time} seconds...")
                time.sleep(wait_time)
        
        # All retries exhausted
        raise last_exception
    
    def health_check(self) -> HarmoniaResponse:
        """
        Perform health check.
        
        Returns:
            HarmoniaResponse: Health status
        """
        return self._make_request('GET', '/api/v1/health')
    
    def store_memory(
        self,
        user_id: str,
        message: str,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        resolution_strategy: str = "auto"
    ) -> HarmoniaResponse:
        """
        Store a new memory from a message.
        
        Args:
            user_id: User identifier
            message: Message to extract memory from
            session_id: Optional session identifier
            metadata: Additional metadata
            resolution_strategy: Conflict resolution strategy
            
        Returns:
            HarmoniaResponse: Storage result
        """
        data = {
            'user_id': user_id,
            'message': message,
            'resolution_strategy': resolution_strategy
        }
        
        if session_id:
            data['session_id'] = session_id
        if metadata:
            data['metadata'] = metadata
        
        return self._make_request('POST', '/api/v1/memory/store', data=data)
    
    def search_memories(
        self,
        user_id: str,
        query: str,
        limit: int = 10,
        offset: int = 0,
        category: Optional[str] = None,
        from_date: Optional[Union[datetime, str]] = None,
        to_date: Optional[Union[datetime, str]] = None,
        min_confidence: Optional[float] = None,
        max_confidence: Optional[float] = None,
        sort_by: str = "relevance",
        sort_order: str = "desc",
        include_metadata: bool = False
    ) -> HarmoniaResponse:
        """
        Search memories.
        
        Args:
            user_id: User identifier
            query: Search query
            limit: Maximum results to return
            offset: Number of results to skip
            category: Optional category filter
            from_date: Optional start date filter
            to_date: Optional end date filter
            min_confidence: Optional minimum confidence filter
            max_confidence: Optional maximum confidence filter
            sort_by: Sort field
            sort_order: Sort order (asc/desc)
            include_metadata: Whether to include metadata
            
        Returns:
            HarmoniaResponse: Search results
        """
        params = {
            'user_id': user_id,
            'query': query,
            'limit': limit,
            'offset': offset,
            'sort_by': sort_by,
            'sort_order': sort_order,
            'include_metadata': include_metadata
        }
        
        # Add optional filters
        if category:
            params['category'] = category
        if from_date:
            params['from_date'] = from_date.isoformat() if isinstance(from_date, datetime) else from_date
        if to_date:
            params['to_date'] = to_date.isoformat() if isinstance(to_date, datetime) else to_date
        if min_confidence is not None:
            params['min_confidence'] = min_confidence
        if max_confidence is not None:
            params['max_confidence'] = max_confidence
        
        return self._make_request('GET', '/api/v1/memory/search', params=params)
    
    def list_memories(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0,
        category: Optional[str] = None,
        from_date: Optional[Union[datetime, str]] = None,
        to_date: Optional[Union[datetime, str]] = None,
        min_confidence: Optional[float] = None,
        max_confidence: Optional[float] = None,
        sort_by: str = "updated_at",
        sort_order: str = "desc",
        include_inactive: bool = False
    ) -> HarmoniaResponse:
        """
        List memories for a user.
        
        Args:
            user_id: User identifier
            limit: Maximum results to return
            offset: Number of results to skip
            category: Optional category filter
            from_date: Optional start date filter
            to_date: Optional end date filter
            min_confidence: Optional minimum confidence filter
            max_confidence: Optional maximum confidence filter
            sort_by: Sort field
            sort_order: Sort order (asc/desc)
            include_inactive: Whether to include inactive memories
            
        Returns:
            HarmoniaResponse: Memory list
        """
        params = {
            'user_id': user_id,
            'limit': limit,
            'offset': offset,
            'sort_by': sort_by,
            'sort_order': sort_order,
            'include_inactive': include_inactive
        }
        
        # Add optional filters
        if category:
            params['category'] = category
        if from_date:
            params['from_date'] = from_date.isoformat() if isinstance(from_date, datetime) else from_date
        if to_date:
            params['to_date'] = to_date.isoformat() if isinstance(to_date, datetime) else to_date
        if min_confidence is not None:
            params['min_confidence'] = min_confidence
        if max_confidence is not None:
            params['max_confidence'] = max_confidence
        
        return self._make_request('GET', '/api/v1/memory/list', params=params)
    
    def get_memory(self, memory_id: str, user_id: str) -> HarmoniaResponse:
        """
        Get a specific memory by ID.
        
        Args:
            memory_id: Memory identifier
            user_id: User identifier
            
        Returns:
            HarmoniaResponse: Memory details
        """
        params = {'user_id': user_id}
        return self._make_request('GET', f'/api/v1/memory/{memory_id}', params=params)
    
    def delete_memory(self, memory_id: str, user_id: str) -> HarmoniaResponse:
        """
        Delete a specific memory by ID.
        
        Args:
            memory_id: Memory identifier
            user_id: User identifier
            
        Returns:
            HarmoniaResponse: Deletion confirmation
        """
        params = {'user_id': user_id}
        return self._make_request('DELETE', f'/api/v1/memory/{memory_id}', params=params)
    
    def export_memories(
        self,
        user_id: str,
        format: str = "json",
        include_metadata: bool = False,
        category: Optional[str] = None,
        from_date: Optional[Union[datetime, str]] = None,
        to_date: Optional[Union[datetime, str]] = None,
        min_confidence: Optional[float] = None,
        max_confidence: Optional[float] = None
    ) -> HarmoniaResponse:
        """
        Export memories in various formats.
        
        Args:
            user_id: User identifier
            format: Export format (json, csv, markdown, text)
            include_metadata: Whether to include metadata
            category: Optional category filter
            from_date: Optional start date filter
            to_date: Optional end date filter
            min_confidence: Optional minimum confidence filter
            max_confidence: Optional maximum confidence filter
            
        Returns:
            HarmoniaResponse: Exported data
        """
        params = {
            'user_id': user_id,
            'format': format,
            'include_metadata': include_metadata
        }
        
        # Add optional filters
        if category:
            params['category'] = category
        if from_date:
            params['from_date'] = from_date.isoformat() if isinstance(from_date, datetime) else from_date
        if to_date:
            params['to_date'] = to_date.isoformat() if isinstance(to_date, datetime) else to_date
        if min_confidence is not None:
            params['min_confidence'] = min_confidence
        if max_confidence is not None:
            params['max_confidence'] = max_confidence
        
        return self._make_request('GET', '/api/v1/memory/export', params=params)
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.session.close()