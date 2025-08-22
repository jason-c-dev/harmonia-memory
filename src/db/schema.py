"""
Database schema definitions for Harmonia Memory Storage System.
"""
import sqlite3
from typing import List, Optional
from pathlib import Path
import logging

from core.logging import get_logger

logger = get_logger(__name__)


class DatabaseSchema:
    """Database schema management and initialization."""
    
    # Schema version for migrations
    SCHEMA_VERSION = 1
    
    # SQL DDL statements for creating tables
    CREATE_TABLES = {
        'users': """
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                settings JSON,
                metadata JSON
            )
        """,
        
        'memories': """
            CREATE TABLE IF NOT EXISTS memories (
                memory_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                content TEXT NOT NULL,
                original_message TEXT,
                category TEXT,
                confidence_score REAL,
                timestamp TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata JSON,
                embedding BLOB,
                is_active BOOLEAN DEFAULT TRUE,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
            )
        """,
        
        'memory_updates': """
            CREATE TABLE IF NOT EXISTS memory_updates (
                update_id TEXT PRIMARY KEY,
                memory_id TEXT NOT NULL,
                previous_content TEXT,
                new_content TEXT,
                update_type TEXT,
                updated_by TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata JSON,
                FOREIGN KEY (memory_id) REFERENCES memories(memory_id) ON DELETE CASCADE
            )
        """,
        
        'sessions': """
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ended_at TIMESTAMP,
                message_count INTEGER DEFAULT 0,
                memories_created INTEGER DEFAULT 0,
                metadata JSON,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
            )
        """,
        
        'categories': """
            CREATE TABLE IF NOT EXISTS categories (
                category_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                parent_category_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (parent_category_id) REFERENCES categories(category_id)
            )
        """,
        
        'schema_version': """
            CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER PRIMARY KEY,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                description TEXT
            )
        """
    }
    
    # FTS5 virtual table for full-text search
    CREATE_FTS_TABLE = """
        CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
            memory_id UNINDEXED,
            content,
            category,
            tokenize = 'porter'
        )
    """
    
    # Database indexes for performance
    CREATE_INDEXES = [
        "CREATE INDEX IF NOT EXISTS idx_memories_user_id ON memories(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_memories_timestamp ON memories(timestamp)",
        "CREATE INDEX IF NOT EXISTS idx_memories_category ON memories(category)",
        "CREATE INDEX IF NOT EXISTS idx_memories_created_at ON memories(created_at)",
        "CREATE INDEX IF NOT EXISTS idx_memories_is_active ON memories(is_active)",
        "CREATE INDEX IF NOT EXISTS idx_memory_updates_memory_id ON memory_updates(memory_id)",
        "CREATE INDEX IF NOT EXISTS idx_memory_updates_updated_at ON memory_updates(updated_at)",
        "CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_sessions_started_at ON sessions(started_at)",
        "CREATE INDEX IF NOT EXISTS idx_categories_parent ON categories(parent_category_id)"
    ]
    
    # Database triggers for maintaining data integrity
    CREATE_TRIGGERS = [
        """
        CREATE TRIGGER IF NOT EXISTS update_memories_timestamp
        AFTER UPDATE ON memories
        FOR EACH ROW
        BEGIN
            UPDATE memories SET updated_at = CURRENT_TIMESTAMP WHERE memory_id = NEW.memory_id;
        END
        """,
        
        """
        CREATE TRIGGER IF NOT EXISTS update_users_timestamp
        AFTER UPDATE ON users
        FOR EACH ROW
        BEGIN
            UPDATE users SET updated_at = CURRENT_TIMESTAMP WHERE user_id = NEW.user_id;
        END
        """,
        
        """
        CREATE TRIGGER IF NOT EXISTS sync_memories_fts_insert
        AFTER INSERT ON memories
        FOR EACH ROW
        BEGIN
            INSERT INTO memories_fts(memory_id, content, category)
            VALUES(NEW.memory_id, NEW.content, COALESCE(NEW.category, ''));
        END
        """,
        
        """
        CREATE TRIGGER IF NOT EXISTS sync_memories_fts_update
        AFTER UPDATE ON memories
        FOR EACH ROW
        BEGIN
            UPDATE memories_fts
            SET content = NEW.content, category = COALESCE(NEW.category, '')
            WHERE memory_id = NEW.memory_id;
        END
        """,
        
        """
        CREATE TRIGGER IF NOT EXISTS sync_memories_fts_delete
        AFTER DELETE ON memories
        FOR EACH ROW
        BEGIN
            DELETE FROM memories_fts WHERE memory_id = OLD.memory_id;
        END
        """
    ]
    
    # Default data to insert after schema creation
    DEFAULT_DATA = [
        """
        INSERT OR IGNORE INTO categories (category_id, name, description) VALUES
        ('personal', 'Personal', 'Personal information and preferences'),
        ('work', 'Work', 'Work-related information and tasks'),
        ('relationships', 'Relationships', 'Information about people and relationships'),
        ('preferences', 'Preferences', 'User preferences and settings'),
        ('events', 'Events', 'Scheduled events and appointments'),
        ('facts', 'Facts', 'General facts and knowledge'),
        ('other', 'Other', 'Uncategorized memories')
        """,
        
        f"""
        INSERT OR IGNORE INTO schema_version (version, description) VALUES
        ({SCHEMA_VERSION}, 'Initial database schema with FTS5 search')
        """
    ]
    
    @classmethod
    def initialize_database(cls, db_path: str, enable_foreign_keys: bool = True) -> bool:
        """
        Initialize the database with complete schema.
        
        Args:
            db_path: Path to the SQLite database file
            enable_foreign_keys: Whether to enable foreign key constraints
            
        Returns:
            True if initialization successful, False otherwise
        """
        try:
            # Ensure directory exists
            db_file = Path(db_path)
            db_file.parent.mkdir(parents=True, exist_ok=True)
            
            logger.info(f"Initializing database at: {db_path}")
            
            with sqlite3.connect(db_path) as conn:
                # Enable foreign keys if requested
                if enable_foreign_keys:
                    conn.execute("PRAGMA foreign_keys = ON")
                
                # Enable WAL mode for better concurrency
                conn.execute("PRAGMA journal_mode = WAL")
                
                # Set reasonable cache size (10MB)
                conn.execute("PRAGMA cache_size = -10240")
                
                # Create all tables
                logger.info("Creating database tables...")
                for table_name, create_sql in cls.CREATE_TABLES.items():
                    logger.debug(f"Creating table: {table_name}")
                    conn.execute(create_sql)
                
                # Create FTS table
                logger.info("Creating full-text search table...")
                conn.execute(cls.CREATE_FTS_TABLE)
                
                # Create indexes
                logger.info("Creating database indexes...")
                for index_sql in cls.CREATE_INDEXES:
                    conn.execute(index_sql)
                
                # Create triggers
                logger.info("Creating database triggers...")
                for trigger_sql in cls.CREATE_TRIGGERS:
                    conn.execute(trigger_sql)
                
                # Insert default data
                logger.info("Inserting default data...")
                for data_sql in cls.DEFAULT_DATA:
                    conn.execute(data_sql)
                
                conn.commit()
                logger.info("Database initialization completed successfully")
                return True
                
        except sqlite3.Error as e:
            logger.error(f"Database initialization failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during database initialization: {e}")
            return False
    
    @classmethod
    def validate_schema(cls, db_path: str) -> bool:
        """
        Validate that the database has the correct schema.
        
        Args:
            db_path: Path to the SQLite database file
            
        Returns:
            True if schema is valid, False otherwise
        """
        try:
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                
                # Check that all required tables exist
                cursor.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name NOT LIKE 'sqlite_%'
                """)
                tables = {row[0] for row in cursor.fetchall()}
                
                required_tables = set(cls.CREATE_TABLES.keys()) | {'memories_fts'}
                missing_tables = required_tables - tables
                
                if missing_tables:
                    logger.error(f"Missing required tables: {missing_tables}")
                    return False
                
                # Check FTS5 table exists and is functional
                cursor.execute("SELECT COUNT(*) FROM memories_fts LIMIT 1")
                
                # Check schema version
                cursor.execute("SELECT MAX(version) FROM schema_version")
                current_version = cursor.fetchone()[0]
                
                if current_version != cls.SCHEMA_VERSION:
                    logger.warning(f"Schema version mismatch: {current_version} != {cls.SCHEMA_VERSION}")
                    return False
                
                logger.info("Database schema validation passed")
                return True
                
        except sqlite3.Error as e:
            logger.error(f"Schema validation failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during schema validation: {e}")
            return False
    
    @classmethod
    def get_table_info(cls, db_path: str, table_name: str) -> Optional[List[tuple]]:
        """
        Get detailed information about a table's structure.
        
        Args:
            db_path: Path to the SQLite database file
            table_name: Name of the table to inspect
            
        Returns:
            List of column information tuples, or None if error
        """
        try:
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(f"PRAGMA table_info({table_name})")
                return cursor.fetchall()
        except sqlite3.Error as e:
            logger.error(f"Failed to get table info for {table_name}: {e}")
            return None
    
    @classmethod
    def test_fts_functionality(cls, db_path: str) -> bool:
        """
        Test that FTS5 search functionality is working.
        
        Args:
            db_path: Path to the SQLite database file
            
        Returns:
            True if FTS is functional, False otherwise
        """
        try:
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                
                # Insert test data
                test_memory_id = "test_fts_memory"
                cursor.execute("""
                    INSERT OR REPLACE INTO memories 
                    (memory_id, user_id, content, category) 
                    VALUES (?, 'test_user', 'This is a test memory for FTS functionality', 'test')
                """, (test_memory_id,))
                
                # Test FTS search
                cursor.execute("""
                    SELECT memory_id FROM memories_fts 
                    WHERE memories_fts MATCH 'test'
                """)
                results = cursor.fetchall()
                
                # Clean up test data
                cursor.execute("DELETE FROM memories WHERE memory_id = ?", (test_memory_id,))
                conn.commit()
                
                if results:
                    logger.info("FTS5 functionality test passed")
                    return True
                else:
                    logger.error("FTS5 functionality test failed - no search results")
                    return False
                    
        except sqlite3.Error as e:
            logger.error(f"FTS functionality test failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during FTS test: {e}")
            return False