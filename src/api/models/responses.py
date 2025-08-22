"""
Response models for the Harmonia Memory Storage API.

This module contains Pydantic models for API response formatting.
"""
from typing import Optional, Dict, Any, List, Union
from datetime import datetime
from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """Standard error response model."""
    
    error: str = Field(..., description="Error type")
    error_code: str = Field(..., description="Error code for programmatic handling")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    timestamp: float = Field(..., description="Error timestamp")


class ConflictResolution(BaseModel):
    """Model for conflict resolution details."""
    
    action: str = Field(..., description="Action taken (created, updated, merged)")
    original_memory_id: Optional[str] = Field(None, description="ID of original memory")
    conflict_type: str = Field(..., description="Type of conflict detected")
    resolution_strategy: str = Field(..., description="Strategy used for resolution")


class MemoryStoreResponse(BaseModel):
    """Response model for memory storage."""
    
    success: bool = Field(..., description="Whether the operation succeeded")
    memory_id: Optional[str] = Field(None, description="ID of the stored memory (None if no memory was extracted)")
    extracted_memory: str = Field(..., description="The extracted memory content")
    action: str = Field(..., description="Action taken (created, updated, merged)")
    confidence: float = Field(..., description="Confidence score of extraction")
    conflicts_resolved: Optional[List[ConflictResolution]] = Field(None, description="Details of conflicts resolved")
    processing_time_ms: int = Field(..., description="Processing time in milliseconds")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional response metadata")


class MemoryResponse(BaseModel):
    """Model for a single memory."""
    
    memory_id: str = Field(..., description="Unique memory identifier")
    user_id: str = Field(..., description="User who owns this memory")
    content: str = Field(..., description="Memory content")
    original_message: Optional[str] = Field(None, description="Original message that generated memory")
    category: Optional[str] = Field(None, description="Memory category")
    confidence_score: float = Field(..., description="Confidence score of extraction")
    timestamp: Optional[datetime] = Field(None, description="Event timestamp if applicable")
    created_at: datetime = Field(..., description="Memory creation timestamp")
    updated_at: datetime = Field(..., description="Memory last updated timestamp")
    is_active: bool = Field(..., description="Whether memory is active")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional memory metadata")


class SearchResult(BaseModel):
    """Model for a search result."""
    
    memory_id: str = Field(..., description="Memory identifier")
    content: str = Field(..., description="Memory content")
    category: Optional[str] = Field(None, description="Memory category")
    confidence_score: float = Field(..., description="Memory confidence score")
    timestamp: Optional[datetime] = Field(None, description="Event timestamp if applicable")
    created_at: datetime = Field(..., description="Memory creation timestamp")
    updated_at: datetime = Field(..., description="Memory last updated timestamp")
    relevance_score: float = Field(..., description="Search relevance score")
    rank: int = Field(..., description="Result rank in search")
    snippet: Optional[str] = Field(None, description="Highlighted search snippet")
    highlights: List[str] = Field(default_factory=list, description="Highlighted search terms")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class PaginationInfo(BaseModel):
    """Model for pagination information."""
    
    limit: int = Field(..., description="Results per page")
    offset: int = Field(..., description="Number of results skipped")
    total_count: int = Field(..., description="Total number of results")
    has_more: bool = Field(..., description="Whether more results are available")


class FiltersApplied(BaseModel):
    """Model for filters that were applied."""
    
    category: Optional[str] = Field(None, description="Category filter applied")
    from_date: Optional[datetime] = Field(None, description="Start date filter applied")
    to_date: Optional[datetime] = Field(None, description="End date filter applied")
    min_confidence: Optional[float] = Field(None, description="Minimum confidence filter applied")
    max_confidence: Optional[float] = Field(None, description="Maximum confidence filter applied")


class SearchResponse(BaseModel):
    """Response model for memory search."""
    
    success: bool = Field(..., description="Whether the operation succeeded")
    results: List[SearchResult] = Field(..., description="Search results")
    total_count: int = Field(..., description="Total number of results")
    # Extended fields for enhanced functionality
    query: str = Field(..., description="The search query that was executed")
    pagination: PaginationInfo = Field(..., description="Pagination information")
    filters_applied: FiltersApplied = Field(..., description="Filters that were applied")
    search_time_ms: int = Field(..., description="Search execution time in milliseconds")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional response metadata")


class MemoryListResponse(BaseModel):
    """Response model for memory listing."""
    
    success: bool = Field(..., description="Whether the operation succeeded")
    memories: List[MemoryResponse] = Field(..., description="List of memories")
    total_count: int = Field(..., description="Total number of memories")
    has_more: bool = Field(..., description="Whether more results are available")
    # Extended fields for enhanced functionality
    pagination: PaginationInfo = Field(..., description="Pagination information")
    filters_applied: FiltersApplied = Field(..., description="Filters that were applied")
    execution_time_ms: int = Field(..., description="Execution time in milliseconds")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional response metadata")


class MemoryDetailResponse(BaseModel):
    """Response model for single memory retrieval."""
    
    success: bool = Field(..., description="Whether the operation succeeded")
    memory: MemoryResponse = Field(..., description="Memory details")
    update_history: Optional[List[Dict[str, Any]]] = Field(None, description="Memory update history")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional response metadata")


class MemoryDeleteResponse(BaseModel):
    """Response model for memory deletion."""
    
    success: bool = Field(..., description="Whether the operation succeeded")
    message: str = Field(..., description="Deletion confirmation message")
    memory_id: str = Field(..., description="ID of deleted memory")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional response metadata")


class MemoryExportResponse(BaseModel):
    """Response model for memory export."""
    
    success: bool = Field(..., description="Whether the operation succeeded")
    data: Union[str, Dict[str, Any], List[Dict[str, Any]]] = Field(..., description="Exported data")
    format: str = Field(..., description="Export format used")
    include_metadata: bool = Field(..., description="Whether metadata was included")
    export_date: datetime = Field(..., description="Export timestamp")
    memory_count: int = Field(..., description="Number of memories exported")
    filters_applied: FiltersApplied = Field(..., description="Filters that were applied")
    execution_time_ms: int = Field(..., description="Export execution time in milliseconds")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional response metadata")


class HealthResponse(BaseModel):
    """Response model for health check."""
    
    status: str = Field(..., description="Overall health status")
    timestamp: datetime = Field(..., description="Health check timestamp")
    version: str = Field(..., description="Application version")
    components: Dict[str, Dict[str, Any]] = Field(..., description="Component health details")
    uptime_seconds: float = Field(..., description="Application uptime in seconds")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional health metadata")