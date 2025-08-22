"""
Database manager with connection pooling, transactions, and CRUD operations.
"""
import sqlite3
import threading
import time
import json
import shutil
from contextlib import contextmanager
from typing import Dict, List, Optional, Any, Union, Tuple
from pathlib import Path
from datetime import datetime, timedelta
import queue
import uuid

from core.config import get_config
from core.logging import get_logger
from .schema import DatabaseSchema

logger = get_logger(__name__)


class DatabaseError(Exception):
    """Base exception for database operations."""
    pass


class ConnectionPoolError(DatabaseError):
    """Exception for connection pool issues."""
    pass


class TransactionError(DatabaseError):
    """Exception for transaction issues."""
    pass


class MigrationError(DatabaseError):
    """Exception for database migration issues."""
    pass


class ConnectionPool:
    """Thread-safe connection pool for SQLite database."""
    
    def __init__(self, db_path: str, max_connections: int = 20, timeout: int = 30):
        """
        Initialize connection pool.
        
        Args:
            db_path: Path to SQLite database
            max_connections: Maximum number of connections in pool
            timeout: Timeout in seconds for getting connection
        """
        self.db_path = db_path
        self.max_connections = max_connections
        self.timeout = timeout
        self._pool = queue.Queue(maxsize=max_connections)
        self._lock = threading.Lock()
        self._created_connections = 0
        
        logger.info(f"Initializing connection pool: max={max_connections}, timeout={timeout}s")
    
    def _create_connection(self) -> sqlite3.Connection:
        """Create a new database connection with proper settings."""
        try:
            conn = sqlite3.connect(
                self.db_path,
                timeout=self.timeout,
                check_same_thread=False
            )
            
            # Configure connection settings
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute("PRAGMA journal_mode = WAL")
            conn.execute("PRAGMA synchronous = NORMAL")
            conn.execute("PRAGMA cache_size = -10240")  # 10MB cache
            conn.execute("PRAGMA temp_store = MEMORY")
            conn.execute("PRAGMA mmap_size = 268435456")  # 256MB mmap
            conn.execute("PRAGMA busy_timeout = 30000")  # 30 second timeout
            
            # Set row factory for dict-like access
            conn.row_factory = sqlite3.Row
            
            return conn
            
        except sqlite3.Error as e:
            logger.error(f"Failed to create database connection: {e}")
            raise ConnectionPoolError(f"Failed to create connection: {e}")
    
    @contextmanager
    def get_connection(self):
        """
        Get a connection from the pool.
        
        Yields:
            sqlite3.Connection: Database connection
            
        Raises:
            ConnectionPoolError: If unable to get connection within timeout
        """
        conn = None
        start_time = time.time()
        
        try:
            # Try to get existing connection from pool
            try:
                conn = self._pool.get_nowait()
                logger.debug("Reused connection from pool")
            except queue.Empty:
                # Create new connection if pool is empty and under limit
                with self._lock:
                    if self._created_connections < self.max_connections:
                        conn = self._create_connection()
                        self._created_connections += 1
                        logger.debug(f"Created new connection ({self._created_connections}/{self.max_connections})")
                    else:
                        # Wait for connection to become available
                        try:
                            conn = self._pool.get(timeout=self.timeout)
                            logger.debug("Got connection from pool after waiting")
                        except queue.Empty:
                            raise ConnectionPoolError(f"Timeout waiting for connection ({self.timeout}s)")
            
            # Verify connection is still valid
            try:
                conn.execute("SELECT 1").fetchone()
            except sqlite3.Error:
                # Connection is invalid, create new one
                logger.warning("Invalid connection detected, creating new one")
                conn.close()
                conn = self._create_connection()
            
            yield conn
            
        except Exception as e:
            if conn:
                try:
                    conn.rollback()
                except sqlite3.Error:
                    pass
            raise
        finally:
            if conn:
                try:
                    # Return connection to pool
                    self._pool.put_nowait(conn)
                    elapsed = time.time() - start_time
                    logger.debug(f"Connection returned to pool (used for {elapsed:.3f}s)")
                except queue.Full:
                    # Pool is full, close connection
                    conn.close()
                    with self._lock:
                        self._created_connections -= 1
                    logger.debug("Pool full, closed connection")
    
    def close_all(self):
        """Close all connections in the pool."""
        with self._lock:
            while not self._pool.empty():
                try:
                    conn = self._pool.get_nowait()
                    conn.close()
                except queue.Empty:
                    break
            self._created_connections = 0
        logger.info("All connections closed")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get connection pool statistics."""
        with self._lock:
            return {
                'max_connections': self.max_connections,
                'created_connections': self._created_connections,
                'available_connections': self._pool.qsize(),
                'active_connections': self._created_connections - self._pool.qsize()
            }


class DatabaseManager:
    """Database manager with connection pooling, transactions, and CRUD operations."""
    
    def __init__(self, db_path: Optional[str] = None, pool_size: Optional[int] = None):
        """
        Initialize database manager.
        
        Args:
            db_path: Path to database file (defaults to config)
            pool_size: Connection pool size (defaults to config)
        """
        config = get_config()
        self.db_path = db_path or config.database.path
        self.pool_size = pool_size or config.database.pool_size
        self.timeout = config.database.timeout
        
        # Initialize connection pool
        self.pool = ConnectionPool(
            self.db_path,
            max_connections=self.pool_size,
            timeout=self.timeout
        )
        
        # Retry configuration
        self.max_retries = 3
        self.retry_delay = 0.1  # 100ms base delay
        
        logger.info(f"DatabaseManager initialized: {self.db_path}")
    
    def _retry_on_locked(self, operation, *args, **kwargs):
        """
        Retry operation on database locked errors.
        
        Args:
            operation: Function to retry
            *args: Arguments for operation
            **kwargs: Keyword arguments for operation
            
        Returns:
            Result of operation
            
        Raises:
            DatabaseError: If operation fails after all retries
        """
        for attempt in range(self.max_retries + 1):
            try:
                return operation(*args, **kwargs)
            except sqlite3.OperationalError as e:
                if "database is locked" in str(e).lower() and attempt < self.max_retries:
                    delay = self.retry_delay * (2 ** attempt)  # Exponential backoff
                    logger.warning(f"Database locked, retrying in {delay:.3f}s (attempt {attempt + 1}/{self.max_retries + 1})")
                    time.sleep(delay)
                    continue
                else:
                    logger.error(f"Database operation failed after {attempt + 1} attempts: {e}")
                    raise DatabaseError(f"Database operation failed: {e}")
            except Exception as e:
                logger.error(f"Unexpected error in database operation: {e}")
                raise DatabaseError(f"Unexpected database error: {e}")
    
    @contextmanager
    def transaction(self, read_only: bool = False):
        """
        Context manager for database transactions.
        
        Args:
            read_only: Whether this is a read-only transaction
            
        Yields:
            sqlite3.Connection: Database connection with active transaction
        """
        with self.pool.get_connection() as conn:
            savepoint = None
            try:
                # Check if we're already in a transaction
                if conn.in_transaction:
                    # Use savepoint for nested transactions
                    savepoint = f"sp_{int(time.time() * 1000000)}"
                    conn.execute(f"SAVEPOINT {savepoint}")
                else:
                    if not read_only:
                        conn.execute("BEGIN IMMEDIATE")
                    else:
                        conn.execute("BEGIN")
                
                yield conn
                
                if savepoint:
                    conn.execute(f"RELEASE SAVEPOINT {savepoint}")
                else:
                    if not read_only:
                        conn.commit()
                        logger.debug("Transaction committed")
                    
            except Exception as e:
                if savepoint:
                    try:
                        conn.execute(f"ROLLBACK TO SAVEPOINT {savepoint}")
                        logger.debug("Savepoint rolled back")
                    except sqlite3.Error as rollback_error:
                        logger.error(f"Failed to rollback savepoint: {rollback_error}")
                else:
                    if not read_only:
                        try:
                            conn.rollback()
                            logger.debug("Transaction rolled back")
                        except sqlite3.Error as rollback_error:
                            logger.error(f"Failed to rollback transaction: {rollback_error}")
                
                logger.error(f"Transaction failed: {e}")
                raise TransactionError(f"Transaction failed: {e}")
    
    # User CRUD operations
    def create_user(self, user_id: str, settings: Optional[Dict] = None, metadata: Optional[Dict] = None) -> bool:
        """Create a new user."""
        def _create():
            with self.transaction() as conn:
                conn.execute("""
                    INSERT INTO users (user_id, settings, metadata)
                    VALUES (?, ?, ?)
                """, (user_id, json.dumps(settings) if settings else None, json.dumps(metadata) if metadata else None))
                return True
        
        try:
            return self._retry_on_locked(_create)
        except DatabaseError as e:
            if "UNIQUE constraint failed" in str(e):
                logger.warning(f"User {user_id} already exists")
                return False
            raise
    
    def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID."""
        def _get():
            with self.transaction(read_only=True) as conn:
                cursor = conn.execute("""
                    SELECT user_id, created_at, updated_at, settings, metadata
                    FROM users WHERE user_id = ?
                """, (user_id,))
                row = cursor.fetchone()
                
                if row:
                    return {
                        'user_id': row['user_id'],
                        'created_at': row['created_at'],
                        'updated_at': row['updated_at'],
                        'settings': json.loads(row['settings']) if row['settings'] else {},
                        'metadata': json.loads(row['metadata']) if row['metadata'] else {}
                    }
                return None
        
        return self._retry_on_locked(_get)
    
    def update_user(self, user_id: str, settings: Optional[Dict] = None, metadata: Optional[Dict] = None) -> bool:
        """Update user settings and metadata."""
        def _update():
            with self.transaction() as conn:
                cursor = conn.execute("""
                    UPDATE users 
                    SET settings = COALESCE(?, settings), metadata = COALESCE(?, metadata)
                    WHERE user_id = ?
                """, (
                    json.dumps(settings) if settings is not None else None,
                    json.dumps(metadata) if metadata is not None else None,
                    user_id
                ))
                return cursor.rowcount > 0
        
        return self._retry_on_locked(_update)
    
    def delete_user(self, user_id: str) -> bool:
        """Delete user and all associated data."""
        def _delete():
            with self.transaction() as conn:
                cursor = conn.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
                return cursor.rowcount > 0
        
        return self._retry_on_locked(_delete)
    
    # Memory CRUD operations
    def create_memory(self, memory_id: str, user_id: str, content: str, 
                     original_message: Optional[str] = None, category: Optional[str] = None,
                     confidence_score: Optional[float] = None, timestamp: Optional[datetime] = None,
                     metadata: Optional[Dict] = None, embedding: Optional[bytes] = None) -> bool:
        """Create a new memory."""
        def _create():
            with self.transaction() as conn:
                conn.execute("""
                    INSERT INTO memories 
                    (memory_id, user_id, content, original_message, category, 
                     confidence_score, timestamp, metadata, embedding)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    memory_id, user_id, content, original_message, category,
                    confidence_score, timestamp.isoformat() if timestamp else None,
                    json.dumps(metadata) if metadata else None, embedding
                ))
                return True
        
        try:
            return self._retry_on_locked(_create)
        except DatabaseError as e:
            if "FOREIGN KEY constraint failed" in str(e) or "UNIQUE constraint failed" in str(e):
                logger.warning(f"Failed to create memory {memory_id}: {e}")
                return False
            raise
    
    def get_memory(self, memory_id: str) -> Optional[Dict[str, Any]]:
        """Get memory by ID."""
        def _get():
            with self.transaction(read_only=True) as conn:
                cursor = conn.execute("""
                    SELECT memory_id, user_id, content, original_message, category,
                           confidence_score, timestamp, created_at, updated_at,
                           metadata, embedding, is_active
                    FROM memories WHERE memory_id = ? AND is_active = TRUE
                """, (memory_id,))
                row = cursor.fetchone()
                
                if row:
                    return {
                        'memory_id': row['memory_id'],
                        'user_id': row['user_id'],
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
        
        return self._retry_on_locked(_get)
    
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
        
        return self._retry_on_locked(_update)
    
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
        
        return self._retry_on_locked(_delete)
    
    def list_memories(self, user_id: str, category: Optional[str] = None, 
                     limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """List memories for a user."""
        def _list():
            with self.transaction(read_only=True) as conn:
                query = """
                    SELECT memory_id, user_id, content, original_message, category,
                           confidence_score, timestamp, created_at, updated_at,
                           metadata, is_active
                    FROM memories 
                    WHERE user_id = ? AND is_active = TRUE
                """
                params = [user_id]
                
                if category:
                    query += " AND category = ?"
                    params.append(category)
                
                query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
                params.extend([limit, offset])
                
                cursor = conn.execute(query, params)
                memories = []
                
                for row in cursor.fetchall():
                    memories.append({
                        'memory_id': row['memory_id'],
                        'user_id': row['user_id'],
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
        
        return self._retry_on_locked(_list)
    
    def search_memories(self, user_id: str, query: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Search memories using FTS5."""
        def _search():
            with self.transaction(read_only=True) as conn:
                cursor = conn.execute("""
                    SELECT m.memory_id, m.user_id, m.content, m.original_message, m.category,
                           m.confidence_score, m.timestamp, m.created_at, m.updated_at,
                           m.metadata, m.is_active
                    FROM memories m
                    JOIN memories_fts fts ON m.memory_id = fts.memory_id
                    WHERE m.user_id = ? AND m.is_active = TRUE 
                    AND memories_fts MATCH ?
                    ORDER BY rank LIMIT ?
                """, (user_id, query, limit))
                
                memories = []
                for row in cursor.fetchall():
                    memories.append({
                        'memory_id': row['memory_id'],
                        'user_id': row['user_id'],
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
        
        return self._retry_on_locked(_search)
    
    # Backup and restore functionality
    def backup_database(self, backup_path: str) -> bool:
        """Create a backup of the database."""
        try:
            backup_file = Path(backup_path)
            backup_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Use SQLite's backup API for consistent backup
            with self.pool.get_connection() as source_conn:
                # Create backup connection
                backup_conn = sqlite3.connect(str(backup_file))
                try:
                    source_conn.backup(backup_conn)
                    logger.info(f"Database backup created: {backup_path}")
                    return True
                finally:
                    backup_conn.close()
                    
        except Exception as e:
            logger.error(f"Database backup failed: {e}")
            return False
    
    def restore_database(self, backup_path: str) -> bool:
        """Restore database from backup."""
        try:
            backup_file = Path(backup_path)
            if not backup_file.exists():
                logger.error(f"Backup file not found: {backup_path}")
                return False
            
            # Close all connections
            self.pool.close_all()
            
            # Use SQLite's backup API for consistency
            backup_conn = sqlite3.connect(str(backup_file))
            try:
                # Create new database connection for restore target
                target_conn = sqlite3.connect(self.db_path)
                try:
                    # Restore using SQLite's backup API
                    backup_conn.backup(target_conn)
                finally:
                    target_conn.close()
            finally:
                backup_conn.close()
            
            # Reinitialize connection pool
            self.pool = ConnectionPool(
                self.db_path,
                max_connections=self.pool_size,
                timeout=self.timeout
            )
            
            # Verify the restore worked by making a test connection
            with self.pool.get_connection() as conn:
                conn.execute("SELECT 1").fetchone()
            
            logger.info(f"Database restored from: {backup_path}")
            return True
            
        except Exception as e:
            logger.error(f"Database restore failed: {e}")
            return False
    
    # Health checks
    def health_check(self) -> Dict[str, Any]:
        """Perform database health check."""
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
            
            # Schema validation
            health['checks']['schema'] = DatabaseSchema.validate_schema(self.db_path)
            
            # FTS functionality
            health['checks']['fts'] = DatabaseSchema.test_fts_functionality(self.db_path)
            
            # Connection pool stats
            health['stats']['pool'] = self.pool.get_stats()
            
            # Database file stats
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
        """Close all database connections."""
        self.pool.close_all()
        logger.info("DatabaseManager closed")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()