"""
Memory management router for Harmonia Memory Storage API.

This module provides all memory-related endpoints including storage,
search, retrieval, and export functionality.
"""
import time
import uuid
import logging
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query, Path
from fastapi.responses import PlainTextResponse

from api.dependencies import get_memory_manager, get_search_engine
from api.models.requests import (
    MemoryStoreRequest, SearchRequest, MemoryListRequest, 
    MemoryExportRequest, SortBy, SortOrder, ExportFormat
)
from api.models.responses import (
    MemoryStoreResponse, SearchResponse, MemoryListResponse,
    MemoryDetailResponse, MemoryDeleteResponse, MemoryExportResponse,
    MemoryResponse, SearchResult, PaginationInfo, FiltersApplied,
    ConflictResolution, ErrorResponse
)
from search.search_engine import SearchFilter, SearchOptions
from processing.exceptions import (
    MemoryProcessingError, ConflictResolutionError, 
    MemoryNotFoundError, ValidationError
)


logger = logging.getLogger(__name__)
router = APIRouter()


def _convert_search_filter(
    category: Optional[str] = None,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    min_confidence: Optional[float] = None,
    max_confidence: Optional[float] = None,
    is_active: bool = True
) -> SearchFilter:
    """
    Convert API parameters to SearchFilter object.
    
    Args:
        category: Memory category filter
        from_date: Start date filter
        to_date: End date filter
        min_confidence: Minimum confidence filter
        max_confidence: Maximum confidence filter
        is_active: Whether to include only active memories
        
    Returns:
        SearchFilter: Configured search filter
    """
    return SearchFilter(
        category=category,
        from_date=from_date,
        to_date=to_date,
        min_confidence=min_confidence,
        max_confidence=max_confidence,
        is_active=is_active
    )


def _convert_search_options(
    limit: int = 10,
    offset: int = 0,
    sort_by: SortBy = SortBy.RELEVANCE,
    sort_order: SortOrder = SortOrder.DESC,
    boost_categories: Optional[List[str]] = None
) -> SearchOptions:
    """
    Convert API parameters to SearchOptions object.
    
    Args:
        limit: Maximum results to return
        offset: Number of results to skip
        sort_by: Field to sort by
        sort_order: Sort order (asc/desc)
        boost_categories: Categories to boost in ranking
        
    Returns:
        SearchOptions: Configured search options
    """
    from search.search_engine import SortOption, SortOrder as SearchSortOrder
    
    # Convert API enums to search engine enums
    sort_option_map = {
        SortBy.RELEVANCE: SortOption.RELEVANCE,
        SortBy.CREATED_AT: SortOption.CREATED_AT,
        SortBy.UPDATED_AT: SortOption.UPDATED_AT,
        SortBy.CONFIDENCE: SortOption.CONFIDENCE,
        SortBy.TIMESTAMP: SortOption.TIMESTAMP
    }
    
    sort_order_map = {
        SortOrder.ASC: SearchSortOrder.ASC,
        SortOrder.DESC: SearchSortOrder.DESC
    }
    
    return SearchOptions(
        limit=limit,
        offset=offset,
        sort_by=sort_option_map[sort_by],
        sort_order=sort_order_map[sort_order],
        boost_categories=boost_categories or []
    )


def _memory_to_response(memory) -> MemoryResponse:
    """
    Convert Memory object to MemoryResponse.
    
    Args:
        memory: Memory object from database
        
    Returns:
        MemoryResponse: API response model
    """
    return MemoryResponse(
        memory_id=memory.memory_id,
        user_id=memory.user_id,
        content=memory.content,
        original_message=memory.original_message,
        category=memory.category,
        confidence_score=memory.confidence_score,
        timestamp=memory.timestamp,
        created_at=memory.created_at,
        updated_at=memory.updated_at,
        is_active=memory.is_active,
        metadata=memory.metadata
    )


def _search_result_to_response(result) -> SearchResult:
    """
    Convert SearchResult object to API response.
    
    Args:
        result: SearchResult object from search engine
        
    Returns:
        SearchResult: API response model
    """
    return SearchResult(
        memory_id=result.memory.memory_id,
        content=result.memory.content,
        category=result.memory.category,
        confidence_score=result.memory.confidence_score,
        timestamp=result.memory.timestamp,
        created_at=result.memory.created_at,
        updated_at=result.memory.updated_at,
        relevance_score=result.relevance_score,
        rank=result.rank,
        snippet=result.snippet,
        highlights=result.highlights,
        metadata=result.memory.metadata
    )


