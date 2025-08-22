"""
Search module for Harmonia Memory Storage System.

This module provides advanced search capabilities including:
- Full-text search using SQLite FTS5
- Query parsing and validation
- Advanced filtering and ranking
- Search result optimization
"""
from .search_engine import (
    SearchEngine,
    SearchFilter,
    SearchOptions,
    SearchResult,
    SearchResults,
    SearchOperator,
    SortOption,
    SortOrder,
    ExportFormat,
    SearchQueryError
)

__all__ = [
    'SearchEngine',
    'SearchFilter',
    'SearchOptions', 
    'SearchResult',
    'SearchResults',
    'SearchOperator',
    'SortOption',
    'SortOrder',
    'ExportFormat',
    'SearchQueryError'
]