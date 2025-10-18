"""
API Module - HTTP endpoints for the Quran AI service.

This module is responsible for:
- Handling HTTP requests
- Managing job queue operations
- Serving job results
- API documentation
"""

from app.api.routes import create_app

__all__ = ['create_app']