@router.post("/memory/store", response_model=MemoryStoreResponse)
async def store_memory(
    request: MemoryStoreRequest,
    memory_manager=Depends(get_memory_manager)
):
    """
    Store a new memory from a user message.
    
    Processes the message through the LLM to extract structured memories,
    handles conflict resolution, and stores the result in the database.
    
    Args:
        request: Memory storage request
        memory_manager: Memory manager dependency
        
    Returns:
        MemoryStoreResponse: Storage result with memory details
    """
    start_time = time.time()
    
    try:
        logger.info(f"Processing and storing memory for user {request.user_id}")
        
        # Process message using LLM and store resulting memories
        result = memory_manager.process_and_store_memory(
            user_id=request.user_id,
            message=request.message,
            session_id=getattr(request, 'session_id', 'default'),
            detect_conflicts=True
        )
        
        processing_time = int((time.time() - start_time) * 1000)
        
        # Convert conflicts to API format
        conflicts_resolved = []
        if result.conflicts_resolved:
            for conflict in result.conflicts_resolved:
                conflicts_resolved.append(ConflictResolution(
                    action=conflict.action.value if hasattr(conflict.action, 'value') else str(conflict.action),
                    original_memory_id=getattr(conflict, 'original_memory_id', None),
                    conflict_type=getattr(conflict, 'conflict_type', 'unknown'),
                    resolution_strategy=getattr(conflict, 'resolution_strategy', 'auto')
                ))
        
        # Handle case where no memories were extracted
        if result.result.value == "no_change" or not result.memory:
            logger.info("No memories were extracted from the message")
            return MemoryStoreResponse(
                success=True,
                memory_id=None,
                extracted_memory="No extractable memories found in message",
                action="no_change",
                confidence=0.0,
                conflicts_resolved=None,
                processing_time_ms=processing_time,
                metadata=result.metadata or {}
            )
        
        logger.info(f"Memory stored successfully: {result.memory.memory_id}")
        
        return MemoryStoreResponse(
            success=True,
            memory_id=result.memory.memory_id,
            extracted_memory=result.memory.content,
            action=result.result.value if hasattr(result.result, 'value') else str(result.result),
            confidence=result.memory.confidence_score,
            conflicts_resolved=conflicts_resolved if conflicts_resolved else None,
            processing_time_ms=processing_time,
            metadata=result.metadata
        )
        
    except ValidationError as e:
        logger.warning(f"Validation error storing memory: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Validation error: {str(e)}"
        )
    
    except MemoryProcessingError as e:
        logger.error(f"Memory processing error: {e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Memory processing failed: {str(e)}"
        )
    
    except ConflictResolutionError as e:
        logger.error(f"Conflict resolution error: {e}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Conflict resolution failed: {str(e)}"
        )
    
    except Exception as e:
        logger.error(f"Unexpected error storing memory: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during memory storage"
        )


