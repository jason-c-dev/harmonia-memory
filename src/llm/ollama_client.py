"""
Ollama client for LLM integration with connection management, retry logic, and health checks.
"""
import time
import json
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
import asyncio
import threading
from contextlib import contextmanager

import ollama
from ollama import Client as OllamaBaseClient

from core.config import get_config
from core.logging import get_logger

logger = get_logger(__name__)


class OllamaError(Exception):
    """Base exception for Ollama client errors."""
    pass


class ModelNotFoundError(OllamaError):
    """Exception raised when the specified model is not found."""
    pass


class ConnectionError(OllamaError):
    """Exception raised when connection to Ollama fails."""
    pass


class TimeoutError(OllamaError):
    """Exception raised when operations timeout."""
    pass


class OllamaClient:
    """
    Ollama client with connection management, retry logic, and health monitoring.
    """
    
    def __init__(self, host: Optional[str] = None, timeout: Optional[int] = None, 
                 default_model: Optional[str] = None, max_retries: int = 3):
        """
        Initialize Ollama client.
        
        Args:
            host: Ollama server host (defaults to config)
            timeout: Request timeout in seconds (defaults to config)
            default_model: Default model to use (defaults to config)
            max_retries: Maximum number of retries for failed requests
        """
        config = get_config()
        
        self.host = host or config.ollama.host
        self.timeout = timeout or config.ollama.timeout
        self.default_model = default_model or config.ollama.model
        self.max_retries = max_retries
        self.retry_delay = 1.0  # Base delay in seconds
        
        # Initialize Ollama client
        self._client = OllamaBaseClient(host=self.host, timeout=self.timeout)
        
        # Connection state
        self._connected = False
        self._last_health_check = None
        self._health_check_interval = timedelta(minutes=5)
        self._lock = threading.Lock()
        
        # Statistics
        self._stats = {
            'requests_made': 0,
            'requests_failed': 0,
            'total_response_time': 0.0,
            'avg_response_time': 0.0,
            'last_request_time': None,
            'models_used': set(),
            'errors': []
        }
        
        logger.info(f"OllamaClient initialized: host={self.host}, model={self.default_model}")
    
    def _update_stats(self, response_time: float, model: str, success: bool, error: Optional[str] = None):
        """Update client statistics."""
        with self._lock:
            self._stats['requests_made'] += 1
            if not success:
                self._stats['requests_failed'] += 1
                if error:
                    self._stats['errors'].append({
                        'error': error,
                        'timestamp': datetime.now().isoformat(),
                        'model': model
                    })
                    # Keep only last 10 errors
                    if len(self._stats['errors']) > 10:
                        self._stats['errors'] = self._stats['errors'][-10:]
            
            if success:
                self._stats['total_response_time'] += response_time
                successful_requests = self._stats['requests_made'] - self._stats['requests_failed']
                if successful_requests > 0:
                    self._stats['avg_response_time'] = self._stats['total_response_time'] / successful_requests
                self._stats['models_used'].add(model)
            
            self._stats['last_request_time'] = datetime.now().isoformat()
    
    def _retry_with_backoff(self, operation, *args, **kwargs):
        """
        Execute operation with exponential backoff retry logic.
        
        Args:
            operation: Function to execute
            *args: Arguments for operation
            **kwargs: Keyword arguments for operation
            
        Returns:
            Result of operation
            
        Raises:
            OllamaError: If operation fails after all retries
        """
        last_error = None
        
        for attempt in range(self.max_retries + 1):
            try:
                start_time = time.time()
                result = operation(*args, **kwargs)
                response_time = time.time() - start_time
                
                # Update stats on success
                model = kwargs.get('model', self.default_model)
                self._update_stats(response_time, model, True)
                
                return result
                
            except Exception as e:
                last_error = e
                model = kwargs.get('model', self.default_model)
                
                # Update stats on failure
                self._update_stats(0.0, model, False, str(e))
                
                if attempt < self.max_retries:
                    delay = self.retry_delay * (2 ** attempt)  # Exponential backoff
                    logger.warning(f"Ollama request failed, retrying in {delay:.1f}s (attempt {attempt + 1}/{self.max_retries + 1}): {e}")
                    time.sleep(delay)
                else:
                    logger.error(f"Ollama request failed after {self.max_retries + 1} attempts: {e}")
        
        # Convert specific errors
        if "model" in str(last_error).lower() and "not found" in str(last_error).lower():
            raise ModelNotFoundError(f"Model not found: {last_error}")
        elif "connection" in str(last_error).lower() or "timeout" in str(last_error).lower():
            raise ConnectionError(f"Connection failed: {last_error}")
        else:
            raise OllamaError(f"Request failed: {last_error}")
    
    def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on Ollama server.
        
        Returns:
            Health check results
        """
        start_time = time.time()
        health = {
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'host': self.host,
            'default_model': self.default_model,
            'response_time_ms': 0,
            'models_available': [],
            'errors': []
        }
        
        try:
            # Test basic connectivity by listing models
            models_response = self._client.list()
            # Handle both old dict format and new model object format
            if hasattr(models_response, 'models'):
                models = models_response.models
            else:
                models = models_response.get('models', [])
            
            health['models_available'] = []
            for model in models:
                if hasattr(model, 'model'):
                    health['models_available'].append(model.model)
                elif isinstance(model, dict) and 'name' in model:
                    health['models_available'].append(model['name'])
                elif hasattr(model, 'name'):
                    health['models_available'].append(model.name)
            
            # Check if default model is available
            if self.default_model not in health['models_available']:
                health['errors'].append(f"Default model '{self.default_model}' not available")
                health['status'] = 'degraded'
            
            # Test model response with simple prompt
            if self.default_model in health['models_available']:
                try:
                    response = self._client.generate(
                        model=self.default_model,
                        prompt="Hello",
                        options={'num_predict': 5}  # Short response
                    )
                    if not response.get('response'):
                        health['errors'].append("Model response test failed")
                        health['status'] = 'degraded'
                except Exception as e:
                    health['errors'].append(f"Model test failed: {str(e)}")
                    health['status'] = 'degraded'
            
        except Exception as e:
            health['status'] = 'unhealthy'
            health['errors'].append(f"Connection failed: {str(e)}")
        
        finally:
            health['response_time_ms'] = round((time.time() - start_time) * 1000, 1)
            
            # Update connection state
            with self._lock:
                self._connected = health['status'] != 'unhealthy'
                self._last_health_check = datetime.now()
        
        return health
    
    def _should_health_check(self) -> bool:
        """Check if health check is needed."""
        if self._last_health_check is None:
            return True
        
        # Handle case where _last_health_check might be set incorrectly as float
        if isinstance(self._last_health_check, (int, float)):
            # Convert timestamp to datetime
            last_check = datetime.fromtimestamp(self._last_health_check)
        else:
            last_check = self._last_health_check
            
        return datetime.now() - last_check > self._health_check_interval
    
    def ensure_connected(self) -> bool:
        """
        Ensure connection to Ollama is healthy.
        
        Returns:
            True if connected and healthy
        """
        if self._should_health_check():
            health = self.health_check()
            return health['status'] != 'unhealthy'
        return self._connected
    
    def list_models(self) -> List[Dict[str, Any]]:
        """
        List available models.
        
        Returns:
            List of available models
        """
        try:
            result = self._retry_with_backoff(self._client.list)
            
            # Handle both old dict format and new model object format
            if hasattr(result, 'models'):
                models = result.models
            else:
                models = result.get('models', [])
            
            # Convert model objects to dictionaries for consistency
            model_list = []
            for model in models:
                if hasattr(model, 'model'):
                    # New format with model objects
                    model_dict = {
                        'name': model.model,
                        'size': getattr(model, 'size', 0),
                        'digest': getattr(model, 'digest', ''),
                        'modified_at': getattr(model, 'modified_at', None)
                    }
                elif isinstance(model, dict):
                    # Old format with dictionaries
                    model_dict = model
                else:
                    # Fallback
                    model_dict = {'name': str(model), 'size': 0}
                
                model_list.append(model_dict)
            
            return model_list
        except Exception as e:
            logger.error(f"Failed to list models: {e}")
            raise
    
    def model_exists(self, model: str) -> bool:
        """
        Check if a model exists.
        
        Args:
            model: Model name to check
            
        Returns:
            True if model exists
        """
        try:
            models = self.list_models()
            return model in [m['name'] for m in models]
        except Exception:
            return False
    
    def generate(self, prompt: str, model: Optional[str] = None, 
                 system: Optional[str] = None, options: Optional[Dict[str, Any]] = None,
                 stream: bool = False) -> Dict[str, Any]:
        """
        Generate text response from model.
        
        Args:
            prompt: Input prompt
            model: Model to use (defaults to default_model)
            system: System prompt
            options: Generation options
            stream: Whether to stream response
            
        Returns:
            Generated response
        """
        if not self.ensure_connected():
            raise ConnectionError("Ollama server is not available")
        
        model = model or self.default_model
        
        # Check if model exists
        if not self.model_exists(model):
            available_models = [m['name'] for m in self.list_models()]
            raise ModelNotFoundError(f"Model '{model}' not found. Available models: {available_models}")
        
        request_params = {
            'model': model,
            'prompt': prompt,
            'stream': stream
        }
        
        if system:
            request_params['system'] = system
        if options:
            request_params['options'] = options
        
        try:
            result = self._retry_with_backoff(self._client.generate, **request_params)
            logger.debug(f"Generated response for model {model}: {len(prompt)} chars in -> {len(result.get('response', ''))} chars out")
            return result
        except Exception as e:
            logger.error(f"Generation failed for model {model}: {e}")
            raise
    
    def chat(self, messages: List[Dict[str, str]], model: Optional[str] = None,
             options: Optional[Dict[str, Any]] = None, stream: bool = False) -> Dict[str, Any]:
        """
        Chat with model using conversation format.
        
        Args:
            messages: List of chat messages (role, content)
            model: Model to use (defaults to default_model)
            options: Generation options
            stream: Whether to stream response
            
        Returns:
            Chat response
        """
        if not self.ensure_connected():
            raise ConnectionError("Ollama server is not available")
        
        model = model or self.default_model
        
        # Check if model exists
        if not self.model_exists(model):
            available_models = [m['name'] for m in self.list_models()]
            raise ModelNotFoundError(f"Model '{model}' not found. Available models: {available_models}")
        
        request_params = {
            'model': model,
            'messages': messages,
            'stream': stream
        }
        
        if options:
            request_params['options'] = options
        
        try:
            result = self._retry_with_backoff(self._client.chat, **request_params)
            logger.debug(f"Chat response for model {model}: {len(messages)} messages in")
            return result
        except Exception as e:
            logger.error(f"Chat failed for model {model}: {e}")
            raise
    
    def pull_model(self, model: str) -> bool:
        """
        Pull a model from Ollama repository.
        
        Args:
            model: Model name to pull
            
        Returns:
            True if successful
        """
        try:
            logger.info(f"Pulling model: {model}")
            self._client.pull(model)
            logger.info(f"Successfully pulled model: {model}")
            return True
        except Exception as e:
            logger.error(f"Failed to pull model {model}: {e}")
            return False
    
    def delete_model(self, model: str) -> bool:
        """
        Delete a model.
        
        Args:
            model: Model name to delete
            
        Returns:
            True if successful
        """
        try:
            logger.info(f"Deleting model: {model}")
            self._client.delete(model)
            logger.info(f"Successfully deleted model: {model}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete model {model}: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get client statistics.
        
        Returns:
            Statistics dictionary
        """
        with self._lock:
            stats = self._stats.copy()
            stats['models_used'] = list(stats['models_used'])  # Convert set to list for JSON serialization
            stats['connected'] = self._connected
            stats['last_health_check'] = self._last_health_check.isoformat() if self._last_health_check else None
            stats['success_rate'] = round(
                (stats['requests_made'] - stats['requests_failed']) / max(stats['requests_made'], 1) * 100, 1
            )
            return stats
    
    @contextmanager
    def model_context(self, model: str):
        """
        Context manager for temporarily using a different model.
        
        Args:
            model: Model to use in this context
        """
        original_model = self.default_model
        self.default_model = model
        try:
            yield self
        finally:
            self.default_model = original_model
    
    def close(self):
        """Close the client and cleanup resources."""
        logger.info("OllamaClient closed")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()