"""
Global state management for the FastAPI application.
This module provides a centralized location for shared application state.
"""
from typing import Dict, Any, Optional

# Global application state
app_state: Dict[str, Any] = {}


def get_app_state() -> Dict[str, Any]:
    """Get the global application state."""
    return app_state


def set_app_state_item(key: str, value: Any) -> None:
    """Set an item in the application state."""
    app_state[key] = value


def get_app_state_item(key: str) -> Optional[Any]:
    """Get an item from the application state."""
    return app_state.get(key)


def clear_app_state() -> None:
    """Clear the application state."""
    app_state.clear()