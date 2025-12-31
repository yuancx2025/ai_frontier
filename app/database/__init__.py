"""
Database package exports.
Provides convenient access to main components.
"""

from .connection import (
    get_session,
    engine,
    create_all_tables,
    check_connection,
    get_database_info,
    get_database_url,
    get_environment,
)
from .models import (
    Base,
    YouTubeVideo,
    Article,
    Digest,
)
from .base_repository import BaseRepository
from .article_repository import ArticleRepository
from .youtube_repository import YouTubeRepository
from .digest_repository import DigestRepository

__all__ = [
    # Connection
    "get_session",
    "engine",
    "create_all_tables",
    "check_connection",
    "get_database_info",
    "get_database_url",
    "get_environment",
    # Models
    "Base",
    "YouTubeVideo",
    "Article",
    "Digest",
    # Repositories
    "BaseRepository",
    "ArticleRepository",
    "YouTubeRepository",
    "DigestRepository",
]
