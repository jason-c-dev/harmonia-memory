"""
User-specific database manager that adapts the original DatabaseManager
interface for per-user databases (without user_id parameters).
"""
import uuid
import json
from typing import Dict, List, Optional, Any
from datetime import datetime
from contextlib import contextmanager

from core.logging import get_logger
from .manager import DatabaseManager, DatabaseError

logger = get_logger(__name__)


class UserDatabaseManager:
    """
    Database manager adapter for per-user databases.
    
    This class wraps a standard DatabaseManager and adapts its interface
    to work with per-user databases where user_id columns don't exist.
    """
    
    def __init__(self, db_manager: DatabaseManager):
        """
        Initialize with a DatabaseManager instance.
        
        Args:
            db_manager: DatabaseManager instance for this user's database
        """
        self.db_manager = db_manager
        self.db_path = db_manager.db_path
        
    @contextmanager
    def transaction(self, read_only: bool = False):
        """Context manager for database transactions."""
        with self.db_manager.transaction(read_only=read_only) as conn:
            yield conn
    
    # Memory CRUD operations (without user_id)
    def create_memory(self, memory_id: str, content: str, 
                     original_message: Optional[str] = None, category: Optional[str] = None,
                     confidence_score: Optional[float] = None, timestamp: Optional[datetime] = None,
                     metadata: Optional[Dict] = None, embedding: Optional[bytes] = None) -> bool:
        """Create a new memory (without user_id since we're in a per-user database)."""
        def _create():
            with self.transaction() as conn:
                conn.execute("""
                    INSERT INTO memories 
                    (memory_id, content, original_message, category, 
                     confidence_score, timestamp, metadata, embedding)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    memory_id, content, original_message, category,
                    confidence_score, timestamp.isoformat() if timestamp else None,
                    json.dumps(metadata) if metadata else None, embedding
                ))
                return True
        
        try:
            return self.db_manager._retry_on_locked(_create)
        except DatabaseError as e:
            if "UNIQUE constraint failed" in str(e):
                logger.warning(f"Memory {memory_id} already exists")
                return False
            raise
    
    def get_memory(self, memory_id: str) -> Optional[Dict[str, Any]]:
        """Get memory by ID."""
        def _get():
            with self.transaction(read_only=True) as conn:
                cursor = conn.execute("""
                    SELECT memory_id, content, original_message, category,
                           confidence_score, timestamp, created_at, updated_at,
                           metadata, embedding, is_active
                    FROM memories WHERE memory_id = ? AND is_active = TRUE
                """, (memory_id,))
                row = cursor.fetchone()
                
                if row:
                    return {
                        'memory_id': row['memory_id'],
                        'content': row['content'],
                        'original_message': row['original_message'],
                        'category': row['category'],
                        'confidence_score': row['confidence_score'],
                        'timestamp': datetime.fromisoformat(row['timestamp']) if row['timestamp'] else None,
                        'created_at': row['created_at'],
                        'updated_at': row['updated_at'],
                        'metadata': json.loads(row['metadata']) if row['metadata'] else {},
                        'embedding': row['embedding'],
                        'is_active': bool(row['is_active'])
                    }
                return None
        
        return self.db_manager._retry_on_locked(_get)
    
    def update_memory(self, memory_id: str, content: Optional[str] = None,
                     category: Optional[str] = None, confidence_score: Optional[float] = None,
                     metadata: Optional[Dict] = None) -> bool:
        """Update memory content and metadata."""
        def _update():
            with self.transaction() as conn:
                # First get current content for audit
                cursor = conn.execute("SELECT content FROM memories WHERE memory_id = ?", (memory_id,))
                current = cursor.fetchone()
                if not current:
                    return False
                
                previous_content = current['content']
                
                # Update memory
                update_fields = []
                params = []
                
                if content is not None:
                    update_fields.append("content = ?")
                    params.append(content)
                if category is not None:
                    update_fields.append("category = ?")
                    params.append(category)
                if confidence_score is not None:
                    update_fields.append("confidence_score = ?")
                    params.append(confidence_score)
                if metadata is not None:
                    update_fields.append("metadata = ?")
                    params.append(json.dumps(metadata))
                
                if not update_fields:
                    return True  # Nothing to update
                
                params.append(memory_id)
                
                cursor = conn.execute(f"""
                    UPDATE memories SET {', '.join(update_fields)}
                    WHERE memory_id = ? AND is_active = TRUE
                """, params)
                
                if cursor.rowcount > 0 and content is not None:
                    # Create audit record
                    conn.execute("""
                        INSERT INTO memory_updates 
                        (update_id, memory_id, previous_content, new_content, update_type, updated_by)
                        VALUES (?, ?, ?, ?, 'update', 'system')
                    """, (str(uuid.uuid4()), memory_id, previous_content, content))
                
                return cursor.rowcount > 0
        
        return self.db_manager._retry_on_locked(_update)
    
    def delete_memory(self, memory_id: str, soft_delete: bool = True) -> bool:
        """Delete memory (soft delete by default)."""
        def _delete():
            with self.transaction() as conn:
                if soft_delete:
                    cursor = conn.execute("""
                        UPDATE memories SET is_active = FALSE 
                        WHERE memory_id = ? AND is_active = TRUE
                    """, (memory_id,))
                else:
                    cursor = conn.execute("DELETE FROM memories WHERE memory_id = ?", (memory_id,))
                
                return cursor.rowcount > 0
        
        return self.db_manager._retry_on_locked(_delete)
    
    def list_memories(self, category: Optional[str] = None, 
                     limit: int = 100, offset: int = 0, 
                     sort_by: str = "created_at", sort_order: str = "desc",
                     from_date: Optional[datetime] = None, to_date: Optional[datetime] = None,
                     min_confidence: Optional[float] = None, max_confidence: Optional[float] = None,
                     include_inactive: bool = False) -> List[Dict[str, Any]]:
        """List memories with advanced filtering options."""
        def _list():
            with self.transaction(read_only=True) as conn:
                query = """
                    SELECT memory_id, content, original_message, category,
                           confidence_score, timestamp, created_at, updated_at,
                           metadata, is_active
                    FROM memories 
                    WHERE 1=1
                """
                params = []
                
                # Active/inactive filter
                if not include_inactive:
                    query += " AND is_active = TRUE"
                
                # Category filter
                if category:
                    query += " AND category = ?"
                    params.append(category)
                
                # Date range filters
                if from_date:
                    query += " AND created_at >= ?"
                    params.append(from_date.isoformat())
                
                if to_date:
                    query += " AND created_at <= ?"
                    params.append(to_date.isoformat())
                
                # Confidence filters
                if min_confidence is not None:
                    query += " AND confidence_score >= ?"
                    params.append(min_confidence)
                
                if max_confidence is not None:
                    query += " AND confidence_score <= ?"
                    params.append(max_confidence)
                
                # Sorting
                if sort_by in ['created_at', 'updated_at', 'timestamp', 'confidence_score']:
                    order = "DESC" if sort_order.lower() == "desc" else "ASC"
                    query += f" ORDER BY {sort_by} {order}"
                else:
                    query += " ORDER BY created_at DESC"
                
                # Pagination
                query += " LIMIT ? OFFSET ?"
                params.extend([limit, offset])
                
                cursor = conn.execute(query, params)
                memories = []
                
                for row in cursor.fetchall():
                    memories.append({
                        'memory_id': row['memory_id'],
                        'content': row['content'],
                        'original_message': row['original_message'],
                        'category': row['category'],
                        'confidence_score': row['confidence_score'],
                        'timestamp': datetime.fromisoformat(row['timestamp']) if row['timestamp'] else None,
                        'created_at': row['created_at'],
                        'updated_at': row['updated_at'],
                        'metadata': json.loads(row['metadata']) if row['metadata'] else {},
                        'is_active': bool(row['is_active'])
                    })
                
                return memories
        
        return self.db_manager._retry_on_locked(_list)
    
    def count_memories(self, category: Optional[str] = None,
                      from_date: Optional[datetime] = None, to_date: Optional[datetime] = None,
                      min_confidence: Optional[float] = None, max_confidence: Optional[float] = None,
                      include_inactive: bool = False) -> int:
        """Count memories with filtering options."""
        def _count():
            with self.transaction(read_only=True) as conn:
                query = "SELECT COUNT(*) FROM memories WHERE 1=1"
                params = []
                
                # Active/inactive filter
                if not include_inactive:
                    query += " AND is_active = TRUE"
                
                # Category filter
                if category:
                    query += " AND category = ?"
                    params.append(category)
                
                # Date range filters
                if from_date:
                    query += " AND created_at >= ?"
                    params.append(from_date.isoformat())
                
                if to_date:
                    query += " AND created_at <= ?"
                    params.append(to_date.isoformat())
                
                # Confidence filters
                if min_confidence is not None:
                    query += " AND confidence_score >= ?"
                    params.append(min_confidence)
                
                if max_confidence is not None:
                    query += " AND confidence_score <= ?"
                    params.append(max_confidence)
                
                cursor = conn.execute(query, params)
                return cursor.fetchone()[0]
        
        return self.db_manager._retry_on_locked(_count)
    
    def search_memories(self, query: str, limit: int = 50, offset: int = 0,
                       category: Optional[str] = None, min_confidence: Optional[float] = None) -> List[Dict[str, Any]]:
        """Search memories using FTS5."""
        def _search():
            with self.transaction(read_only=True) as conn:
                # Clean query for FTS5 - remove problematic characters
                import re
                clean_query = re.sub(r'\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2}[\.\d]*', '', query)
                clean_query = re.sub(r'[<>()"\'-]', ' ', clean_query)
                clean_query = ' '.join(clean_query.split())  # Normalize whitespace
                
                if not clean_query or len(clean_query) < 2:
                    # If query is too short after cleaning, use simple LIKE search
                    search_query = """
                        SELECT memory_id, content, original_message, category,
                               confidence_score, timestamp, created_at, updated_at,
                               metadata, is_active
                        FROM memories
                        WHERE is_active = TRUE AND content LIKE ?
                    """
                    params = [f'%{query[:20]}%']
                    
                    # Add category filter
                    if category:
                        search_query += " AND category = ?"
                        params.append(category)
                    
                    # Add confidence filter
                    if min_confidence is not None:
                        search_query += " AND confidence_score >= ?"
                        params.append(min_confidence)
                    
                    search_query += " ORDER BY confidence_score DESC LIMIT ? OFFSET ?"
                    params.extend([limit, offset])
                    
                else:
                    search_query = """
                        SELECT m.memory_id, m.content, m.original_message, m.category,
                               m.confidence_score, m.timestamp, m.created_at, m.updated_at,
                               m.metadata, m.is_active
                        FROM memories m
                        JOIN memories_fts fts ON m.memory_id = fts.memory_id
                        WHERE m.is_active = TRUE AND memories_fts MATCH ?
                    """
                    params = [clean_query]
                    
                    # Add category filter
                    if category:
                        search_query += " AND m.category = ?"
                        params.append(category)
                    
                    # Add confidence filter
                    if min_confidence is not None:
                        search_query += " AND m.confidence_score >= ?"
                        params.append(min_confidence)
                    
                    search_query += " ORDER BY rank LIMIT ? OFFSET ?"
                    params.extend([limit, offset])
                
                cursor = conn.execute(search_query, params)
                memories = []
                
                for row in cursor.fetchall():
                    memories.append({
                        'memory_id': row['memory_id'],
                        'content': row['content'],
                        'original_message': row['original_message'],
                        'category': row['category'],
                        'confidence_score': row['confidence_score'],
                        'timestamp': datetime.fromisoformat(row['timestamp']) if row['timestamp'] else None,
                        'created_at': row['created_at'],
                        'updated_at': row['updated_at'],
                        'metadata': json.loads(row['metadata']) if row['metadata'] else {},
                        'is_active': bool(row['is_active'])
                    })
                
                return memories
        
        return self.db_manager._retry_on_locked(_search)
    
    # Session management
    def create_session(self, session_id: str, metadata: Optional[Dict] = None) -> bool:
        """Create a new session."""
        def _create():
            with self.transaction() as conn:
                conn.execute("""
                    INSERT INTO sessions (session_id, metadata)
                    VALUES (?, ?)
                """, (session_id, json.dumps(metadata) if metadata else None))
                return True
        
        try:
            return self.db_manager._retry_on_locked(_create)
        except DatabaseError as e:
            if "UNIQUE constraint failed" in str(e):
                logger.warning(f"Session {session_id} already exists")
                return False
            raise
    
    def update_session(self, session_id: str, ended_at: Optional[datetime] = None,
                      message_count: Optional[int] = None, memories_created: Optional[int] = None,
                      metadata: Optional[Dict] = None) -> bool:
        """Update session information."""
        def _update():
            with self.transaction() as conn:
                update_fields = []
                params = []
                
                if ended_at is not None:
                    update_fields.append("ended_at = ?")
                    params.append(ended_at.isoformat())
                if message_count is not None:
                    update_fields.append("message_count = ?")
                    params.append(message_count)
                if memories_created is not None:
                    update_fields.append("memories_created = ?")
                    params.append(memories_created)
                if metadata is not None:
                    update_fields.append("metadata = ?")
                    params.append(json.dumps(metadata))
                
                if not update_fields:
                    return True  # Nothing to update
                
                params.append(session_id)
                
                cursor = conn.execute(f"""
                    UPDATE sessions SET {', '.join(update_fields)}
                    WHERE session_id = ?
                """, params)
                
                return cursor.rowcount > 0
        
        return self.db_manager._retry_on_locked(_update)
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session by ID."""
        def _get():
            with self.transaction(read_only=True) as conn:
                cursor = conn.execute("""
                    SELECT session_id, started_at, ended_at, message_count, 
                           memories_created, metadata
                    FROM sessions WHERE session_id = ?
                """, (session_id,))
                row = cursor.fetchone()
                
                if row:
                    return {
                        'session_id': row['session_id'],
                        'started_at': row['started_at'],
                        'ended_at': datetime.fromisoformat(row['ended_at']) if row['ended_at'] else None,
                        'message_count': row['message_count'],
                        'memories_created': row['memories_created'],
                        'metadata': json.loads(row['metadata']) if row['metadata'] else {}
                    }
                return None
        
        return self.db_manager._retry_on_locked(_get)
    
    # Backup and utility methods
    def backup_database(self, backup_path: str) -> bool:
        """Create a backup of the database."""
        return self.db_manager.backup_database(backup_path)
    
    def restore_database(self, backup_path: str) -> bool:
        """Restore database from backup."""
        return self.db_manager.restore_database(backup_path)
    
    def health_check(self) -> Dict[str, Any]:
        """Perform health check on user's memory system."""
        from .schema import DatabaseSchema
        
        health = {
            'status': 'healthy',
            'checks': {},
            'stats': {},
            'timestamp': datetime.now().isoformat()
        }
        
        try:
            # Basic connectivity check
            with self.transaction(read_only=True) as conn:
                conn.execute("SELECT 1").fetchone()
            health['checks']['connectivity'] = True
            
            # Schema validation for per-user database
            health['checks']['schema'] = DatabaseSchema.validate_user_schema(self.db_path)
            
            # FTS functionality for per-user database
            health['checks']['fts'] = DatabaseSchema.test_user_fts_functionality(self.db_path)
            
            # Connection pool stats from underlying database manager
            if hasattr(self.db_manager, 'pool'):
                health['stats']['pool'] = self.db_manager.pool.get_stats()
            
            # Database file stats
            from pathlib import Path
            db_file = Path(self.db_path)
            if db_file.exists():
                health['stats']['file_size'] = db_file.stat().st_size
            
            # Check for any failed checks
            if not all(health['checks'].values()):
                health['status'] = 'degraded'
                
        except Exception as e:
            health['status'] = 'unhealthy'
            health['error'] = str(e)
            logger.error(f"Health check failed: {e}")
        
        return health
    
    def close(self):
        """Close database connections."""
        self.db_manager.close()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()