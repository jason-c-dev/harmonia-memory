"""
Multi-database manager for per-user database isolation.

This module provides a database manager that creates and manages separate SQLite 
databases for each user, providing complete data isolation while maintaining 
the lightweight benefits of SQLite.
"""
import os
import threading
import time
from pathlib import Path
from typing import Dict, Optional, Any, List
from datetime import datetime
import weakref

from core.config import get_config
from core.logging import get_logger
from .manager import DatabaseManager, DatabaseError
from .schema import DatabaseSchema

logger = get_logger(__name__)


class UserDatabaseError(DatabaseError):
    """Exception for user database specific issues."""
    pass


class MultiDatabaseManager:
    """
    Database manager that maintains separate SQLite databases per user.
    
    Features:
    - Automatic database creation for new users
    - Per-user database isolation
    - Connection pooling per database
    - Centralized management of multiple databases
    - Thread-safe operations
    """
    
    def __init__(self, base_path: Optional[str] = None, pool_size_per_db: Optional[int] = None):
        """
        Initialize multi-database manager.
        
        Args:
            base_path: Base directory for user databases (defaults to config)
            pool_size_per_db: Connection pool size per database (defaults to config)
        """
        config = get_config()
        
        # Use configured database path as base, but organize in user directories
        configured_db_path = base_path or config.database.path
        self.base_path = Path(configured_db_path).parent / "users"
        self.pool_size_per_db = pool_size_per_db or max(5, config.database.pool_size // 4)  # Smaller pools per DB
        
        # Thread-safe database manager cache
        self._db_managers: Dict[str, DatabaseManager] = {}
        self._managers_lock = threading.RLock()
        
        # Weak references for cleanup
        self._weak_managers = weakref.WeakValueDictionary()
        
        # Ensure base directory exists
        self.base_path.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"MultiDatabaseManager initialized: base_path={self.base_path}, pool_size_per_db={self.pool_size_per_db}")
    
    def _get_user_db_path(self, user_id: str) -> str:
        """
        Get the database path for a specific user.
        
        Args:
            user_id: User identifier
            
        Returns:
            Path to user's database file
        """
        # Sanitize user_id for filesystem safety
        safe_user_id = "".join(c for c in user_id if c.isalnum() or c in ('-', '_', '.'))
        if not safe_user_id:
            raise UserDatabaseError(f"Invalid user_id: {user_id}")
        
        user_dir = self.base_path / safe_user_id
        return str(user_dir / "harmonia.db")
    
    def _get_or_create_db_manager(self, user_id: str) -> DatabaseManager:
        """
        Get or create a database manager for a specific user.
        
        Args:
            user_id: User identifier
            
        Returns:
            DatabaseManager instance for the user
            
        Raises:
            UserDatabaseError: If database cannot be created or accessed
        """
        with self._managers_lock:
            # Check if we already have a manager for this user
            if user_id in self._db_managers:
                return self._db_managers[user_id]
            
            try:
                # Get user database path
                db_path = self._get_user_db_path(user_id)
                db_file = Path(db_path)
                
                # Create user directory if it doesn't exist
                db_file.parent.mkdir(parents=True, exist_ok=True)
                
                # Check if database exists, if not, we'll need to initialize it
                db_exists = db_file.exists()
                
                # Create database manager
                db_manager = DatabaseManager(
                    db_path=db_path,
                    pool_size=self.pool_size_per_db
                )
                
                # Initialize database schema if it's a new database
                if not db_exists:
                    self._initialize_user_database(user_id, db_manager)
                    logger.info(f"Created new database for user: {user_id}")
                
                # Cache the manager
                self._db_managers[user_id] = db_manager
                self._weak_managers[user_id] = db_manager
                
                return db_manager
                
            except Exception as e:
                logger.error(f"Failed to create database manager for user {user_id}: {e}")
                raise UserDatabaseError(f"Failed to access user database: {e}")
    
    def _initialize_user_database(self, user_id: str, db_manager: DatabaseManager):
        """
        Initialize a new user database with the required schema.
        
        Args:
            user_id: User identifier
            db_manager: Database manager for the user
            
        Raises:
            UserDatabaseError: If database initialization fails
        """
        try:
            # Create schema using the existing schema module
            schema = DatabaseSchema()
            
            # Get the database path and initialize it
            with db_manager.pool.get_connection() as conn:
                # Create all tables without user_id columns (since we have physical separation)
                schema.create_tables_without_user_id(conn)
                
                # Create indexes
                schema.create_indexes_without_user_id(conn)
                
                # Create FTS virtual tables
                schema.create_fts_tables(conn)
                
                # Create triggers for FTS updates (per-user version)
                schema.create_fts_triggers_per_user(conn)
                
                conn.commit()
                
            logger.info(f"Initialized database schema for user: {user_id}")
            
        except Exception as e:
            logger.error(f"Failed to initialize database for user {user_id}: {e}")
            raise UserDatabaseError(f"Database initialization failed: {e}")
    
    def get_user_db_manager(self, user_id: str) -> DatabaseManager:
        """
        Get the database manager for a specific user.
        
        Args:
            user_id: User identifier
            
        Returns:
            DatabaseManager instance for the user
        """
        if not user_id:
            raise UserDatabaseError("user_id cannot be empty")
        
        return self._get_or_create_db_manager(user_id)
    
    def user_exists(self, user_id: str) -> bool:
        """
        Check if a user database exists.
        
        Args:
            user_id: User identifier
            
        Returns:
            True if user database exists
        """
        try:
            db_path = self._get_user_db_path(user_id)
            return Path(db_path).exists()
        except Exception:
            return False
    
    def list_users(self) -> List[str]:
        """
        List all users that have databases.
        
        Returns:
            List of user IDs with existing databases
        """
        users = []
        try:
            if self.base_path.exists():
                for user_dir in self.base_path.iterdir():
                    if user_dir.is_dir():
                        db_file = user_dir / "harmonia.db"
                        if db_file.exists():
                            users.append(user_dir.name)
        except Exception as e:
            logger.error(f"Failed to list users: {e}")
        
        return sorted(users)
    
    def delete_user_database(self, user_id: str) -> bool:
        """
        Delete a user's database and all associated data.
        
        Args:
            user_id: User identifier
            
        Returns:
            True if database was deleted successfully
        """
        try:
            # Close any existing database manager
            with self._managers_lock:
                if user_id in self._db_managers:
                    self._db_managers[user_id].close()
                    del self._db_managers[user_id]
            
            # Delete database files
            db_path = self._get_user_db_path(user_id)
            db_file = Path(db_path)
            
            if db_file.exists():
                # Delete main database file
                db_file.unlink()
                
                # Delete WAL and SHM files if they exist
                wal_file = db_file.with_suffix('.db-wal')
                if wal_file.exists():
                    wal_file.unlink()
                
                shm_file = db_file.with_suffix('.db-shm')
                if shm_file.exists():
                    shm_file.unlink()
                
                # Try to remove user directory if it's empty
                try:
                    db_file.parent.rmdir()
                except OSError:
                    pass  # Directory not empty, that's okay
                
                logger.info(f"Deleted database for user: {user_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to delete user database {user_id}: {e}")
            return False
    
    def backup_user_database(self, user_id: str, backup_path: str) -> bool:
        """
        Create a backup of a user's database.
        
        Args:
            user_id: User identifier
            backup_path: Path for backup file
            
        Returns:
            True if backup was created successfully
        """
        try:
            db_manager = self.get_user_db_manager(user_id)
            return db_manager.backup_database(backup_path)
        except Exception as e:
            logger.error(f"Failed to backup user database {user_id}: {e}")
            return False
    
    def backup_all_databases(self, backup_dir: str) -> Dict[str, bool]:
        """
        Create backups of all user databases.
        
        Args:
            backup_dir: Directory for backup files
            
        Returns:
            Dict mapping user_id to backup success status
        """
        results = {}
        backup_path = Path(backup_dir)
        backup_path.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        for user_id in self.list_users():
            try:
                backup_file = backup_path / f"{user_id}_{timestamp}.db"
                results[user_id] = self.backup_user_database(user_id, str(backup_file))
            except Exception as e:
                logger.error(f"Failed to backup user {user_id}: {e}")
                results[user_id] = False
        
        return results
    
    def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on all user databases.
        
        Returns:
            Health status information for all databases
        """
        health = {
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'total_users': 0,
            'healthy_databases': 0,
            'unhealthy_databases': 0,
            'users': {},
            'base_path': str(self.base_path),
            'active_managers': len(self._db_managers)
        }
        
        users = self.list_users()
        health['total_users'] = len(users)
        
        for user_id in users:
            try:
                # Check health for databases we have managers for
                if user_id in self._db_managers:
                    from .user_db_manager import UserDatabaseManager
                    db_manager = self._db_managers[user_id]
                    user_db_manager = UserDatabaseManager(db_manager)
                    user_health = user_db_manager.health_check()
                    health['users'][user_id] = user_health
                    
                    if user_health['status'] == 'healthy':
                        health['healthy_databases'] += 1
                    else:
                        health['unhealthy_databases'] += 1
                else:
                    # Just verify the file exists
                    db_path = self._get_user_db_path(user_id)
                    if Path(db_path).exists():
                        health['users'][user_id] = {'status': 'not_loaded', 'file_exists': True}
                        health['healthy_databases'] += 1
                    else:
                        health['users'][user_id] = {'status': 'missing', 'file_exists': False}
                        health['unhealthy_databases'] += 1
                        
            except Exception as e:
                logger.error(f"Health check failed for user {user_id}: {e}")
                health['users'][user_id] = {'status': 'error', 'error': str(e)}
                health['unhealthy_databases'] += 1
        
        # Overall status
        if health['unhealthy_databases'] > 0:
            health['status'] = 'degraded' if health['healthy_databases'] > 0 else 'unhealthy'
        
        return health
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about all user databases.
        
        Returns:
            Statistics about the multi-database system
        """
        stats = {
            'total_users': 0,
            'active_managers': len(self._db_managers),
            'total_disk_usage': 0,
            'users': {},
            'timestamp': datetime.now().isoformat()
        }
        
        users = self.list_users()
        stats['total_users'] = len(users)
        
        for user_id in users:
            try:
                db_path = self._get_user_db_path(user_id)
                db_file = Path(db_path)
                
                user_stats = {
                    'database_size': 0,
                    'has_manager': user_id in self._db_managers
                }
                
                if db_file.exists():
                    user_stats['database_size'] = db_file.stat().st_size
                    stats['total_disk_usage'] += user_stats['database_size']
                
                # Add WAL and SHM file sizes
                wal_file = db_file.with_suffix('.db-wal')
                if wal_file.exists():
                    wal_size = wal_file.stat().st_size
                    user_stats['wal_size'] = wal_size
                    stats['total_disk_usage'] += wal_size
                
                shm_file = db_file.with_suffix('.db-shm')
                if shm_file.exists():
                    shm_size = shm_file.stat().st_size
                    user_stats['shm_size'] = shm_size
                    stats['total_disk_usage'] += shm_size
                
                stats['users'][user_id] = user_stats
                
            except Exception as e:
                logger.error(f"Failed to get stats for user {user_id}: {e}")
                stats['users'][user_id] = {'error': str(e)}
        
        return stats
    
    def cleanup_inactive_managers(self, max_idle_time: int = 300) -> int:
        """
        Clean up database managers that haven't been used recently.
        
        Args:
            max_idle_time: Maximum idle time in seconds before cleanup
            
        Returns:
            Number of managers cleaned up
        """
        cleaned_up = 0
        current_time = time.time()
        
        with self._managers_lock:
            managers_to_remove = []
            
            for user_id, manager in self._db_managers.items():
                # This is a simple cleanup - in a more sophisticated implementation,
                # you'd track last access time per manager
                try:
                    # For now, we'll just check if the manager is still referenced
                    if user_id not in self._weak_managers:
                        managers_to_remove.append(user_id)
                except Exception as e:
                    logger.error(f"Error checking manager for cleanup {user_id}: {e}")
                    managers_to_remove.append(user_id)
            
            # Clean up identified managers
            for user_id in managers_to_remove:
                try:
                    manager = self._db_managers[user_id]
                    manager.close()
                    del self._db_managers[user_id]
                    cleaned_up += 1
                    logger.debug(f"Cleaned up database manager for user: {user_id}")
                except Exception as e:
                    logger.error(f"Error cleaning up manager for user {user_id}: {e}")
        
        if cleaned_up > 0:
            logger.info(f"Cleaned up {cleaned_up} inactive database managers")
        
        return cleaned_up
    
    def close_all(self):
        """Close all database managers and connections."""
        with self._managers_lock:
            for user_id, manager in list(self._db_managers.items()):
                try:
                    manager.close()
                except Exception as e:
                    logger.error(f"Error closing manager for user {user_id}: {e}")
            
            self._db_managers.clear()
            self._weak_managers.clear()
        
        logger.info("All database managers closed")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close_all()