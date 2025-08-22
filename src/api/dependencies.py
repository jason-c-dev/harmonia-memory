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