@router.get("/memory/search", response_model=SearchResponse)
async def search_memories(
    user_id: str = Query(..., description="User ID"),
    query: str = Query(..., description="Search query"),
    limit: int = Query(10, ge=1, le=100, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Results to skip"),
    category: Optional[str] = Query(None, description="Category filter"),
    from_date: Optional[datetime] = Query(None, description="Start date filter"),
    to_date: Optional[datetime] = Query(None, description="End date filter"),
    min_confidence: Optional[float] = Query(None, ge=0.0, le=1.0, description="Min confidence"),
    max_confidence: Optional[float] = Query(None, ge=0.0, le=1.0, description="Max confidence"),
    sort_by: SortBy = Query(SortBy.RELEVANCE, description="Sort field"),
    sort_order: SortOrder = Query(SortOrder.DESC, description="Sort order"),
    include_metadata: bool = Query(False, description="Include metadata"),
    search_engine=Depends(get_search_engine)
):
    """
    Search memories using full-text search.
    
    Performs intelligent search across user's memories with ranking,
    filtering, and pagination support.
    
    Args:
        user_id: User identifier
        query: Search query string
        limit: Maximum results to return
        offset: Number of results to skip
        category: Optional category filter
        from_date: Optional start date filter
        to_date: Optional end date filter
        min_confidence: Optional minimum confidence filter
        max_confidence: Optional maximum confidence filter
        sort_by: Field to sort by
        sort_order: Sort order
        include_metadata: Whether to include metadata
        search_engine: Search engine dependency
        
    Returns:
        SearchResponse: Search results with metadata
    """
    start_time = time.time()
    
    try:
        logger.info(f"Searching memories for user {user_id}: '{query}'")
        
        # Convert API parameters to search engine objects
        filters = _convert_search_filter(
            category=category,
            from_date=from_date,
            to_date=to_date,
            min_confidence=min_confidence,
            max_confidence=max_confidence
        )
        
        options = _convert_search_options(
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            sort_order=sort_order
        )
        
        # Perform search
        results = search_engine.search(user_id, query, filters=filters, options=options)
        
        search_time = int((time.time() - start_time) * 1000)
        
        # Convert results to API format
        api_results = [_search_result_to_response(result) for result in results.results]
        
        # Remove metadata if not requested
        if not include_metadata:
            for result in api_results:
                result.metadata = None
        
        logger.info(f"Search completed: {len(api_results)} results in {search_time}ms")
        
        return SearchResponse(
            success=True,
            results=api_results,
            total_count=results.total_count,
            query=query,
            pagination=PaginationInfo(
                limit=limit,
                offset=offset,
                total_count=results.total_count,
                has_more=results.has_more
            ),
            filters_applied=FiltersApplied(
                category=category,
                from_date=from_date,
                to_date=to_date,
                min_confidence=min_confidence,
                max_confidence=max_confidence
            ),
            search_time_ms=search_time,
            metadata={
                "execution_time": results.execution_time,
                "total_results": results.total_count
            }
        )
        
    except Exception as e:
        logger.error(f"Search error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}"
        )


@router.get("/memory/list", response_model=MemoryListResponse)
async def list_memories(
    user_id: str = Query(..., description="User ID"),
    limit: int = Query(50, ge=1, le=1000, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Results to skip"),
    category: Optional[str] = Query(None, description="Category filter"),
    from_date: Optional[datetime] = Query(None, description="Start date filter"),
    to_date: Optional[datetime] = Query(None, description="End date filter"),
    min_confidence: Optional[float] = Query(None, ge=0.0, le=1.0, description="Min confidence"),
    max_confidence: Optional[float] = Query(None, ge=0.0, le=1.0, description="Max confidence"),
    sort_by: SortBy = Query(SortBy.UPDATED_AT, description="Sort field"),
    sort_order: SortOrder = Query(SortOrder.DESC, description="Sort order"),
    include_inactive: bool = Query(False, description="Include inactive memories"),
    search_engine=Depends(get_search_engine)
):
    """
    List memories for a user with filtering and pagination.
    
    Args:
        user_id: User identifier
        limit: Maximum results to return
        offset: Number of results to skip
        category: Optional category filter
        from_date: Optional start date filter
        to_date: Optional end date filter
        min_confidence: Optional minimum confidence filter
        max_confidence: Optional maximum confidence filter
        sort_by: Field to sort by
        sort_order: Sort order
        include_inactive: Whether to include inactive memories
        search_engine: Search engine dependency
        
    Returns:
        MemoryListResponse: List of memories with metadata
    """
    start_time = time.time()
    
    try:
        logger.info(f"Listing memories for user {user_id}")
        
        # Convert API parameters to search engine objects
        filters = _convert_search_filter(
            category=category,
            from_date=from_date,
            to_date=to_date,
            min_confidence=min_confidence,
            max_confidence=max_confidence,
            is_active=not include_inactive
        )
        
        options = _convert_search_options(
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            sort_order=sort_order
        )
        
        # List memories
        results = search_engine.list_memories(user_id, filters=filters, options=options)
        
        execution_time = int((time.time() - start_time) * 1000)
        
        # Convert results to API format
        api_memories = [_memory_to_response(result.memory) for result in results.results]
        
        logger.info(f"Listed {len(api_memories)} memories in {execution_time}ms")
        
        return MemoryListResponse(
            success=True,
            memories=api_memories,
            total_count=results.total_count,
            has_more=results.has_more,
            pagination=PaginationInfo(
                limit=limit,
                offset=offset,
                total_count=results.total_count,
                has_more=results.has_more
            ),
            filters_applied=FiltersApplied(
                category=category,
                from_date=from_date,
                to_date=to_date,
                min_confidence=min_confidence,
                max_confidence=max_confidence
            ),
            execution_time_ms=execution_time,
            metadata={
                "execution_time": results.execution_time,
                "total_results": results.total_count
            }
        )
        
    except Exception as e:
        logger.error(f"List memories error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list memories: {str(e)}"
        )


@router.get("/memory/export", response_model=MemoryExportResponse)
async def export_memories(
    user_id: str = Query(..., description="User ID"),
    format: ExportFormat = Query(ExportFormat.JSON, description="Export format"),
    include_metadata: bool = Query(False, description="Include metadata"),
    category: Optional[str] = Query(None, description="Category filter"),
    from_date: Optional[datetime] = Query(None, description="Start date filter"),
    to_date: Optional[datetime] = Query(None, description="End date filter"),
    min_confidence: Optional[float] = Query(None, ge=0.0, le=1.0, description="Min confidence"),
    max_confidence: Optional[float] = Query(None, ge=0.0, le=1.0, description="Max confidence"),
    search_engine=Depends(get_search_engine)
):
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
        search_engine: Search engine dependency
        
    Returns:
        MemoryExportResponse: Exported data in specified format
    """
    start_time = time.time()
    
    try:
        logger.info(f"Exporting memories for user {user_id} in {format} format")
        
        # Convert API parameters to search engine objects
        filters = _convert_search_filter(
            category=category,
            from_date=from_date,
            to_date=to_date,
            min_confidence=min_confidence,
            max_confidence=max_confidence
        )
        
        # Map API format to search engine format
        from search.search_engine import ExportFormat as SearchExportFormat
        format_map = {
            ExportFormat.JSON: SearchExportFormat.JSON,
            ExportFormat.CSV: SearchExportFormat.CSV,
            ExportFormat.MARKDOWN: SearchExportFormat.MARKDOWN,
            ExportFormat.TEXT: SearchExportFormat.TEXT
        }
        
        # Export memories
        result = search_engine.export_memories(
            user_id=user_id,
            export_format=format_map[format],
            filters=filters,
            include_metadata=include_metadata
        )
        
        execution_time = int((time.time() - start_time) * 1000)
        
        logger.info(f"Exported {result['memory_count']} memories in {execution_time}ms")
        
        return MemoryExportResponse(
            success=result['success'],
            data=result['data'],
            format=format,
            include_metadata=include_metadata,
            export_date=datetime.now(),
            memory_count=result['memory_count'],
            filters_applied=FiltersApplied(
                category=category,
                from_date=from_date,
                to_date=to_date,
                min_confidence=min_confidence,
                max_confidence=max_confidence
            ),
            execution_time_ms=execution_time,
            metadata={
                "export_timestamp": datetime.now().isoformat(),
                "original_execution_time": result['execution_time']
            }
        )
        
    except Exception as e:
        logger.error(f"Export memories error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export memories: {str(e)}"
        )


@router.get("/memory/{memory_id}", response_model=MemoryDetailResponse)
async def get_memory(
    memory_id: str = Path(..., description="Memory ID"),
    user_id: str = Query(..., description="User ID"),
    memory_manager=Depends(get_memory_manager)
):
    """
    Retrieve a specific memory by ID.
    
    Args:
        memory_id: Unique memory identifier
        memory_manager: Memory manager dependency
        
    Returns:
        MemoryDetailResponse: Memory details with update history
    """
    try:
        logger.info(f"Retrieving memory {memory_id}")
        
        # Get memory from database
        memory = memory_manager.get_memory(memory_id)
        
        if not memory:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Memory {memory_id} not found"
            )
        
        # Get update history (TODO: implement if needed)
        update_history = []  # Placeholder since get_memory_history doesn't exist yet
        
        logger.info(f"Retrieved memory {memory_id}")
        
        return MemoryDetailResponse(
            success=True,
            memory=_memory_to_response(memory),
            update_history=update_history,
            metadata={
                "memory_id": memory_id,
                "has_history": len(update_history) > 0 if update_history else False
            }
        )
        
    except MemoryNotFoundError as e:
        logger.warning(f"Memory not found: {memory_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Memory {memory_id} not found"
        )
    
    except Exception as e:
        logger.error(f"Get memory error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve memory: {str(e)}"
        )


@router.delete("/memory/{memory_id}", response_model=MemoryDeleteResponse)
async def delete_memory(
    memory_id: str = Path(..., description="Memory ID"),
    user_id: str = Query(..., description="User ID"),
    memory_manager=Depends(get_memory_manager)
):
    """
    Delete a specific memory by ID.
    
    Args:
        memory_id: Unique memory identifier
        memory_manager: Memory manager dependency
        
    Returns:
        MemoryDeleteResponse: Deletion confirmation
    """
    try:
        logger.info(f"Deleting memory {memory_id}")
        
        # Delete memory
        success = memory_manager.delete_memory(memory_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Memory {memory_id} not found"
            )
        
        logger.info(f"Deleted memory {memory_id}")
        
        return MemoryDeleteResponse(
            success=True,
            message=f"Memory {memory_id} deleted successfully",
            memory_id=memory_id,
            metadata={
                "deleted_at": datetime.now().isoformat()
            }
        )
        
    except MemoryNotFoundError as e:
        logger.warning(f"Memory not found for deletion: {memory_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Memory {memory_id} not found"
        )
    
    except Exception as e:
        logger.error(f"Delete memory error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete memory: {str(e)}"
        )

