"""
Main FastAPI application for Harmonia Memory Storage System.

This module creates and configures the FastAPI application with all necessary
middleware, routes, and error handlers.
"""
import logging
import os
import sys
import time
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

from core.config import get_config
from core.logging import configure_logging
from api.routers import health, memory
from api.middleware.logging import LoggingMiddleware
from api.middleware.auth import AuthMiddleware
from api.middleware.rate_limit import RateLimitMiddleware
from api.dependencies import get_database_manager, get_memory_manager, get_search_engine
from api.globals import get_app_state


# No need for global app_state - now managed in api.globals


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan context manager.
    Handles startup and shutdown events.
    """
    # Startup
    try:
        # Load configuration
        config = get_config()
        
        # Setup logging
        configure_logging(config)
        logger = logging.getLogger(__name__)
        logger.info("Starting Harmonia Memory Storage API...")
        
        # Initialize multi-database manager
        from db.multi_db_manager import MultiDatabaseManager
        multi_db_manager = MultiDatabaseManager(
            base_path=config.database.path,
            pool_size_per_db=max(5, config.database.pool_size // 4)
        )
        
        # Keep the old single-database system for backward compatibility and health checks
        from db.manager import DatabaseManager
        db_manager = DatabaseManager(
            db_path=config.database.path,
            pool_size=config.database.pool_size
        )
        
        # Initialize search engine with the original database manager for now
        from search.search_engine import SearchEngine
        search_engine = SearchEngine(db_manager=db_manager)
        
        # Initialize processing components (shared across users)
        from processing.memory_processor import MemoryProcessor
        from processing.conflict_detector import ConflictDetector
        from processing.conflict_resolver import ConflictResolver
        from processing.temporal_resolver import TemporalResolver
        from llm.ollama_client import OllamaClient
        
        ollama_client = OllamaClient(
            host=config.ollama.host,
            default_model=config.ollama.model
        )
        
        memory_processor = MemoryProcessor(ollama_client=ollama_client)
        conflict_detector = ConflictDetector()
        conflict_resolver = ConflictResolver()
        temporal_resolver = TemporalResolver()
        
        # Initialize legacy memory manager for compatibility
        from processing.memory_manager import MemoryManager
        memory_manager = MemoryManager(
            db_manager=db_manager
        )
        
        # Store in app state for dependency injection
        app_state = get_app_state()
        app_state['config'] = config
        app_state['db_manager'] = db_manager  # Legacy single DB
        app_state['multi_db_manager'] = multi_db_manager  # New multi-user DB system
        app_state['memory_manager'] = memory_manager  # Legacy memory manager
        app_state['search_engine'] = search_engine
        app_state['ollama_client'] = ollama_client
        app_state['memory_processor'] = memory_processor
        app_state['conflict_detector'] = conflict_detector
        app_state['conflict_resolver'] = conflict_resolver
        app_state['temporal_resolver'] = temporal_resolver
        
        logger.info("Application startup complete")
        
        yield
        
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to start application: {e}")
        raise
    
    # Shutdown
    try:
        logger = logging.getLogger(__name__)
        logger.info("Shutting down Harmonia Memory Storage API...")
        
        # Cleanup resources
        app_state = get_app_state()
        if 'multi_db_manager' in app_state:
            app_state['multi_db_manager'].close_all()
        if 'db_manager' in app_state:
            app_state['db_manager'].close()
        if 'search_engine' in app_state:
            app_state['search_engine'].close()
        if 'ollama_client' in app_state:
            app_state['ollama_client'].close()
        
        logger.info("Application shutdown complete")
        
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Error during shutdown: {e}")


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.
    
    Returns:
        FastAPI: Configured application instance
    """
    app = FastAPI(
        title="Harmonia Memory Storage API",
        description="Local-first memory storage system for chat LLMs",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan
    )
    
    # Load configuration for middleware setup
    try:
        config = get_config()
    except Exception:
        # Use default config if loading fails
        from core.config import Config
        config = Config()
    
    # Add security middleware
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.server.cors_origins,
        allow_credentials=config.security.cors.allow_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Add custom middleware
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(RateLimitMiddleware, rate_limit=config.security.rate_limit.requests_per_minute)
    
    # Add authentication middleware if required
    if config.security.api_key_required:
        app.add_middleware(AuthMiddleware)
    
    # Include routers
    app.include_router(health.router, prefix="/api/v1", tags=["health"])
    app.include_router(memory.router, prefix="/api/v1", tags=["memory"])
    
    # Global exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger = logging.getLogger(__name__)
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "error_code": "SYS001",
                "message": "An unexpected error occurred",
                "timestamp": time.time()
            }
        )
    
    # HTTP exception handler
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.detail,
                "error_code": f"HTTP{exc.status_code}",
                "message": exc.detail,
                "timestamp": time.time()
            }
        )
    
    return app


# Create the application instance
app = create_app()


if __name__ == "__main__":
    import uvicorn
    
    # Load configuration
    try:
        config = get_config()
        host = config.server.host
        port = config.server.port
    except Exception:
        host = '0.0.0.0'
        port = 8000
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=True,
        log_level="info"
    )