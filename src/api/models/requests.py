"""
Request models for the Harmonia Memory Storage API.

This module contains Pydantic models for API request validation.
"""
from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field, validator
from enum import Enum


class MemoryStoreRequest(BaseModel):
    """Request model for storing a memory."""
    
    user_id: str = Field(..., description="Unique identifier for the user")
    message: str = Field(..., min_length=1, max_length=10000, description="Message to extract memory from")
    session_id: Optional[str] = Field(None, description="Optional session identifier")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")
    resolution_strategy: Optional[str] = Field("auto", description="Conflict resolution strategy")
    
    @validator('user_id')
    def validate_user_id(cls, v):
        if not v or not v.strip():
            raise ValueError('User ID cannot be empty')
        return v.strip()
    
    @validator('message')
    def validate_message(cls, v):
        if not v or not v.strip():
            raise ValueError('Message cannot be empty')
        return v.strip()


class SortOrder(str, Enum):
    """Sort order enumeration."""
    ASC = "asc"
    DESC = "desc"


class SortBy(str, Enum):
    """Sort field enumeration."""
    RELEVANCE = "relevance"
    CREATED_AT = "created_at"
    UPDATED_AT = "updated_at"
    CONFIDENCE = "confidence"
    TIMESTAMP = "timestamp"


class ExportFormat(str, Enum):
    """Export format enumeration."""
    JSON = "json"
    CSV = "csv"
    MARKDOWN = "markdown"
    TEXT = "text"


class SearchRequest(BaseModel):
    """Request model for searching memories."""
    
    user_id: str = Field(..., description="Unique identifier for the user")
    query: str = Field(..., min_length=1, max_length=1000, description="Search query")
    limit: int = Field(10, ge=1, le=100, description="Maximum number of results")
    offset: int = Field(0, ge=0, description="Number of results to skip")
    from_date: Optional[datetime] = Field(None, description="Start date for filtering")
    to_date: Optional[datetime] = Field(None, description="End date for filtering")
    category: Optional[str] = Field(None, description="Memory category filter")
    min_confidence: Optional[float] = Field(None, ge=0.0, le=1.0, description="Minimum confidence score")
    max_confidence: Optional[float] = Field(None, ge=0.0, le=1.0, description="Maximum confidence score")
    sort_by: SortBy = Field(SortBy.RELEVANCE, description="Sort field")
    sort_order: SortOrder = Field(SortOrder.DESC, description="Sort order")
    include_metadata: bool = Field(False, description="Include metadata in results")
    
    @validator('user_id')
    def validate_user_id(cls, v):
        if not v or not v.strip():
            raise ValueError('User ID cannot be empty')
        return v.strip()
    
    @validator('query')
    def validate_query(cls, v):
        if not v or not v.strip():
            raise ValueError('Query cannot be empty')
        return v.strip()
    
    @validator('to_date')
    def validate_date_range(cls, v, values):
        if v and 'from_date' in values and values['from_date']:
            if v <= values['from_date']:
                raise ValueError('to_date must be after from_date')
        return v
    
    @validator('max_confidence')
    def validate_confidence_range(cls, v, values):
        if v is not None and 'min_confidence' in values and values['min_confidence'] is not None:
            if v <= values['min_confidence']:
                raise ValueError('max_confidence must be greater than min_confidence')
        return v


class MemoryListRequest(BaseModel):
    """Request model for listing memories."""
    
    user_id: str = Field(..., description="Unique identifier for the user")
    limit: int = Field(50, ge=1, le=1000, description="Maximum number of results")
    offset: int = Field(0, ge=0, description="Number of results to skip")
    from_date: Optional[datetime] = Field(None, description="Start date for filtering")
    to_date: Optional[datetime] = Field(None, description="End date for filtering")
    category: Optional[str] = Field(None, description="Memory category filter")
    min_confidence: Optional[float] = Field(None, ge=0.0, le=1.0, description="Minimum confidence score")
    max_confidence: Optional[float] = Field(None, ge=0.0, le=1.0, description="Maximum confidence score")
    sort_by: SortBy = Field(SortBy.UPDATED_AT, description="Sort field")
    sort_order: SortOrder = Field(SortOrder.DESC, description="Sort order")
    include_inactive: bool = Field(False, description="Include inactive memories")
    
    @validator('user_id')
    def validate_user_id(cls, v):
        if not v or not v.strip():
            raise ValueError('User ID cannot be empty')
        return v.strip()


class MemoryExportRequest(BaseModel):
    """Request model for exporting memories."""
    
    user_id: str = Field(..., description="Unique identifier for the user")
    format: ExportFormat = Field(ExportFormat.JSON, description="Export format")
    include_metadata: bool = Field(False, description="Include metadata in export")
    from_date: Optional[datetime] = Field(None, description="Start date for filtering")
    to_date: Optional[datetime] = Field(None, description="End date for filtering")
    category: Optional[str] = Field(None, description="Memory category filter")
    min_confidence: Optional[float] = Field(None, ge=0.0, le=1.0, description="Minimum confidence score")
    max_confidence: Optional[float] = Field(None, ge=0.0, le=1.0, description="Maximum confidence score")
    
    @validator('user_id')
    def validate_user_id(cls, v):
        if not v or not v.strip():
            raise ValueError('User ID cannot be empty')
        return v.strip()