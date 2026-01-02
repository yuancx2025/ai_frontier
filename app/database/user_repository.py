"""
Repository for User model.
Handles all user-related database operations.
"""

from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
import json
import uuid
from .base_repository import BaseRepository
from .models import User


def user_to_profile_dict(user: User) -> Dict[str, Any]:
    """
    Convert User model to profile dictionary format compatible with existing agents.
    
    Args:
        user: User model instance
        
    Returns:
        Dictionary in the format expected by CuratorDigestAgent and EmailAgent
    """
    # Handle content_preferences (stored as JSON/list)
    if user.content_preferences is None:
        interests = []
    elif isinstance(user.content_preferences, list):
        interests = user.content_preferences
    elif isinstance(user.content_preferences, str):
        try:
            interests = json.loads(user.content_preferences)
        except (json.JSONDecodeError, TypeError):
            interests = []
    else:
        interests = []
    
    # Handle preferences (stored as JSON/dict)
    if user.preferences is None:
        preferences = {}
    elif isinstance(user.preferences, dict):
        preferences = user.preferences
    elif isinstance(user.preferences, str):
        try:
            preferences = json.loads(user.preferences)
        except (json.JSONDecodeError, TypeError):
            preferences = {}
    else:
        preferences = {}
    
    return {
        "name": user.name,
        "title": user.title or "",
        "background": user.background or "",
        "interests": interests,  # Uses content_preferences (category names)
        "preferences": preferences,
        "expertise_level": user.expertise_level or "Medium"
    }


class UserRepository(BaseRepository):
    """
    Repository for managing user profiles.
    """
    
    def __init__(self, session: Optional[Session] = None):
        super().__init__(session)
        self.model_class = User
    
    def create_user(
        self,
        email: str,
        name: str,
        title: Optional[str] = None,
        background: Optional[str] = None,
        content_preferences: Optional[list] = None,
        preferences: Optional[dict] = None,
        expertise_level: str = "Medium",
        is_active: bool = True
    ) -> User:
        """
        Create a new user.
        
        Args:
            email: User email address (must be unique)
            name: User name
            title: Optional title/role
            background: Optional background description
            content_preferences: List of selected content category names
            preferences: Dictionary of preference flags
            expertise_level: Beginner, Medium, or Advanced
            is_active: Whether user is active
            
        Returns:
            Created User instance
            
        Raises:
            ValueError: If email already exists
        """
        # Check if user with email already exists
        existing = self.get_user_by_email(email)
        if existing:
            raise ValueError(f"User with email {email} already exists")
        
        user = User(
            email=email,
            name=name,
            title=title,
            background=background,
            content_preferences=content_preferences or [],
            preferences=preferences or {},
            expertise_level=expertise_level,
            is_active=is_active
        )
        
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        return user
    
    def get_user(self, user_id: str) -> Optional[User]:
        """
        Get user by ID.
        
        Args:
            user_id: User ID
            
        Returns:
            User instance or None if not found
        """
        return self.get_by_id(user_id, "id")
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        """
        Get user by email address.
        
        Args:
            email: User email address
            
        Returns:
            User instance or None if not found
        """
        return self.session.query(User).filter(User.email == email).first()
    
    def get_default_user(self) -> Optional[User]:
        """
        Get the default user (first active user).
        For single-user mode, returns the first active user.
        
        Returns:
            First active User instance or None if no active users exist
        """
        return self.session.query(User).filter(User.is_active == True).first()
    
    def get_all_active_users(self) -> List[User]:
        """
        Get all active users.
        For multi-user mode.
        
        Returns:
            List of active User instances
        """
        return self.session.query(User).filter(User.is_active == True).all()
    
    def update_user(
        self,
        user_id: str,
        email: Optional[str] = None,
        name: Optional[str] = None,
        title: Optional[str] = None,
        background: Optional[str] = None,
        content_preferences: Optional[list] = None,
        preferences: Optional[dict] = None,
        expertise_level: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> Optional[User]:
        """
        Update user fields.
        
        Args:
            user_id: User ID to update
            email: New email (must be unique if provided)
            name: New name
            title: New title
            background: New background
            content_preferences: New content preferences
            preferences: New preferences
            expertise_level: New expertise level
            is_active: New active status
            
        Returns:
            Updated User instance or None if not found
            
        Raises:
            ValueError: If email already exists (when updating email)
        """
        user = self.get_user(user_id)
        if not user:
            return None
        
        # Check email uniqueness if updating email
        if email and email != user.email:
            existing = self.get_user_by_email(email)
            if existing:
                raise ValueError(f"User with email {email} already exists")
            user.email = email
        
        if name is not None:
            user.name = name
        if title is not None:
            user.title = title
        if background is not None:
            user.background = background
        if content_preferences is not None:
            user.content_preferences = content_preferences
        if preferences is not None:
            user.preferences = preferences
        if expertise_level is not None:
            user.expertise_level = expertise_level
        if is_active is not None:
            user.is_active = is_active
        
        from datetime import datetime
        user.updated_at = datetime.utcnow()
        
        self.session.commit()
        self.session.refresh(user)
        return user
    
    def update_user_by_email(
        self,
        email: str,
        **kwargs
    ) -> Optional[User]:
        """
        Update user by email address.
        
        Args:
            email: User email address
            **kwargs: Fields to update (same as update_user)
            
        Returns:
            Updated User instance or None if not found
        """
        user = self.get_user_by_email(email)
        if not user:
            return None
        
        return self.update_user(user.id, **kwargs)
