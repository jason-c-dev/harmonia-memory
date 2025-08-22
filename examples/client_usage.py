"""
Example usage of the Harmonia Python client.

This script demonstrates how to use the Harmonia client library
to interact with the memory storage API.
"""
import sys
import os
import asyncio
from datetime import datetime, timedelta

# Add src to path for examples
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from client import HarmoniaClient, HarmoniaClientError


def basic_example():
    """
    Basic usage example showing memory storage and retrieval.
    """
    print("=== Basic Harmonia Client Example ===")
    
    # Initialize client
    client = HarmoniaClient(
        base_url="http://localhost:8000",
        api_key="dev-key-123"  # Use appropriate API key
    )
    
    try:
        # Check API health
        health = client.health_check()
        print(f"API Health: {health.data['status']}")
        
        # Store some memories
        user_id = "example_user"
        
        print("\nStoring memories...")
        
        messages = [
            "My name is Alice and I work as a software engineer",
            "I have a cat named Whiskers who loves to play with yarn",
            "I have a meeting tomorrow at 2pm with the development team",
            "My favorite programming language is Python",
            "I live in San Francisco and love hiking on weekends"
        ]
        
        stored_memories = []
        for message in messages:
            response = client.store_memory(user_id, message)
            if response.success:
                memory_id = response.data['memory_id']
                extracted = response.data['extracted_memory']
                print(f"Stored: {extracted} (ID: {memory_id})")
                stored_memories.append(memory_id)
            else:
                print(f"Failed to store: {message}")
        
        print(f"\nStored {len(stored_memories)} memories")
        
        # Search memories
        print("\nSearching memories...")
        
        search_queries = [
            "cat",
            "programming",
            "meeting",
            "San Francisco"
        ]
        
        for query in search_queries:
            response = client.search_memories(user_id, query, limit=3)
            if response.success:
                results = response.data['results']
                print(f"\nSearch '{query}' found {len(results)} results:")
                for result in results:
                    print(f"  - {result['content']} (score: {result['relevance_score']:.2f})")
        
        # List all memories
        print("\nListing all memories...")
        response = client.list_memories(user_id, limit=10)
        if response.success:
            memories = response.data['memories']
            print(f"Total memories: {response.data['pagination']['total_count']}")
            for memory in memories:
                print(f"  - {memory['content']} (created: {memory['created_at']})")
        
        # Export memories
        print("\nExporting memories...")
        response = client.export_memories(user_id, format="json", include_metadata=True)
        if response.success:
            export_data = response.data
            print(f"Exported {export_data['memory_count']} memories in JSON format")
            # Could save to file: with open('memories.json', 'w') as f: json.dump(export_data['data'], f)
        
        # Get specific memory
        if stored_memories:
            memory_id = stored_memories[0]
            print(f"\nGetting memory {memory_id}...")
            response = client.get_memory(memory_id)
            if response.success:
                memory = response.data['memory']
                print(f"Memory: {memory['content']}")
                print(f"Confidence: {memory['confidence_score']}")
                print(f"Category: {memory.get('category', 'None')}")
        
    except HarmoniaClientError as e:
        print(f"Client error: {e.message}")
        if e.status_code:
            print(f"Status code: {e.status_code}")
    except Exception as e:
        print(f"Unexpected error: {e}")


def advanced_filtering_example():
    """
    Advanced example showing filtering and pagination.
    """
    print("\n=== Advanced Filtering Example ===")
    
    client = HarmoniaClient(base_url="http://localhost:8000")
    user_id = "advanced_user"
    
    try:
        # Store memories with different categories and dates
        print("Setting up test data...")
        
        test_memories = [
            {"message": "I love playing tennis on weekends", "metadata": {"category": "hobbies"}},
            {"message": "Meeting with Sarah about the project", "metadata": {"category": "work"}},
            {"message": "My dog Max loves to fetch balls", "metadata": {"category": "pets"}},
            {"message": "Conference call at 10am tomorrow", "metadata": {"category": "work"}},
            {"message": "I enjoy reading science fiction books", "metadata": {"category": "hobbies"}},
        ]
        
        for item in test_memories:
            client.store_memory(user_id, item["message"], metadata=item["metadata"])
        
        # Search with category filter
        print("\nSearching work-related memories...")
        response = client.search_memories(
            user_id=user_id,
            query="meeting",
            category="work",
            limit=5
        )
        
        if response.success:
            results = response.data['results']
            print(f"Found {len(results)} work-related memories:")
            for result in results:
                print(f"  - {result['content']}")
        
        # Search with confidence filter
        print("\nSearching high-confidence memories...")
        response = client.search_memories(
            user_id=user_id,
            query="*",  # Match all
            min_confidence=0.8,
            limit=10
        )
        
        if response.success:
            results = response.data['results']
            print(f"Found {len(results)} high-confidence memories:")
            for result in results:
                print(f"  - {result['content']} (confidence: {result['confidence_score']:.2f})")
        
        # Search with date range
        print("\nSearching recent memories...")
        yesterday = datetime.now() - timedelta(days=1)
        tomorrow = datetime.now() + timedelta(days=1)
        
        response = client.search_memories(
            user_id=user_id,
            query="*",
            from_date=yesterday,
            to_date=tomorrow,
            limit=10
        )
        
        if response.success:
            results = response.data['results']
            print(f"Found {len(results)} recent memories:")
            for result in results:
                print(f"  - {result['content']}")
        
        # Pagination example
        print("\nPagination example...")
        all_memories = []
        offset = 0
        limit = 2
        
        while True:
            response = client.list_memories(
                user_id=user_id,
                limit=limit,
                offset=offset,
                sort_by="created_at",
                sort_order="desc"
            )
            
            if not response.success:
                break
            
            memories = response.data['memories']
            all_memories.extend(memories)
            
            print(f"Page {offset//limit + 1}: {len(memories)} memories")
            for memory in memories:
                print(f"  - {memory['content'][:50]}...")
            
            if not response.data['pagination']['has_more']:
                break
            
            offset += limit
        
        print(f"Total memories retrieved: {len(all_memories)}")
        
    except HarmoniaClientError as e:
        print(f"Client error: {e.message}")


