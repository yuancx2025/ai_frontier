from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, Index, Float
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class YouTubeVideo(Base):
    __tablename__ = "youtube_videos"

    video_id = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    url = Column(String, nullable=False)
    channel_id = Column(String, nullable=False)
    published_at = Column(DateTime, nullable=False)
    description = Column(Text)
    transcript = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Article(Base):
    """
    Unified article model for all RSS feed sources.
    Replaces separate models for OpenAI, Anthropic, Cursor, etc.
    """
    __tablename__ = "articles"

    guid = Column(String, primary_key=True)
    source = Column(String, nullable=False)  # 'openai', 'anthropic', 'cursor', etc.
    title = Column(String, nullable=False)
    url = Column(String, nullable=False)
    description = Column(Text)
    published_at = Column(DateTime, nullable=False)
    category = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Composite unique constraint: same GUID from different sources is OK
    __table_args__ = (
        Index('idx_source_guid', 'source', 'guid', unique=True),
    )


class Digest(Base):
    __tablename__ = "digests"

    id = Column(String, primary_key=True)
    article_type = Column(String, nullable=False)
    article_id = Column(String, nullable=False)
    url = Column(String, nullable=False)
    title = Column(String, nullable=False)
    summary = Column(Text, nullable=False)
    relevance_score = Column(Float, nullable=True)
    reasoning = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    sent_at = Column(DateTime, nullable=True)
