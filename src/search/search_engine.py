"""
Search Engine implementation for Harmonia Memory Storage System.

This module provides advanced search capabilities including:
- Full-text search using SQLite FTS5
- Query parsing and validation
- Advanced filtering (date range, category, confidence)
- Result ranking and scoring
- Search performance optimization
"""
import re
import time
import math
import json
import csv
import io
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum

from models.memory import Memory
from db.manager import DatabaseManager
from core.logging import get_logger

logger = get_logger(__name__)


class SearchOperator(Enum):
    """Search operators for query building."""
    AND = "AND"
    OR = "OR"
    NOT = "NOT"
    PHRASE = "PHRASE"
    WILDCARD = "WILDCARD"


class SortOption(Enum):
    """Sort options for search results."""
    RELEVANCE = "relevance"
    CREATED_AT = "created_at"
    UPDATED_AT = "updated_at"
    CONFIDENCE = "confidence_score"
    TIMESTAMP = "timestamp"


class SortOrder(Enum):
    """Sort order options."""
    ASC = "asc"
    DESC = "desc"


class ExportFormat(Enum):
    """Export format options."""
    JSON = "json"
    CSV = "csv"
    MARKDOWN = "markdown"
    TEXT = "text"


@dataclass
class SearchFilter:
    """Search filter configuration."""
    category: Optional[str] = None
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None
    min_confidence: Optional[float] = None
    max_confidence: Optional[float] = None
    is_active: Optional[bool] = True


@dataclass
class SearchOptions:
    """Search configuration options."""
    limit: int = 50
    offset: int = 0
    sort_by: SortOption = SortOption.RELEVANCE
    sort_order: SortOrder = SortOrder.DESC
    include_inactive: bool = False
    boost_recent: bool = True
    boost_categories: List[str] = field(default_factory=list)


@dataclass
class SearchResult:
    """Individual search result."""
    memory: Memory
    relevance_score: float
    rank: int
    snippet: Optional[str] = None
    highlights: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert search result to dictionary."""
        return {
            'memory_id': self.memory.memory_id,
            'user_id': self.memory.user_id,
            'content': self.memory.content,
            'category': self.memory.category,
            'confidence_score': self.memory.confidence_score,
            'timestamp': self.memory.timestamp.isoformat() if self.memory.timestamp else None,
            'created_at': self.memory.created_at.isoformat() if self.memory.created_at else None,
            'updated_at': self.memory.updated_at.isoformat() if self.memory.updated_at else None,
            'relevance_score': self.relevance_score,
            'rank': self.rank,
            'snippet': self.snippet,
            'highlights': self.highlights,
            'metadata': self.memory.metadata
        }


@dataclass
class SearchResults:
    """Search results container."""
    results: List[SearchResult]
    total_count: int
    query: str
    filters: SearchFilter
    options: SearchOptions
    execution_time: float
    has_more: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert search results to dictionary."""
        return {
            'results': [r.to_dict() for r in self.results],
            'total_count': self.total_count,
            'query': self.query,
            'execution_time': self.execution_time,
            'has_more': self.has_more,
            'pagination': {
                'limit': self.options.limit,
                'offset': self.options.offset,
                'sort_by': self.options.sort_by.value,
                'sort_order': self.options.sort_order.value
            },
            'filters_applied': {
                'category': self.filters.category,
                'from_date': self.filters.from_date.isoformat() if self.filters.from_date else None,
                'to_date': self.filters.to_date.isoformat() if self.filters.to_date else None,
                'min_confidence': self.filters.min_confidence,
                'max_confidence': self.filters.max_confidence
            }
        }


class SearchQueryError(Exception):
    """Exception for search query errors."""
    pass


