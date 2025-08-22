"""
Health check router for Harmonia Memory Storage API.

This module provides health check endpoints for monitoring system status.
"""
import time
import logging
from datetime import datetime
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status

from api.dependencies import get_database_manager, get_memory_manager, get_search_engine, get_config
from api.models.responses import HealthResponse


logger = logging.getLogger(__name__)
router = APIRouter()

# Track application start time for uptime calculation
app_start_time = time.time()


@router.get("/health", response_model=HealthResponse)
async def health_check(
    db_manager=Depends(get_database_manager),
    memory_manager=Depends(get_memory_manager),
    search_engine=Depends(get_search_engine),
    config=Depends(get_config)
):
    """
    Comprehensive health check endpoint.
    
    Checks the status of all system components including:
    - Database connectivity
    - LLM service availability
    - Search engine status
    - Memory manager status
    
    Returns:
        HealthResponse: System health status
    """
    logger.info("Performing health check")
    
    components = {}
    overall_status = "healthy"
    
    # Check database health
    try:
        db_health = db_manager.health_check()
        pool_stats = db_health.get("stats", {}).get("pool", {})
        components["database"] = {
            "status": db_health.get("status", "unknown"),
            "connection_pool_size": pool_stats.get("max_connections", 0),
            "active_connections": pool_stats.get("active_connections", 0),
            "last_check": datetime.now().isoformat()
        }
        
        if db_health.get("status") != "healthy":
            overall_status = "degraded"
            
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        components["database"] = {
            "status": "unhealthy",
            "error": str(e),
            "last_check": datetime.now().isoformat()
        }
        overall_status = "unhealthy"
    
    # Check search engine health
    try:
        search_health = search_engine.health_check()
        components["search_engine"] = {
            "status": search_health.get("status", "unknown"),
            "indexed_memories": search_health.get("components", {}).get("fts5", {}).get("indexed_memories", 0),
            "last_check": datetime.now().isoformat()
        }
        
        if search_health.get("status") != "healthy":
            overall_status = "degraded"
            
    except Exception as e:
        logger.error(f"Search engine health check failed: {e}")
        components["search_engine"] = {
            "status": "unhealthy",
            "error": str(e),
            "last_check": datetime.now().isoformat()
        }
        overall_status = "unhealthy"
    
    # Check memory manager health
    try:
        memory_health = memory_manager.get_statistics()
        manager_stats = memory_health.get("memory_manager", {})
        components["memory_manager"] = {
            "status": "healthy",
            "operations_count": manager_stats.get("operations_count", 0),
            "error_count": manager_stats.get("error_count", 0),
            "error_rate": manager_stats.get("error_rate", 0.0),
            "last_check": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Memory manager health check failed: {e}")
        components["memory_manager"] = {
            "status": "unhealthy",
            "error": str(e),
            "last_check": datetime.now().isoformat()
        }
        overall_status = "unhealthy"
    
    # Check LLM service health via memory manager
    try:
        # Get LLM health through memory processor
        processor_health = memory_manager.memory_processor.health_check()
        ollama_component = processor_health.get("components", {}).get("ollama", {})
        
        components["llm_service"] = {
            "status": ollama_component.get("status", "unknown"),
            "response_time_ms": ollama_component.get("response_time_ms", 0),
            "last_check": datetime.now().isoformat()
        }
        
        if ollama_component.get("status") != "healthy":
            overall_status = "degraded"
            
    except Exception as e:
        logger.error(f"LLM service health check failed: {e}")
        components["llm_service"] = {
            "status": "unknown", 
            "error": str(e),
            "last_check": datetime.now().isoformat()
        }
    
    # Calculate uptime
    uptime_seconds = time.time() - app_start_time
    
    logger.info(f"Health check completed: {overall_status}")
    
    return HealthResponse(
        status=overall_status,
        timestamp=datetime.now(),
        version="1.0.0",
        components=components,
        uptime_seconds=uptime_seconds,
        metadata={
            "environment": getattr(config, "environment", "production"),
            "api_version": "v1"
        }
    )


@router.get("/health/simple")
async def simple_health_check():
    """
    Simple health check endpoint for basic monitoring.
    
    Returns:
        dict: Basic health status
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "uptime_seconds": time.time() - app_start_time
    }