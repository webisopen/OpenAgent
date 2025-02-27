"""
Router package for OpenAgent API.
"""

# Import from server to avoid circular dependencies
from .server import app

__all__ = ["app"]
