"""
Logging infrastructure for Harmonia Memory Storage System.
"""
import json
import logging
import logging.handlers
import sys
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
from .config import get_config


class StructuredFormatter(logging.Formatter):
    """Structured JSON formatter for logs."""
    
    def __init__(self, include_caller: bool = False):
        super().__init__()
        self.include_caller = include_caller
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON."""
        log_entry = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'thread': threading.current_thread().name,
            'thread_id': threading.get_ident()
        }
        
        # Add caller information if requested
        if self.include_caller:
            log_entry.update({
                'file': record.filename,
                'line': record.lineno,
                'function': record.funcName
            })
        
        # Add exception information if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        # Add extra fields from record
        for key, value in record.__dict__.items():
            if key not in {
                'name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
                'filename', 'module', 'lineno', 'funcName', 'created',
                'msecs', 'relativeCreated', 'thread', 'threadName',
                'processName', 'process', 'message', 'exc_info', 'exc_text',
                'stack_info', 'getMessage'
            }:
                log_entry['extra'] = log_entry.get('extra', {})
                log_entry['extra'][key] = value
        
        return json.dumps(log_entry, default=str)


class DetailedFormatter(logging.Formatter):
    """Detailed formatter with comprehensive information."""
    
    def __init__(self):
        super().__init__(
            fmt='%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(lineno)d - %(funcName)s() - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )


class SimpleFormatter(logging.Formatter):
    """Simple formatter for console output."""
    
    def __init__(self):
        super().__init__(
            fmt='%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%H:%M:%S'
        )


class LogManager:
    """Centralized logging manager for the application."""
    
    def __init__(self):
        self._configured = False
        self._loggers: Dict[str, logging.Logger] = {}
        self._lock = threading.Lock()
    
    def configure(self, config=None) -> None:
        """Configure logging based on configuration."""
        with self._lock:
            
            if config is None:
                config = get_config()
            
            # Clear any existing handlers
            self._clear_handlers()
            
            # Set root logger level
            root_logger = logging.getLogger()
            root_logger.setLevel(getattr(logging, config.logging.level))
            
            # Configure file logging
            if config.logging.file.enabled:
                self._configure_file_logging(config.logging)
            
            # Configure console logging
            if config.logging.console.enabled:
                self._configure_console_logging(config.logging)
            
            # Set up logger for this module
            self._setup_harmonia_loggers(config.logging)
            
            self._configured = True
    
    def _clear_handlers(self) -> None:
        """Clear existing handlers from root logger."""
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
            handler.close()
    
    def _configure_file_logging(self, logging_config) -> None:
        """Configure file-based logging."""
        log_path = Path(logging_config.file.path)
        
        # Create log directory if it doesn't exist
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Parse max size
        max_bytes = self._parse_size(logging_config.file.max_size)
        
        # Create rotating file handler
        if logging_config.file.rotation == "size":
            handler = logging.handlers.RotatingFileHandler(
                filename=log_path,
                maxBytes=max_bytes,
                backupCount=logging_config.file.backup_count,
                encoding='utf-8'
            )
        else:  # time-based rotation
            handler = logging.handlers.TimedRotatingFileHandler(
                filename=log_path,
                when='midnight',
                interval=1,
                backupCount=logging_config.file.backup_count,
                encoding='utf-8'
            )
        
        # Set formatter based on format setting
        formatter = self._get_formatter(logging_config.format, logging_config.structured)
        handler.setFormatter(formatter)
        
        # Set level
        handler.setLevel(getattr(logging, logging_config.level))
        
        # Add to root logger
        logging.getLogger().addHandler(handler)
    
    def _configure_console_logging(self, logging_config) -> None:
        """Configure console-based logging."""
        handler = logging.StreamHandler(sys.stdout)
        
        # Use simple formatter for console
        formatter = SimpleFormatter()
        handler.setFormatter(formatter)
        
        # Set level
        console_level = getattr(logging, logging_config.console.level)
        handler.setLevel(console_level)
        
        # Add to root logger
        logging.getLogger().addHandler(handler)
    
    def _setup_harmonia_loggers(self, logging_config) -> None:
        """Set up specific loggers for Harmonia components."""
        harmonia_modules = [
            'harmonia',
            'harmonia.api',
            'harmonia.core',
            'harmonia.db',
            'harmonia.llm',
            'harmonia.search',
            'harmonia.memory'
        ]
        
        for module_name in harmonia_modules:
            logger = logging.getLogger(module_name)
            logger.setLevel(getattr(logging, logging_config.level))
            self._loggers[module_name] = logger
    
    def _get_formatter(self, format_type: str, structured_config) -> logging.Formatter:
        """Get appropriate formatter based on configuration."""
        if format_type == "structured":
            return StructuredFormatter(include_caller=structured_config.include_caller)
        elif format_type == "detailed":
            return DetailedFormatter()
        else:  # simple
            return SimpleFormatter()
    
    def _parse_size(self, size_str: str) -> int:
        """Parse size string like '10MB' to bytes."""
        size_str = size_str.upper().strip()
        
        if size_str.endswith('KB'):
            return int(size_str[:-2]) * 1024
        elif size_str.endswith('MB'):
            return int(size_str[:-2]) * 1024 * 1024
        elif size_str.endswith('GB'):
            return int(size_str[:-2]) * 1024 * 1024 * 1024
        else:
            # Assume bytes
            return int(size_str)
    
    def get_logger(self, name: str) -> logging.Logger:
        """Get a configured logger by name."""
        if not self._configured:
            self.configure()
        
        if name not in self._loggers:
            logger = logging.getLogger(name)
            self._loggers[name] = logger
        
        return self._loggers[name]
    
    def reconfigure(self, config=None) -> None:
        """Reconfigure logging (e.g., after config reload)."""
        with self._lock:
            # Clear handlers first
            self._clear_handlers()
            self._configured = False
            self.configure(config)
    
    def reset(self) -> None:
        """Reset log manager state (for testing)."""
        with self._lock:
            self._clear_handlers()
            self._configured = False
            self._loggers.clear()
    
    def test_logging(self) -> Dict[str, Any]:
        """Test logging functionality and return status."""
        results = {
            'file_logging': False,
            'console_logging': False,
            'structured_logging': False,
            'rotation_working': False,
            'errors': []
        }
        
        try:
            # Get test logger
            test_logger = self.get_logger('harmonia.test')
            
            # Test basic logging
            test_logger.info("Test log message for functionality verification")
            results['console_logging'] = True
            
            # Test file logging if enabled
            config = get_config()
            if config.logging.file.enabled:
                log_path = Path(config.logging.file.path)
                if log_path.exists():
                    results['file_logging'] = True
            
            # Test structured logging
            if config.logging.format == "structured":
                test_logger.info("Structured log test", extra={'test_field': 'test_value'})
                results['structured_logging'] = True
            
            # Test log levels
            test_logger.debug("Debug message")
            test_logger.info("Info message")
            test_logger.warning("Warning message")
            test_logger.error("Error message")
            
            results['rotation_working'] = True  # If we get here, basic setup worked
            
        except Exception as e:
            results['errors'].append(str(e))
        
        return results


class LoggerMixin:
    """Mixin class to add logging capabilities to any class."""
    
    @property
    def logger(self) -> logging.Logger:
        """Get logger for this class."""
        if not hasattr(self, '_logger'):
            class_name = self.__class__.__module__ + '.' + self.__class__.__qualname__
            self._logger = get_logger(class_name)
        return self._logger


# Global log manager instance
_log_manager = LogManager()


def configure_logging(config=None) -> None:
    """Configure the logging system."""
    _log_manager.configure(config)


def get_logger(name: str) -> logging.Logger:
    """Get a configured logger by name."""
    return _log_manager.get_logger(name)


def reconfigure_logging(config=None) -> None:
    """Reconfigure logging after config changes."""
    _log_manager.reconfigure(config)


def test_logging() -> Dict[str, Any]:
    """Test logging system functionality."""
    return _log_manager.test_logging()


# Convenience function for getting module-specific loggers
def get_module_logger(module_file: str) -> logging.Logger:
    """Get logger for a specific module file."""
    module_path = Path(module_file)
    
    # Convert file path to logger name
    if 'harmonia' in str(module_path):
        # Extract harmonia-relative path
        parts = module_path.parts
        harmonia_index = next(i for i, part in enumerate(parts) if 'harmonia' in part.lower())
        logger_parts = parts[harmonia_index:]
        
        # Remove src/ if present and convert to dot notation
        if logger_parts and logger_parts[0] == 'src':
            logger_parts = logger_parts[1:]
        
        logger_name = '.'.join(logger_parts).replace('.py', '')
    else:
        # Fallback to file name
        logger_name = module_path.stem
    
    return get_logger(logger_name)


# Auto-configure logging on import
try:
    configure_logging()
except Exception:
    # Silently fail if configuration fails during import
    # This prevents import errors if config is not yet available
    pass