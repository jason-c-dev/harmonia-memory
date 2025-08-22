"""
Factory classes for creating test model instances.
"""
import random
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from .user import User
from .memory import Memory
from .session import Session
from .category import Category


class ModelFactory:
    """Base factory class for creating test model instances."""
    
    @staticmethod
    def random_string(length: int = 10) -> str:
        """Generate a random string of specified length."""
        import string
        return ''.join(random.choices(string.ascii_letters + string.digits, k=length))
    
    @staticmethod
    def random_datetime(days_ago: int = 30) -> datetime:
        """Generate a random datetime within the last N days."""
        now = datetime.now()
        delta = timedelta(days=random.randint(0, days_ago))
        return now - delta
    
    @staticmethod
    def random_choice(choices: List[any]) -> any:
        """Pick a random choice from a list."""
        return random.choice(choices)


class UserFactory(ModelFactory):
    """Factory for creating User test instances."""
    
    SAMPLE_SETTINGS = [
        {'theme': 'dark', 'language': 'en', 'notifications': True},
        {'theme': 'light', 'language': 'es', 'notifications': False},
        {'theme': 'auto', 'language': 'fr', 'notifications': True, 'timezone': 'UTC'},
        {'theme': 'dark', 'language': 'en', 'auto_save': True, 'privacy_mode': False}
    ]
    
    SAMPLE_METADATA = [
        {'signup_date': '2024-01-15', 'source': 'web', 'plan': 'free'},
        {'signup_date': '2024-02-20', 'source': 'mobile', 'plan': 'premium'},
        {'signup_date': '2024-03-10', 'source': 'referral', 'plan': 'free', 'referrer': 'friend'},
        {'beta_tester': True, 'features': ['advanced_search', 'export']}
    ]
    
    @classmethod
    def create(cls, user_id: Optional[str] = None, **kwargs) -> User:
        """
        Create a User instance with realistic test data.
        
        Args:
            user_id: Optional user ID (generated if not provided)
            **kwargs: Additional fields to override
            
        Returns:
            User instance with test data
        """
        if user_id is None:
            user_id = f"test_user_{cls.random_string(8)}"
        
        defaults = {
            'user_id': user_id,
            'created_at': cls.random_datetime(90),
            'updated_at': cls.random_datetime(7),
            'settings': cls.random_choice(cls.SAMPLE_SETTINGS).copy(),
            'metadata': cls.random_choice(cls.SAMPLE_METADATA).copy()
        }
        
        defaults.update(kwargs)
        return User(**defaults)
    
    @classmethod
    def create_batch(cls, count: int, **common_kwargs) -> List[User]:
        """
        Create multiple User instances.
        
        Args:
            count: Number of users to create
            **common_kwargs: Common fields for all users
            
        Returns:
            List of User instances
        """
        return [cls.create(**common_kwargs) for _ in range(count)]
    
    @classmethod
    def create_simple(cls, user_id: Optional[str] = None) -> User:
        """
        Create a simple User with minimal data.
        
        Args:
            user_id: Optional user ID
            
        Returns:
            Simple User instance
        """
        if user_id is None:
            user_id = f"simple_user_{cls.random_string(6)}"
        
        return User(
            user_id=user_id,
            settings={},
            metadata={}
        )


