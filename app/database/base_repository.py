"""
Base repository with common CRUD operations.
Provides generic methods that can be reused across all repositories.
"""

from typing import List, TypeVar, Generic, Type, Optional
from sqlalchemy.orm import Session
from .connection import get_session

T = TypeVar('T')


class BaseRepository(Generic[T]):
    """
    Base repository class providing common database operations.
    
    Subclasses should set the model_class attribute to their specific model.
    """
    
    def __init__(self, session: Optional[Session] = None):
        self.session = session or get_session()
        self.model_class: Optional[Type[T]] = None  # Set by subclasses
    
    def _bulk_create_items(
        self,
        items: List[dict],
        model_class: Type[T],
        id_field: str,
        id_attr: str,
        unique_fields: Optional[List[str]] = None,
    ) -> int:
        """
        Generic bulk create with duplicate checking.
        
        Args:
            items: List of dictionaries containing item data
            model_class: SQLAlchemy model class
            id_field: Field name in the dictionary that contains the ID
            id_attr: Attribute name in the model that represents the ID
            unique_fields: Optional list of field names for composite unique check
                         (e.g., ['source', 'guid']). If provided, uses these instead
                         of single id_field/id_attr.
            
        Returns:
            Number of new items created
        """
        new_items = []
        for item in items:
            if unique_fields:
                # Composite unique check (e.g., source + guid)
                filters = {field: item[field] for field in unique_fields}
                existing = self.session.query(model_class).filter_by(**filters).first()
            else:
                # Simple single-field check
                existing = (
                    self.session.query(model_class)
                    .filter_by(**{id_attr: item[id_field]})
                    .first()
                )
            if not existing:
                new_items.append(model_class(**item))
        
        if new_items:
            self.session.add_all(new_items)
            self.session.commit()
        
        return len(new_items)
    
    def get_by_id(self, id_value: str, id_attr: str = "id") -> Optional[T]:
        """
        Get item by primary key.
        
        Args:
            id_value: Value of the primary key
            id_attr: Name of the primary key attribute
            
        Returns:
            Model instance or None if not found
        """
        if not self.model_class:
            raise ValueError("model_class must be set in subclass")
        return self.session.query(self.model_class).filter_by(
            **{id_attr: id_value}
        ).first()
    
    def get_all(self, limit: Optional[int] = None) -> List[T]:
        """
        Get all items, optionally limited.
        
        Args:
            limit: Maximum number of items to return
            
        Returns:
            List of model instances
        """
        if not self.model_class:
            raise ValueError("model_class must be set in subclass")
        query = self.session.query(self.model_class)
        if limit:
            query = query.limit(limit)
        return query.all()
