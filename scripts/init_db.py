#!/usr/bin/env python3
"""
Database initialization script for Harmonia Memory Storage System.

This script creates and initializes the SQLite database with the complete schema,
indexes, triggers, and default data.
"""
import argparse
import sys
from pathlib import Path

# Add the src directory to the Python path
script_dir = Path(__file__).parent
project_root = script_dir.parent
sys.path.insert(0, str(project_root / "src"))

from core.config import get_config
from core.logging import configure_logging, get_logger
from db.schema import DatabaseSchema


def main():
    """Main function for database initialization."""
    parser = argparse.ArgumentParser(description="Initialize Harmonia database")
    parser.add_argument(
        "--db-path", 
        help="Path to database file (default: from config)"
    )
    parser.add_argument(
        "--force", 
        action="store_true",
        help="Force recreation of existing database"
    )
    parser.add_argument(
        "--validate-only", 
        action="store_true",
        help="Only validate existing database schema"
    )
    parser.add_argument(
        "--test-fts", 
        action="store_true",
        help="Test FTS5 functionality after initialization"
    )
    parser.add_argument(
        "--verbose", "-v", 
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    # Initialize logging
    config = get_config()
    if args.verbose:
        # Override log level for verbose output
        config.logging.level = "DEBUG"
        config.logging.console.level = "DEBUG"
    
    configure_logging(config)
    logger = get_logger(__name__)
    
    # Determine database path
    db_path = args.db_path or config.database.path
    db_file = Path(db_path)
    
    logger.info(f"Harmonia Database Initialization")
    logger.info(f"Database path: {db_path}")
    
    # Check if database exists
    if db_file.exists():
        if args.validate_only:
            logger.info("Validating existing database schema...")
            if DatabaseSchema.validate_schema(db_path):
                logger.info("✅ Database schema validation passed")
                
                if args.test_fts:
                    logger.info("Testing FTS5 functionality...")
                    if DatabaseSchema.test_fts_functionality(db_path):
                        logger.info("✅ FTS5 functionality test passed")
                    else:
                        logger.error("❌ FTS5 functionality test failed")
                        sys.exit(1)
                
                sys.exit(0)
            else:
                logger.error("❌ Database schema validation failed")
                sys.exit(1)
        
        elif not args.force:
            logger.warning(f"Database already exists at: {db_path}")
            logger.info("Use --force to recreate or --validate-only to check schema")
            
            # Offer to validate existing database
            try:
                response = input("Validate existing database? (y/N): ")
                if response.lower() in ['y', 'yes']:
                    if DatabaseSchema.validate_schema(db_path):
                        logger.info("✅ Existing database schema is valid")
                        sys.exit(0)
                    else:
                        logger.error("❌ Existing database schema is invalid")
                        sys.exit(1)
                else:
                    logger.info("Database initialization cancelled")
                    sys.exit(0)
            except KeyboardInterrupt:
                logger.info("\nDatabase initialization cancelled")
                sys.exit(0)
        
        else:
            logger.warning(f"Forcing recreation of existing database: {db_path}")
            db_file.unlink()  # Remove existing database
    
    # Initialize database
    logger.info("Creating new database...")
    success = DatabaseSchema.initialize_database(db_path)
    
    if success:
        logger.info("✅ Database initialization completed successfully")
        
        # Validate the newly created database
        logger.info("Validating newly created database...")
        if DatabaseSchema.validate_schema(db_path):
            logger.info("✅ Schema validation passed")
        else:
            logger.error("❌ Schema validation failed")
            sys.exit(1)
        
        # Test FTS functionality if requested
        if args.test_fts:
            logger.info("Testing FTS5 functionality...")
            if DatabaseSchema.test_fts_functionality(db_path):
                logger.info("✅ FTS5 functionality test passed")
            else:
                logger.error("❌ FTS5 functionality test failed")
                sys.exit(1)
        
        # Display database statistics
        try:
            import sqlite3
            with sqlite3.connect(db_path) as conn:
                    cursor = conn.cursor()
                    
                    # Get table count
                    cursor.execute("""
                        SELECT COUNT(*) FROM sqlite_master 
                        WHERE type='table' AND name NOT LIKE 'sqlite_%'
                    """)
                    table_count = cursor.fetchone()[0]
                    
                    # Get index count
                    cursor.execute("""
                        SELECT COUNT(*) FROM sqlite_master 
                        WHERE type='index' AND name NOT LIKE 'sqlite_%'
                    """)
                    index_count = cursor.fetchone()[0]
                    
                    # Get trigger count
                    cursor.execute("""
                        SELECT COUNT(*) FROM sqlite_master 
                        WHERE type='trigger'
                    """)
                    trigger_count = cursor.fetchone()[0]
                    
                    logger.info(f"📊 Database Statistics:")
                    logger.info(f"   Tables: {table_count}")
                    logger.info(f"   Indexes: {index_count}")  
                    logger.info(f"   Triggers: {trigger_count}")
                    logger.info(f"   File size: {db_file.stat().st_size} bytes")
        
        except Exception as e:
            logger.warning(f"Could not retrieve database statistics: {e}")
        
        logger.info("🎉 Database is ready for use!")
        
    else:
        logger.error("❌ Database initialization failed")
        sys.exit(1)


if __name__ == "__main__":
    main()