class MemoryFactory(ModelFactory):
    """Factory for creating Memory test instances."""
    
    SAMPLE_CONTENTS = [
        "I love playing guitar in my free time",
        "My favorite restaurant is the Italian place downtown",
        "I have a meeting with the client tomorrow at 3 PM",
        "I prefer working from home on Fridays",
        "My cat's name is Whiskers and she's 3 years old",
        "I need to buy groceries: milk, bread, and eggs",
        "I enjoyed the movie we watched last night",
        "My birthday is on March 15th",
        "I'm learning Spanish and practicing daily",
        "The project deadline is next Wednesday"
    ]
    
    SAMPLE_CATEGORIES = [
        'personal', 'work', 'preferences', 'facts', 'goals', 
        'events', 'relationships', 'shopping', 'entertainment'
    ]
    
    SAMPLE_ORIGINAL_MESSAGES = [
        "Hey, I just wanted to mention that I really love playing guitar when I have some free time.",
        "You know that Italian restaurant downtown? That's my absolute favorite place to eat.",
        "Just a reminder that I have that important client meeting scheduled for tomorrow at 3 PM.",
        "I've been thinking about my work schedule, and I really prefer working from home on Fridays.",
        "I should tell you about my pet - I have a cat named Whiskers who is 3 years old."
    ]
    
    @classmethod
    def create(cls, memory_id: Optional[str] = None, user_id: Optional[str] = None, **kwargs) -> Memory:
        """
        Create a Memory instance with realistic test data.
        
        Args:
            memory_id: Optional memory ID (generated if not provided)
            user_id: Optional user ID (generated if not provided)
            **kwargs: Additional fields to override
            
        Returns:
            Memory instance with test data
        """
        if memory_id is None:
            memory_id = f"test_mem_{cls.random_string(10)}"
        if user_id is None:
            user_id = f"test_user_{cls.random_string(8)}"
        
        defaults = {
            'memory_id': memory_id,
            'user_id': user_id,
            'content': cls.random_choice(cls.SAMPLE_CONTENTS),
            'original_message': cls.random_choice(cls.SAMPLE_ORIGINAL_MESSAGES),
            'category': cls.random_choice(cls.SAMPLE_CATEGORIES),
            'confidence_score': round(random.uniform(0.7, 1.0), 2),
            'timestamp': cls.random_datetime(30),
            'created_at': cls.random_datetime(30),
            'updated_at': cls.random_datetime(7),
            'metadata': {'source': 'test', 'importance': cls.random_choice(['low', 'medium', 'high'])},
            'is_active': True
        }
        
        defaults.update(kwargs)
        return Memory(**defaults)
    
    @classmethod
    def create_batch(cls, count: int, user_id: Optional[str] = None, **common_kwargs) -> List[Memory]:
        """
        Create multiple Memory instances for a user.
        
        Args:
            count: Number of memories to create
            user_id: User ID for all memories (generated if not provided)
            **common_kwargs: Common fields for all memories
            
        Returns:
            List of Memory instances
        """
        if user_id is None:
            user_id = f"test_user_{cls.random_string(8)}"
        
        return [cls.create(user_id=user_id, **common_kwargs) for _ in range(count)]
    
    @classmethod
    def create_simple(cls, user_id: str, content: str, memory_id: Optional[str] = None) -> Memory:
        """
        Create a simple Memory with minimal data.
        
        Args:
            user_id: User ID
            content: Memory content
            memory_id: Optional memory ID
            
        Returns:
            Simple Memory instance
        """
        if memory_id is None:
            memory_id = f"simple_mem_{cls.random_string(8)}"
        
        return Memory(
            memory_id=memory_id,
            user_id=user_id,
            content=content,
            metadata={}
        )


class SessionFactory(ModelFactory):
    """Factory for creating Session test instances."""
    
    @classmethod
    def create(cls, session_id: Optional[str] = None, user_id: Optional[str] = None, **kwargs) -> Session:
        """
        Create a Session instance with realistic test data.
        
        Args:
            session_id: Optional session ID (generated if not provided)
            user_id: Optional user ID (generated if not provided)
            **kwargs: Additional fields to override
            
        Returns:
            Session instance with test data
        """
        if session_id is None:
            session_id = f"test_sess_{cls.random_string(8)}"
        if user_id is None:
            user_id = f"test_user_{cls.random_string(8)}"
        
        started_at = cls.random_datetime(7)
        is_active = random.choice([True, False])
        ended_at = None if is_active else started_at + timedelta(minutes=random.randint(5, 120))
        
        defaults = {
            'session_id': session_id,
            'user_id': user_id,
            'started_at': started_at,
            'ended_at': ended_at,
            'message_count': random.randint(1, 50),
            'memories_created': random.randint(0, 10),
            'metadata': {
                'platform': cls.random_choice(['web', 'mobile', 'cli']),
                'version': cls.random_choice(['1.0.0', '1.1.0', '1.2.0'])
            }
        }
        
        defaults.update(kwargs)
        return Session(**defaults)
    
    @classmethod
    def create_active(cls, user_id: Optional[str] = None, **kwargs) -> Session:
        """
        Create an active Session (not ended).
        
        Args:
            user_id: Optional user ID
            **kwargs: Additional fields to override
            
        Returns:
            Active Session instance
        """
        kwargs['ended_at'] = None
        return cls.create(user_id=user_id, **kwargs)
    
    @classmethod
    def create_ended(cls, user_id: Optional[str] = None, **kwargs) -> Session:
        """
        Create an ended Session.
        
        Args:
            user_id: Optional user ID
            **kwargs: Additional fields to override
            
        Returns:
            Ended Session instance
        """
        # Ensure started_at is set first
        started_at = kwargs.get('started_at', cls.random_datetime(7))
        kwargs['started_at'] = started_at
        kwargs['ended_at'] = started_at + timedelta(minutes=random.randint(5, 120))
        return cls.create(user_id=user_id, **kwargs)
    
    @classmethod
    def create_batch(cls, count: int, user_id: Optional[str] = None, **common_kwargs) -> List[Session]:
        """
        Create multiple Session instances for a user.
        
        Args:
            count: Number of sessions to create
            user_id: User ID for all sessions (generated if not provided)
            **common_kwargs: Common fields for all sessions
            
        Returns:
            List of Session instances
        """
        if user_id is None:
            user_id = f"test_user_{cls.random_string(8)}"
        
        return [cls.create(user_id=user_id, **common_kwargs) for _ in range(count)]