class SearchEngine:
    """
    Advanced search engine for memory retrieval.
    
    Features:
    - Full-text search using SQLite FTS5
    - Advanced query parsing and validation
    - Date range and category filtering
    - Relevance scoring and ranking
    - Performance optimization for large datasets
    """
    
    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        """
        Initialize SearchEngine.
        
        Args:
            db_manager: Database manager instance
        """
        self.db_manager = db_manager or DatabaseManager()
        self._search_stats = {
            'total_searches': 0,
            'avg_execution_time': 0.0,
            'cache_hits': 0
        }
        
        # FTS5 special characters that need escaping
        self._fts_special_chars = set(['"', "'", '(', ')', '-', '*', ':', '^'])
        
        # BM25 parameters
        self.k1 = 1.2  # Controls term frequency saturation point
        self.b = 0.75  # Controls length normalization (0=no normalization, 1=full normalization)
        
        # BM25 corpus statistics cache
        self._corpus_stats = {
            'avg_doc_length': 0.0,
            'total_docs': 0,
            'term_doc_freq': defaultdict(int),  # How many docs contain each term
            'last_updated': None
        }
        
        logger.info("SearchEngine initialized with BM25 scoring")
    
    def _update_corpus_stats(self, user_id: str):
        """
        Update corpus statistics for BM25 scoring.
        
        Args:
            user_id: User ID to calculate stats for
        """
        try:
            with self.db_manager.pool.get_connection() as conn:
                # Get total number of documents and average document length
                cursor = conn.execute("""
                    SELECT COUNT(*) as total_docs,
                           AVG(LENGTH(content)) as avg_length
                    FROM memories 
                    WHERE user_id = ? AND is_active = 1
                """, (user_id,))
                
                row = cursor.fetchone()
                if row:
                    self._corpus_stats['total_docs'] = row['total_docs'] or 0
                    self._corpus_stats['avg_doc_length'] = row['avg_length'] or 0.0
                
                # Calculate document frequency for each term
                # This is expensive but necessary for proper BM25
                cursor = conn.execute("""
                    SELECT content FROM memories 
                    WHERE user_id = ? AND is_active = 1
                """, (user_id,))
                
                term_doc_freq = defaultdict(int)
                for row in cursor.fetchall():
                    content = row['content'].lower()
                    # Simple tokenization - split on whitespace and punctuation
                    words = re.findall(r'\b\w+\b', content)
                    unique_words = set(words)
                    for word in unique_words:
                        term_doc_freq[word] += 1
                
                self._corpus_stats['term_doc_freq'] = term_doc_freq
                self._corpus_stats['last_updated'] = datetime.now()
                
                logger.debug(f"Updated corpus stats for user {user_id}: "
                           f"{self._corpus_stats['total_docs']} docs, "
                           f"avg length {self._corpus_stats['avg_doc_length']:.1f}")
                
        except Exception as e:
            logger.error(f"Failed to update corpus stats: {e}")
            # Use safe defaults
            self._corpus_stats = {
                'avg_doc_length': 100.0,
                'total_docs': 1,
                'term_doc_freq': defaultdict(int),
                'last_updated': datetime.now()
            }
    
    def search(self, user_id: str, query: str, 
               filters: Optional[SearchFilter] = None,
               options: Optional[SearchOptions] = None) -> SearchResults:
        """
        Perform advanced search across user memories.
        
        Args:
            user_id: User ID to search within
            query: Search query string
            filters: Optional search filters
            options: Optional search configuration
            
        Returns:
            SearchResults with ranked and filtered results
            
        Raises:
            SearchQueryError: If query is invalid
        """
        start_time = time.time()
        
        try:
            # Set defaults
            filters = filters or SearchFilter()
            options = options or SearchOptions()
            
            # Update corpus statistics if needed (cache for 5 minutes)
            if (not self._corpus_stats['last_updated'] or 
                (datetime.now() - self._corpus_stats['last_updated']).seconds > 300):
                self._update_corpus_stats(user_id)
            
            # Validate and parse query
            parsed_query = self._parse_query(query)
            if not parsed_query:
                raise SearchQueryError("Query cannot be empty")
            
            # Build FTS5 query
            fts_query = self._build_fts_query(parsed_query)
            
            # Execute search with filters
            raw_results = self._execute_search(user_id, fts_query, filters, options)
            
            # Convert to Memory objects
            memories = [Memory(**row) for row in raw_results]
            
            # Apply relevance scoring and ranking
            ranked_results = self._rank_results(memories, query, options)
            
            # Apply pagination
            paginated_results = self._apply_pagination(ranked_results, options)
            
            # Calculate totals
            total_count = len(ranked_results)
            has_more = (options.offset + len(paginated_results)) < total_count
            
            execution_time = time.time() - start_time
            
            # Update statistics
            self._update_stats(execution_time)
            
            logger.debug(f"Search completed: {len(paginated_results)} results in {execution_time:.3f}s")
            
            return SearchResults(
                results=paginated_results,
                total_count=total_count,
                query=query,
                filters=filters,
                options=options,
                execution_time=execution_time,
                has_more=has_more
            )
            
        except Exception as e:
            self._search_stats['total_searches'] += 1
            logger.error(f"Search failed for user {user_id}: {e}")
            raise SearchQueryError(f"Search failed: {e}")
    
    def _parse_query(self, query: str) -> str:
        """
        Parse and validate search query.
        
        Args:
            query: Raw search query
            
        Returns:
            Parsed and sanitized query
        """
        if not query or not query.strip():
            return ""
        
        # Remove extra whitespace
        query = query.strip()
        
        # Handle quoted phrases
        query = self._handle_quoted_phrases(query)
        
        # Escape FTS5 special characters (except those we want to preserve)
        query = self._escape_fts_characters(query)
        
        # Validate query length
        if len(query) > 1000:
            raise SearchQueryError("Query too long (max 1000 characters)")
        
        return query
    
    def _handle_quoted_phrases(self, query: str) -> str:
        """Handle quoted phrases in search query."""
        # Find quoted phrases and preserve them
        quoted_pattern = r'"([^"]*)"'
        matches = re.findall(quoted_pattern, query)
        
        # Replace quotes with FTS5 compatible format
        for match in matches:
            if match.strip():  # Only if not empty
                query = query.replace(f'"{match}"', f'"{match}"')
        
        return query
    
    def _escape_fts_characters(self, query: str) -> str:
        """Escape FTS5 special characters that could cause syntax errors."""
        # Remove problematic characters that can cause FTS5 syntax errors
        # Keep quotes for phrase search but escape others
        cleaned = query
        
        # Remove unmatched quotes
        quote_count = cleaned.count('"')
        if quote_count % 2 != 0:
            # Remove the last unmatched quote
            last_quote = cleaned.rfind('"')
            cleaned = cleaned[:last_quote] + cleaned[last_quote+1:]
        
        # Escape other problematic characters
        for char in ["'", "(", ")", "^"]:
            cleaned = cleaned.replace(char, "")
        
        return cleaned
    
    def _build_fts_query(self, query: str) -> str:
        """
        Build FTS5 compatible query.
        
        Args:
            query: Parsed search query
            
        Returns:
            FTS5 query string
        """
        if not query:
            return "*"
        
        # Split query into terms and build OR query for better keyword matching
        terms = query.split()
        if len(terms) == 1:
            # Single term - use as-is
            return query
        elif len(terms) > 1:
            # Multiple terms - use OR logic for broader matching
            # Also include phrase matching for exact sequences
            or_terms = " OR ".join(terms)
            phrase_query = f'"{query}"'
            return f"({or_terms}) OR {phrase_query}"
        
        return query
    
    def _execute_search(self, user_id: str, fts_query: str, 
                       filters: SearchFilter, options: SearchOptions) -> List[Dict[str, Any]]:
        """
        Execute search query against database.
        
        Args:
            user_id: User ID to search within
            fts_query: FTS5 query string
            filters: Search filters
            options: Search options
            
        Returns:
            Raw database results
        """
        # Build base query
        base_query = """
            SELECT m.memory_id, m.user_id, m.content, m.original_message, m.category,
                   m.confidence_score, m.timestamp, m.created_at, m.updated_at,
                   m.metadata, m.embedding, m.is_active,
                   fts.rank as fts_rank
            FROM memories m
            JOIN memories_fts fts ON m.memory_id = fts.memory_id
            WHERE m.user_id = ? AND m.is_active = ?
        """
        
        params = [user_id, not options.include_inactive]
        
        # Add FTS query
        if fts_query != "*":
            base_query += " AND memories_fts MATCH ?"
            params.append(fts_query)
        
        # Add filters
        if filters.category:
            base_query += " AND m.category = ?"
            params.append(filters.category)
        
        if filters.from_date:
            base_query += " AND m.created_at >= ?"
            params.append(filters.from_date.isoformat())
        
        if filters.to_date:
            base_query += " AND m.created_at <= ?"
            params.append(filters.to_date.isoformat())
        
        if filters.min_confidence is not None:
            base_query += " AND m.confidence_score >= ?"
            params.append(filters.min_confidence)
        
        if filters.max_confidence is not None:
            base_query += " AND m.confidence_score <= ?"
            params.append(filters.max_confidence)
        
        # Add ordering (will be re-ranked later for relevance)
        if options.sort_by == SortOption.RELEVANCE:
            base_query += " ORDER BY fts.rank"
        else:
            base_query += f" ORDER BY m.{options.sort_by.value} {options.sort_order.value}"
        
        # Execute query using database manager
        try:
            with self.db_manager.pool.get_connection() as conn:
                cursor = conn.execute(base_query, params)
                results = []
                for row in cursor.fetchall():
                    # Convert Row to dict
                    row_dict = dict(row)
                    
                    # Parse JSON fields
                    if row_dict.get('metadata'):
                        import json
                        row_dict['metadata'] = json.loads(row_dict['metadata'])
                    else:
                        row_dict['metadata'] = {}
                    
                    # Convert SQLite integer booleans to Python booleans
                    if 'is_active' in row_dict:
                        row_dict['is_active'] = bool(row_dict['is_active'])
                    
                    # Parse datetime fields
                    for field in ['timestamp', 'created_at', 'updated_at']:
                        if row_dict.get(field) and isinstance(row_dict[field], str):
                            try:
                                row_dict[field] = datetime.fromisoformat(row_dict[field])
                            except ValueError:
                                # Handle different datetime formats if needed
                                pass
                    
                    results.append(row_dict)
                return results
                
        except Exception as e:
            logger.error(f"Database search error: {e}")
            raise SearchQueryError(f"Database search failed: {e}")
    
    def _rank_results(self, memories: List[Memory], query: str, 
                     options: SearchOptions) -> List[SearchResult]:
        """
        Apply relevance ranking to search results.
        
        Args:
            memories: List of Memory objects
            query: Original search query
            options: Search options
            
        Returns:
            List of ranked SearchResult objects
        """
        results = []
        
        for i, memory in enumerate(memories):
            # BM25 relevance score
            relevance_score = self._calculate_bm25_relevance(memory, query)
            
            # Apply recency boost if enabled
            if options.boost_recent:
                relevance_score = self._apply_recency_boost(relevance_score, memory)
            
            # Apply category boost if specified
            if options.boost_categories and memory.category in options.boost_categories:
                relevance_score *= 1.2  # 20% boost for preferred categories
            
            # Generate snippet
            snippet = self._generate_snippet(memory.content, query)
            
            results.append(SearchResult(
                memory=memory,
                relevance_score=relevance_score,
                rank=i + 1,
                snippet=snippet,
                highlights=self._extract_highlights(memory.content, query)
            ))
        
        # Sort by relevance score if using relevance ranking
        if options.sort_by == SortOption.RELEVANCE:
            results.sort(key=lambda x: x.relevance_score, reverse=True)
            # Update ranks after sorting
            for i, result in enumerate(results):
                result.rank = i + 1
        
        return results
    
    def _calculate_bm25_relevance(self, memory: Memory, query: str) -> float:
        """
        Calculate BM25 relevance score.
        
        BM25 Formula:
        score = IDF * (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * |d| / avgdl))
        
        Where:
        - tf = term frequency in document
        - IDF = log((N - df + 0.5) / (df + 0.5))
        - N = total number of documents
        - df = number of documents containing term
        - |d| = document length
        - avgdl = average document length
        """
        content = memory.content.lower()
        query_terms = re.findall(r'\b\w+\b', query.lower())
        
        if not query_terms:
            return 0.1
        
        # Document length and corpus stats
        doc_length = len(re.findall(r'\b\w+\b', content))
        avg_doc_length = self._corpus_stats['avg_doc_length']
        total_docs = self._corpus_stats['total_docs']
        
        if total_docs == 0 or avg_doc_length == 0:
            return 0.1
        
        # Calculate BM25 score
        bm25_score = 0.0
        
        for term in query_terms:
            # Term frequency in document
            tf = content.count(term)
            if tf == 0:
                continue
            
            # Document frequency (number of docs containing this term)
            df = self._corpus_stats['term_doc_freq'].get(term, 1)
            
            # IDF calculation
            # Add smoothing to prevent log(0) and negative values
            idf = math.log((total_docs - df + 0.5) / (df + 0.5))
            idf = max(idf, 0.01)  # Minimum IDF to avoid negative scores
            
            # BM25 term score
            numerator = tf * (self.k1 + 1)
            denominator = tf + self.k1 * (1 - self.b + self.b * (doc_length / avg_doc_length))
            
            term_score = idf * (numerator / denominator)
            bm25_score += term_score
        
        # Apply confidence boost
        if memory.confidence_score:
            bm25_score *= memory.confidence_score
        
        return max(bm25_score, 0.1)  # Minimum score to avoid zeros
    
    def _apply_recency_boost(self, score: float, memory: Memory) -> float:
        """Apply recency boost to relevance score."""
        if not memory.created_at:
            return score
        
        days_old = (datetime.now() - memory.created_at).days
        
        # Boost recent memories (within 30 days)
        if days_old <= 30:
            boost = max(0.1, 1.0 - (days_old / 30.0) * 0.5)
            return score * (1.0 + boost)
        
        return score
    
    def _generate_snippet(self, content: str, query: str, max_length: int = 200) -> str:
        """Generate search result snippet."""
        if len(content) <= max_length:
            return content
        
        # Try to find query terms in content
        query_terms = query.lower().split()
        content_lower = content.lower()
        
        best_pos = 0
        for term in query_terms:
            pos = content_lower.find(term)
            if pos != -1:
                best_pos = max(0, pos - 50)
                break
        
        # Generate snippet around the found position
        snippet = content[best_pos:best_pos + max_length]
        
        # Add ellipsis if truncated
        if best_pos > 0:
            snippet = "..." + snippet
        if best_pos + max_length < len(content):
            snippet = snippet + "..."
        
        return snippet
    
    def _extract_highlights(self, content: str, query: str) -> List[str]:
        """Extract highlighted terms from content."""
        query_terms = query.lower().split()
        content_lower = content.lower()
        highlights = []
        
        for term in query_terms:
            if term in content_lower:
                highlights.append(term)
        
        return highlights
    
    def _apply_pagination(self, results: List[SearchResult], 
                         options: SearchOptions) -> List[SearchResult]:
        """Apply pagination to search results."""
        start_idx = options.offset
        end_idx = start_idx + options.limit
        return results[start_idx:end_idx]
    
    def _update_stats(self, execution_time: float):
        """Update search statistics."""
        self._search_stats['total_searches'] += 1
        
        # Update running average
        total = self._search_stats['total_searches']
        current_avg = self._search_stats['avg_execution_time']
        self._search_stats['avg_execution_time'] = ((current_avg * (total - 1)) + execution_time) / total
    
    def get_search_stats(self) -> Dict[str, Any]:
        """Get search engine statistics."""
        return {
            'total_searches': self._search_stats['total_searches'],
            'average_execution_time': self._search_stats['avg_execution_time'],
            'cache_hits': self._search_stats['cache_hits']
        }
    
    def health_check(self) -> Dict[str, Any]:
        """Perform search engine health check."""
        health = {
            'status': 'healthy',
            'components': {},
            'timestamp': datetime.now().isoformat()
        }
        
        try:
            # Test FTS5 functionality
            test_query = "SELECT count(*) FROM memories_fts"
            with self.db_manager.pool.get_connection() as conn:
                cursor = conn.execute(test_query)
                result = cursor.fetchone()
                health['components']['fts5'] = {
                    'status': 'healthy',
                    'indexed_memories': result[0] if result else 0
                }
            
            # Check database health
            db_health = self.db_manager.health_check()
            health['components']['database'] = db_health
            
            # Overall status
            if db_health.get('status') != 'healthy':
                health['status'] = 'degraded'
                
        except Exception as e:
            health['status'] = 'unhealthy'
            health['error'] = str(e)
            logger.error(f"Search engine health check failed: {e}")
        
        return health
    
    def list_memories(self, user_id: str, 
                      filters: Optional[SearchFilter] = None,
                      options: Optional[SearchOptions] = None) -> SearchResults:
        """
        List all memories for a user with filtering, sorting, and pagination.
        
        Args:
            user_id: User ID to list memories for
            filters: Optional filters (category, date range, confidence)
            options: Optional listing options (limit, offset, sort)
            
        Returns:
            SearchResults containing listed memories
            
        Raises:
            SearchQueryError: If listing fails
        """
        start_time = time.time()
        
        try:
            # Set defaults
            filters = filters or SearchFilter()
            options = options or SearchOptions()
            
            # Execute listing query
            raw_results = self._execute_memory_listing(user_id, filters, options)
            
            # Convert to Memory objects
            memories = [Memory(**row) for row in raw_results]
            
            # For listing, we don't need relevance scoring, just use confidence or creation order
            listing_results = self._create_listing_results(memories, options)
            
            # Apply pagination
            paginated_results = self._apply_pagination(listing_results, options)
            
            # Calculate totals
            total_count = len(listing_results)
            has_more = (options.offset + len(paginated_results)) < total_count
            
            execution_time = time.time() - start_time
            
            # Update statistics
            self._update_stats(execution_time)
            
            logger.debug(f"Memory listing completed: {len(paginated_results)} results in {execution_time:.3f}s")
            
            return SearchResults(
                results=paginated_results,
                total_count=total_count,
                query="",  # No query for listing
                filters=filters,
                options=options,
                execution_time=execution_time,
                has_more=has_more
            )
            
        except Exception as e:
            self._search_stats['total_searches'] += 1
            logger.error(f"Memory listing failed for user {user_id}: {e}")
            raise SearchQueryError(f"Memory listing failed: {e}")
    
    def _execute_memory_listing(self, user_id: str, 
                                filters: SearchFilter, 
                                options: SearchOptions) -> List[Dict[str, Any]]:
        """
        Execute memory listing query against database.
        
        Args:
            user_id: User ID to list memories for
            filters: Listing filters
            options: Listing options
            
        Returns:
            Raw database results
        """
        # Build base query
        base_query = """
            SELECT memory_id, user_id, content, original_message, category,
                   confidence_score, timestamp, created_at, updated_at,
                   metadata, embedding, is_active
            FROM memories
            WHERE user_id = ? AND is_active = ?
        """
        
        params = [user_id, not options.include_inactive]
        
        # Add filters
        if filters.category:
            base_query += " AND category = ?"
            params.append(filters.category)
        
        if filters.from_date:
            base_query += " AND created_at >= ?"
            params.append(filters.from_date.isoformat())
        
        if filters.to_date:
            base_query += " AND created_at <= ?"
            params.append(filters.to_date.isoformat())
        
        if filters.min_confidence is not None:
            base_query += " AND confidence_score >= ?"
            params.append(filters.min_confidence)
        
        if filters.max_confidence is not None:
            base_query += " AND confidence_score <= ?"
            params.append(filters.max_confidence)
        
        # Add ordering
        sort_column = options.sort_by.value
        if sort_column == "relevance":
            sort_column = "confidence_score"  # Use confidence as relevance for listing
        
        base_query += f" ORDER BY {sort_column} {options.sort_order.value}"
        
        # Execute query using database manager
        try:
            with self.db_manager.pool.get_connection() as conn:
                cursor = conn.execute(base_query, params)
                results = []
                for row in cursor.fetchall():
                    # Convert Row to dict
                    row_dict = dict(row)
                    
                    # Parse JSON fields
                    if row_dict.get('metadata'):
                        import json
                        row_dict['metadata'] = json.loads(row_dict['metadata'])
                    else:
                        row_dict['metadata'] = {}
                    
                    # Convert SQLite integer booleans to Python booleans
                    if 'is_active' in row_dict:
                        row_dict['is_active'] = bool(row_dict['is_active'])
                    
                    # Parse datetime fields
                    for field in ['timestamp', 'created_at', 'updated_at']:
                        if row_dict.get(field) and isinstance(row_dict[field], str):
                            try:
                                row_dict[field] = datetime.fromisoformat(row_dict[field])
                            except ValueError:
                                # Handle different datetime formats if needed
                                pass
                    
                    results.append(row_dict)
                return results
                
        except Exception as e:
            logger.error(f"Database listing error: {e}")
            raise SearchQueryError(f"Database listing failed: {e}")
    
    def _create_listing_results(self, memories: List[Memory], options: SearchOptions) -> List[SearchResult]:
        """
        Create SearchResult objects for memory listing.
        
        Args:
            memories: List of Memory objects
            options: Listing options
            
        Returns:
            List of SearchResult objects for listing
        """
        results = []
        
        for i, memory in enumerate(memories):
            # For listing, use confidence score as relevance or rank by position
            relevance_score = memory.confidence_score or 0.5
            
            # Generate a basic snippet (first 200 chars)
            snippet = self._generate_snippet(memory.content, "", max_length=200)
            
            results.append(SearchResult(
                memory=memory,
                relevance_score=relevance_score,
                rank=i + 1,
                snippet=snippet,
                highlights=[]  # No highlights for listing
            ))
        
        return results
    
    def export_memories(self, user_id: str, 
                        export_format: ExportFormat,
                        filters: Optional[SearchFilter] = None,
                        include_metadata: bool = False) -> Dict[str, Any]:
        """
        Export memories in specified format.
        
        Args:
            user_id: User ID to export memories for
            export_format: Export format (JSON, CSV, Markdown, Text)
            filters: Optional filters to apply during export
            include_metadata: Whether to include metadata in export
            
        Returns:
            Dictionary containing export data and metadata
            
        Raises:
            SearchQueryError: If export fails
        """
        start_time = time.time()
        
        try:
            # Get all memories matching filters
            options = SearchOptions(limit=100000)  # Large limit to get all memories
            results = self.list_memories(user_id, filters, options)
            memories = [result.memory for result in results.results]
            
            # Generate export data based on format
            if export_format == ExportFormat.JSON:
                export_data = self._export_to_json(memories, include_metadata)
            elif export_format == ExportFormat.CSV:
                export_data = self._export_to_csv(memories, include_metadata)
            elif export_format == ExportFormat.MARKDOWN:
                export_data = self._export_to_markdown(memories, include_metadata)
            elif export_format == ExportFormat.TEXT:
                export_data = self._export_to_text(memories, include_metadata)
            else:
                raise SearchQueryError(f"Unsupported export format: {export_format.value}")
            
            execution_time = time.time() - start_time
            
            logger.info(f"Export completed for user {user_id}: {len(memories)} memories in "
                       f"{export_format.value} format ({execution_time:.3f}s)")
            
            return {
                'success': True,
                'data': export_data,
                'format': export_format.value,
                'memory_count': len(memories),
                'export_date': datetime.now().isoformat(),
                'execution_time': execution_time,
                'filters_applied': {
                    'category': filters.category if filters else None,
                    'from_date': filters.from_date.isoformat() if filters and filters.from_date else None,
                    'to_date': filters.to_date.isoformat() if filters and filters.to_date else None,
                    'min_confidence': filters.min_confidence if filters else None,
                    'max_confidence': filters.max_confidence if filters else None
                },
                'include_metadata': include_metadata
            }
            
        except Exception as e:
            logger.error(f"Export failed for user {user_id}: {e}")
            raise SearchQueryError(f"Export failed: {e}")
    
    def _export_to_json(self, memories: List[Memory], include_metadata: bool = False) -> str:
        """Export memories to JSON format."""
        export_data = []
        
        for memory in memories:
            memory_data = {
                'memory_id': memory.memory_id,
                'content': memory.content,
                'category': memory.category,
                'confidence_score': memory.confidence_score,
                'created_at': memory.created_at.isoformat() if memory.created_at else None,
                'updated_at': memory.updated_at.isoformat() if memory.updated_at else None,
                'timestamp': memory.timestamp.isoformat() if memory.timestamp else None,
                'is_active': memory.is_active
            }
            
            if include_metadata:
                memory_data.update({
                    'user_id': memory.user_id,
                    'original_message': memory.original_message,
                    'metadata': memory.metadata,
                    'embedding': memory.embedding
                })
            
            export_data.append(memory_data)
        
        return json.dumps(export_data, indent=2, ensure_ascii=False)
    
    def _export_to_csv(self, memories: List[Memory], include_metadata: bool = False) -> str:
        """Export memories to CSV format."""
        if not memories:
            return ""
        
        output = io.StringIO()
        
        # Define CSV fields
        basic_fields = [
            'memory_id', 'content', 'category', 'confidence_score',
            'created_at', 'updated_at', 'timestamp', 'is_active'
        ]
        
        metadata_fields = [
            'user_id', 'original_message', 'metadata'
        ]
        
        fieldnames = basic_fields + (metadata_fields if include_metadata else [])
        
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        
        for memory in memories:
            row_data = {
                'memory_id': memory.memory_id,
                'content': memory.content,
                'category': memory.category,
                'confidence_score': memory.confidence_score,
                'created_at': memory.created_at.isoformat() if memory.created_at else '',
                'updated_at': memory.updated_at.isoformat() if memory.updated_at else '',
                'timestamp': memory.timestamp.isoformat() if memory.timestamp else '',
                'is_active': memory.is_active
            }
            
            if include_metadata:
                row_data.update({
                    'user_id': memory.user_id,
                    'original_message': memory.original_message or '',
                    'metadata': json.dumps(memory.metadata) if memory.metadata else ''
                })
            
            writer.writerow(row_data)
        
        return output.getvalue()
    
    def _export_to_markdown(self, memories: List[Memory], include_metadata: bool = False) -> str:
        """Export memories to Markdown format."""
        if not memories:
            return "# Memory Export\n\nNo memories found.\n"
        
        lines = [
            "# Memory Export",
            f"\n**Export Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Total Memories:** {len(memories)}",
            "\n---\n"
        ]
        
        for i, memory in enumerate(memories, 1):
            lines.append(f"## Memory {i}")
            lines.append("")
            lines.append(f"**Content:** {memory.content}")
            lines.append(f"**Category:** {memory.category or 'Uncategorized'}")
            lines.append(f"**Confidence:** {memory.confidence_score:.2f}")
            
            if memory.created_at:
                lines.append(f"**Created:** {memory.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
            
            if include_metadata:
                lines.append(f"**ID:** {memory.memory_id}")
                lines.append(f"**User ID:** {memory.user_id}")
                if memory.original_message:
                    lines.append(f"**Original Message:** {memory.original_message}")
                if memory.metadata:
                    lines.append(f"**Metadata:** ```json\n{json.dumps(memory.metadata, indent=2)}\n```")
            
            lines.append("\n---\n")
        
        return "\n".join(lines)
    
    def _export_to_text(self, memories: List[Memory], include_metadata: bool = False) -> str:
        """Export memories to plain text format."""
        if not memories:
            return "Memory Export\n============\n\nNo memories found.\n"
        
        lines = [
            "Memory Export",
            "=============",
            f"\nExport Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"Total Memories: {len(memories)}",
            "\n" + "="*50 + "\n"
        ]
        
        for i, memory in enumerate(memories, 1):
            lines.append(f"Memory {i}")
            lines.append("-" * len(f"Memory {i}"))
            lines.append(f"Content: {memory.content}")
            lines.append(f"Category: {memory.category or 'Uncategorized'}")
            lines.append(f"Confidence: {memory.confidence_score:.2f}")
            
            if memory.created_at:
                lines.append(f"Created: {memory.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
            
            if include_metadata:
                lines.append(f"ID: {memory.memory_id}")
                lines.append(f"User ID: {memory.user_id}")
                if memory.original_message:
                    lines.append(f"Original Message: {memory.original_message}")
                if memory.metadata:
                    lines.append(f"Metadata: {json.dumps(memory.metadata)}")
            
            lines.append("\n" + "-"*30 + "\n")
        
        return "\n".join(lines)
    
    def close(self):
        """Close search engine and cleanup resources."""
        try:
            # Database manager has its own close method
            logger.info("SearchEngine closed")
        except Exception as e:
            logger.error(f"Error closing SearchEngine: {e}")