def error_handling_example():
    """
    Example showing proper error handling.
    """
    print("\n=== Error Handling Example ===")
    
    # Client with invalid API key
    client = HarmoniaClient(
        base_url="http://localhost:8000",
        api_key="invalid-key"
    )
    
    try:
        # This should fail with authentication error
        response = client.store_memory("test_user", "This should fail")
        
    except AuthenticationError as e:
        print(f"Authentication failed: {e.message}")
    
    except RateLimitError as e:
        print(f"Rate limited: {e.message}")
        if e.retry_after:
            print(f"Retry after: {e.retry_after} seconds")
    
    except ValidationError as e:
        print(f"Validation error: {e.message}")
    
    except NotFoundError as e:
        print(f"Resource not found: {e.message}")
    
    except ServerError as e:
        print(f"Server error: {e.message}")
    
    except HarmoniaClientError as e:
        print(f"General client error: {e.message}")
        print(f"Status code: {e.status_code}")
        print(f"Response: {e.response}")
    
    # Try with invalid memory ID
    try:
        valid_client = HarmoniaClient(base_url="http://localhost:8000")
        response = valid_client.get_memory("non-existent-id")
        
    except NotFoundError as e:
        print(f"Memory not found: {e.message}")


def context_manager_example():
    """
    Example using client as context manager for automatic cleanup.
    """
    print("\n=== Context Manager Example ===")
    
    with HarmoniaClient(base_url="http://localhost:8000") as client:
        try:
            # Client will automatically close session when exiting context
            health = client.health_check()
            print(f"API is {health.data['status']}")
            
            # Store a memory
            response = client.store_memory(
                "context_user",
                "Using context manager for automatic resource cleanup"
            )
            
            if response.success:
                print(f"Memory stored: {response.data['memory_id']}")
            
        except HarmoniaClientError as e:
            print(f"Error: {e.message}")
    
    print("Session automatically closed")


def async_example():
    """
    Example showing how to use the client in async context.
    Note: The current client is synchronous, but you can wrap calls.
    """
    print("\n=== Async Usage Example ===")
    
    async def async_memory_operations():
        """Wrapper for async operations."""
        import asyncio
        import concurrent.futures
        
        client = HarmoniaClient(base_url="http://localhost:8000")
        
        # Use thread pool for async operations
        with concurrent.futures.ThreadPoolExecutor() as executor:
            loop = asyncio.get_event_loop()
            
            # Store multiple memories concurrently
            tasks = []
            messages = [
                "I love async programming",
                "Concurrency makes things faster",
                "Thread pools are useful for I/O"
            ]
            
            for message in messages:
                task = loop.run_in_executor(
                    executor,
                    client.store_memory,
                    "async_user",
                    message
                )
                tasks.append(task)
            
            # Wait for all tasks to complete
            results = await asyncio.gather(*tasks)
            
            print("Stored memories concurrently:")
            for result in results:
                if result.success:
                    print(f"  - {result.data['extracted_memory']}")
    
    # Run async example
    asyncio.run(async_memory_operations())


if __name__ == "__main__":
    """
    Run all examples.
    
    Make sure the Harmonia API server is running before executing:
    python main.py
    """
    print("Harmonia Python Client Examples")
    print("=" * 50)
    
    try:
        basic_example()
        advanced_filtering_example()
        error_handling_example()
        context_manager_example()
        async_example()
        
        print("\nAll examples completed!")
        
    except KeyboardInterrupt:
        print("\nExamples interrupted by user")
    except Exception as e:
        print(f"\nUnexpected error in examples: {e}")
        import traceback
        traceback.print_exc()