class CategoryFactory(ModelFactory):
    """Factory for creating Category test instances."""
    
    SAMPLE_CATEGORIES = [
        ('work', 'Work', 'Work-related information and tasks'),
        ('personal', 'Personal', 'Personal life and experiences'),
        ('hobbies', 'Hobbies', 'Leisure activities and interests'),
        ('health', 'Health', 'Health and fitness information'),
        ('travel', 'Travel', 'Travel plans and experiences'),
        ('food', 'Food', 'Food preferences and recipes'),
        ('technology', 'Technology', 'Tech-related information'),
        ('finance', 'Finance', 'Financial information and planning')
    ]
    
    @classmethod
    def create(cls, category_id: Optional[str] = None, name: Optional[str] = None, **kwargs) -> Category:
        """
        Create a Category instance with realistic test data.
        
        Args:
            category_id: Optional category ID (generated if not provided)
            name: Optional category name (generated if not provided)
            **kwargs: Additional fields to override
            
        Returns:
            Category instance with test data
        """
        if category_id is None or name is None:
            sample_id, sample_name, sample_desc = cls.random_choice(cls.SAMPLE_CATEGORIES)
            category_id = category_id or sample_id
            name = name or sample_name
            kwargs.setdefault('description', sample_desc)
        
        defaults = {
            'category_id': category_id,
            'name': name,
            'created_at': cls.random_datetime(30)
        }
        
        defaults.update(kwargs)
        return Category(**defaults)
    
    @classmethod
    def create_hierarchy(cls) -> List[Category]:
        """
        Create a hierarchical set of categories.
        
        Returns:
            List of Category instances with parent-child relationships
        """
        categories = []
        
        # Root categories
        work = Category(category_id='work', name='Work', description='Work-related information')
        personal = Category(category_id='personal', name='Personal', description='Personal information')
        categories.extend([work, personal])
        
        # Work subcategories
        meetings = Category(
            category_id='work_meetings', 
            name='Meetings', 
            description='Work meetings and appointments',
            parent_category_id='work'
        )
        projects = Category(
            category_id='work_projects', 
            name='Projects', 
            description='Work projects and tasks',
            parent_category_id='work'
        )
        categories.extend([meetings, projects])
        
        # Personal subcategories
        family = Category(
            category_id='personal_family', 
            name='Family', 
            description='Family-related information',
            parent_category_id='personal'
        )
        hobbies = Category(
            category_id='personal_hobbies', 
            name='Hobbies', 
            description='Personal hobbies and interests',
            parent_category_id='personal'
        )
        categories.extend([family, hobbies])
        
        return categories
    
    @classmethod
    def create_default(cls) -> List[Category]:
        """
        Create default system categories.
        
        Returns:
            List of default Category instances
        """
        return Category.create_default_categories()
    
    @classmethod
    def create_batch(cls, count: int, **common_kwargs) -> List[Category]:
        """
        Create multiple Category instances.
        
        Args:
            count: Number of categories to create
            **common_kwargs: Common fields for all categories
            
        Returns:
            List of Category instances
        """
        return [cls.create(**common_kwargs) for _ in range(count)]