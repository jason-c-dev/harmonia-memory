"""
Dependency injection for FastAPI application.

This module provides dependency functions for accessing shared resources
like database managers, memory processors, and search engines.
"""
from typing import Generator
from fastapi import Depends, HTTPException, status
import logging

from .globals import get_app_state


logger = logging.getLogger(__name__)


def get_database_manager():
    """
    Get the database manager instance.
    
    Returns:
        DatabaseManager: The database manager instance
    """
    app_state = get_app_state()
    db_manager = app_state.get('db_manager')
    if not db_manager:
        logger.error("Database manager not initialized")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service unavailable"
        )
    return db_manager


def get_memory_manager():
    """
    Get the memory manager instance.
    
    Returns:
        MemoryManager: The memory manager instance
    """
    app_state = get_app_state()
    memory_manager = app_state.get('memory_manager')
    if not memory_manager:
        logger.error("Memory manager not initialized")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Memory service unavailable"
        )
    return memory_manager


def get_search_engine():
    """
    Get the search engine instance.
    
    Returns:
        SearchEngine: The search engine instance
    """
    app_state = get_app_state()
    search_engine = app_state.get('search_engine')
    if not search_engine:
        logger.error("Search engine not initialized")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Search service unavailable"
        )
    return search_engine


def get_multi_database_manager():
    """
    Get the multi-database manager instance.
    
    Returns:
        MultiDatabaseManager: The multi-database manager instance
    """
    app_state = get_app_state()
    multi_db_manager = app_state.get('multi_db_manager')
    if not multi_db_manager:
        logger.error("Multi-database manager not initialized")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service unavailable"
        )
    return multi_db_manager


def get_user_database_manager(user_id: str, multi_db_manager=Depends(get_multi_database_manager)):
    """
    Get a user-specific database manager.
    
    Args:
        user_id: User identifier
        multi_db_manager: Multi-database manager dependency
        
    Returns:
        UserDatabaseManager: Database manager for the specific user
    """
    try:
        db_manager = multi_db_manager.get_user_db_manager(user_id)
        from db.user_db_manager import UserDatabaseManager
        return UserDatabaseManager(db_manager)
    except Exception as e:
        logger.error(f"Failed to get user database manager for {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="User database service unavailable"
        )


def get_processing_components():
    """
    Get shared processing components.
    
    Returns:
        Dict containing processing components
    """
    app_state = get_app_state()
    
    components = {
        'memory_processor': app_state.get('memory_processor'),
        'conflict_detector': app_state.get('conflict_detector'),
        'conflict_resolver': app_state.get('conflict_resolver'),
        'temporal_resolver': app_state.get('temporal_resolver'),
        'ollama_client': app_state.get('ollama_client')
    }
    
    missing = [k for k, v in components.items() if v is None]
    if missing:
        logger.error(f"Processing components not initialized: {missing}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Processing service unavailable"
        )
    
    return components


def get_user_memory_manager(user_id: str, 
                           user_db_manager=Depends(get_user_database_manager),
                           processing_components=Depends(get_processing_components)):
    """
    Get a user-specific memory manager.
    
    Args:
        user_id: User identifier (passed through)
        user_db_manager: User database manager dependency
        processing_components: Processing components dependency
        
    Returns:
        UserMemoryManager: Memory manager for the specific user
    """
    try:
        from processing.user_memory_manager import UserMemoryManager
        
        return UserMemoryManager(
            user_db_manager=user_db_manager,
            memory_processor=processing_components['memory_processor'],
            conflict_detector=processing_components['conflict_detector'],
            conflict_resolver=processing_components['conflict_resolver'],
            temporal_resolver=processing_components['temporal_resolver']
        )
    except Exception as e:
        logger.error(f"Failed to create user memory manager for {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Memory service unavailable"
        )


def get_config():
    """
    Get the application configuration.
    
    Returns:
        Dict: The application configuration
    """
    app_state = get_app_state()
    config = app_state.get('config')
    if not config:
        logger.error("Configuration not loaded")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Configuration service unavailable"
        )
    return config