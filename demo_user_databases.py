#!/usr/bin/env python3
"""
Demonstration of per-user database architecture using actual data directory.
This script shows the creation and isolation of user-specific databases.
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from db.multi_db_manager import MultiDatabaseManager
from db.user_db_manager import UserDatabaseManager
from processing.user_memory_manager import UserMemoryManager
from processing.memory_processor import MemoryProcessor
from processing.conflict_detector import ConflictDetector
from processing.conflict_resolver import ConflictResolver
from processing.temporal_resolver import TemporalResolver
from llm.ollama_client import OllamaClient
from core.config import get_config
from core.logging import configure_logging
import logging
import json
from datetime import datetime


def main():
    """Demonstrate per-user database functionality."""
    
    # Setup
    config = get_config()
    configure_logging(config)
    logger = logging.getLogger(__name__)
    
    print("\n" + "="*80)
    print("HARMONIA MEMORY STORAGE - PER-USER DATABASE DEMONSTRATION")
    print("="*80)
    
    # Use actual configured data directory
    base_path = Path(config.database.path).parent / "users"
    print(f"\nUsing data directory: {base_path}")
    print(f"Directory exists: {base_path.exists()}")
    
    # Initialize multi-database manager with actual data path
    print("\nInitializing Multi-Database Manager...")
    multi_db_manager = MultiDatabaseManager(
        base_path=str(Path(config.database.path).parent / "users"),
        pool_size_per_db=5
    )
    
    # Initialize processing components
    ollama_client = OllamaClient(
        host=config.ollama.host,
        default_model=config.ollama.model
    )
    
    memory_processor = MemoryProcessor(ollama_client=ollama_client)
    conflict_detector = ConflictDetector()
    conflict_resolver = ConflictResolver()
    temporal_resolver = TemporalResolver()
    
    # Test users
    test_users = ["alice", "bob", "charlie"]
    
    print("\n" + "-"*80)
    print("CREATING USER DATABASES")
    print("-"*80)
    
    for user_id in test_users:
        print(f"\n📁 Creating database for user: {user_id}")
        
        # Get user-specific database manager
        db_manager = multi_db_manager.get_user_db_manager(user_id)
        user_db = UserDatabaseManager(db_manager)
        
        # Create user-specific memory manager
        user_memory = UserMemoryManager(
            user_db_manager=user_db,
            memory_processor=memory_processor,
            conflict_detector=conflict_detector,
            conflict_resolver=conflict_resolver,
            temporal_resolver=temporal_resolver
        )
        
        # Add some memories for each user
        memories = [
            {
                "memory_id": f"{user_id}_memory_1",
                "content": f"This is {user_id.capitalize()}'s first memory",
                "category": "personal",
                "confidence_score": 0.8,
                "metadata": {"source": "demo_script", "tags": [user_id, "demo", "first"]}
            },
            {
                "memory_id": f"{user_id}_memory_2",
                "content": f"{user_id.capitalize()} likes to code in Python",
                "category": "preference",
                "confidence_score": 0.7,
                "metadata": {"category": "skills", "tags": [user_id, "programming", "python"]}
            }
        ]
        
        for memory in memories:
            # Store memory directly using database manager
            result = user_db.create_memory(**memory)
            print(f"  ✓ Created memory: {memory['memory_id']}")
        
        # Show database file location
        db_path = multi_db_manager._get_user_db_path(user_id)
        print(f"  📍 Database location: {db_path}")
        print(f"  📊 Database exists: {Path(db_path).exists()}")
        print(f"  📏 Database size: {Path(db_path).stat().st_size if Path(db_path).exists() else 0} bytes")
    
    print("\n" + "-"*80)
    print("VERIFYING DATA ISOLATION")
    print("-"*80)
    
    # Verify each user can only see their own data
    for user_id in test_users:
        db_manager = multi_db_manager.get_user_db_manager(user_id)
        user_db = UserDatabaseManager(db_manager)
        
        memories = user_db.list_memories(limit=10)
        print(f"\n👤 User: {user_id}")
        print(f"  Memories found: {len(memories)}")
        for mem in memories:
            print(f"    - {mem['memory_id']}: {mem['content'][:50]}...")
    
    print("\n" + "-"*80)
    print("DATABASE STATISTICS")
    print("-"*80)
    
    stats = multi_db_manager.get_statistics()
    print(f"\nTotal users: {stats['total_users']}")
    print(f"Active managers: {stats['active_managers']}")
    print(f"Total disk usage: {stats['total_disk_usage']} bytes")
    
    for user_id, user_stats in stats['users'].items():
        print(f"\n  User: {user_id}")
        print(f"    Database size: {user_stats.get('database_size', 0)} bytes")
        if 'wal_size' in user_stats:
            print(f"    WAL size: {user_stats['wal_size']} bytes")
    
    print("\n" + "-"*80)
    print("DIRECTORY STRUCTURE")
    print("-"*80)
    
    print(f"\nData directory tree ({base_path}):")
    
    def show_tree(path, prefix="", is_last=True):
        """Display directory tree."""
        connector = "└── " if is_last else "├── "
        print(f"{prefix}{connector}{path.name}")
        
        if path.is_dir():
            children = sorted(list(path.iterdir()))
            for i, child in enumerate(children):
                extension = "    " if is_last else "│   "
                show_tree(child, prefix + extension, i == len(children) - 1)
    
    if base_path.exists():
        for i, user_dir in enumerate(sorted(base_path.iterdir())):
            if user_dir.is_dir():
                show_tree(user_dir, "", i == len(list(base_path.iterdir())) - 1)
    else:
        print("  (Directory will be created on first run)")
    
    print("\n" + "-"*80)
    print("HEALTH CHECK")
    print("-"*80)
    
    health = multi_db_manager.health_check()
    print(f"\nOverall status: {health['status']}")
    print(f"Total users: {health['total_users']}")
    print(f"Healthy databases: {health['healthy_databases']}")
    print(f"Unhealthy databases: {health['unhealthy_databases']}")
    
    print("\n" + "="*80)
    print("DEMONSTRATION COMPLETE")
    print("="*80)
    print(f"\n✅ Per-user databases created in: {base_path}")
    print("✅ Each user has isolated data storage")
    print("✅ Databases are auto-created on first access")
    print("\nYou can now check the data/users/ directory to see the structure!")
    
    # Keep managers alive briefly to ensure files are written
    import time
    time.sleep(1)
    
    # Clean up
    multi_db_manager.close_all()
    ollama_client.close()


if __name__ == "__main__":
    main()