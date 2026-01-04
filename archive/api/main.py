"""
FastAPI application for user profile management API.
"""
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
import os
import time
import logging

from app.database.user_repository import UserRepository, user_to_profile_dict
from app.database.models import Base
from app.database.connection import engine

logger = logging.getLogger(__name__)

app = FastAPI(
    title="AI Frontier User API",
    description="API for managing user profiles and preferences",
    version="1.0.0"
)

# CORS middleware - MVP: no credentials, allow all origins
# For production, replace "*" with specific frontend domain(s)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Replace with ["https://yourdomain.com"] in production
    allow_credentials=False,  # Set to False when using "*"
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)


# Pydantic models
class UserCreate(BaseModel):
    email: EmailStr
    name: str = Field(..., min_length=1)
    title: Optional[str] = None
    background: Optional[str] = None
    content_preferences: Optional[List[str]] = []
    preferences: Optional[dict] = {}
    expertise_level: str = Field(default="Medium", pattern="^(Beginner|Medium|Advanced)$")
    is_active: bool = True


class UserUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1)
    title: Optional[str] = None
    background: Optional[str] = None
    content_preferences: Optional[List[str]] = None
    preferences: Optional[dict] = None
    expertise_level: Optional[str] = Field(None, pattern="^(Beginner|Medium|Advanced)$")
    is_active: Optional[bool] = None


class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    title: Optional[str]
    background: Optional[str]
    content_preferences: Optional[List[str]]
    preferences: Optional[dict]
    expertise_level: str
    is_active: bool
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


def get_user_repo() -> UserRepository:
    """Dependency injection for UserRepository."""
    return UserRepository()


@app.on_event("startup")
async def startup_event():
    """Initialize database tables on startup with retry logic."""
    max_retries = 5
    retry_delay = 2
    
    for attempt in range(max_retries):
        try:
            logger.info(f"Attempting to create database tables (attempt {attempt + 1}/{max_retries})...")
            Base.metadata.create_all(engine)
            logger.info("Database tables created successfully")
            return
        except Exception as e:
            logger.warning(f"Failed to create tables (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                logger.error("Failed to create database tables after all retries")
                raise


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "AI Frontier User API",
        "version": "1.0.0"
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.post("/api/users", response_model=UserResponse, status_code=201)
async def create_user(user: UserCreate, repo: UserRepository = Depends(get_user_repo)):
    """Create a new user profile."""
    try:
        new_user = repo.create_user(
            email=user.email,
            name=user.name,
            title=user.title,
            background=user.background,
            content_preferences=user.content_preferences or [],
            preferences=user.preferences or {},
            expertise_level=user.expertise_level,
            is_active=user.is_active
        )
        return UserResponse(
            id=new_user.id,
            email=new_user.email,
            name=new_user.name,
            title=new_user.title,
            background=new_user.background,
            content_preferences=new_user.content_preferences or [],
            preferences=new_user.preferences or {},
            expertise_level=new_user.expertise_level,
            is_active=new_user.is_active,
            created_at=new_user.created_at.isoformat() if new_user.created_at else "",
            updated_at=new_user.updated_at.isoformat() if new_user.updated_at else ""
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating user: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create user: {str(e)}")


@app.get("/api/users/{email}", response_model=UserResponse)
async def get_user(email: str, repo: UserRepository = Depends(get_user_repo)):
    """Get user profile by email."""
    user = repo.get_user_by_email(email)
    if not user:
        raise HTTPException(status_code=404, detail=f"User with email {email} not found")
    
    return UserResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        title=user.title,
        background=user.background,
        content_preferences=user.content_preferences or [],
        preferences=user.preferences or {},
        expertise_level=user.expertise_level,
        is_active=user.is_active,
        created_at=user.created_at.isoformat() if user.created_at else "",
        updated_at=user.updated_at.isoformat() if user.updated_at else ""
    )


@app.put("/api/users/{email}", response_model=UserResponse)
async def update_user(
    email: str,
    user_update: UserUpdate,
    repo: UserRepository = Depends(get_user_repo)
):
    """Update user profile by email."""
    existing_user = repo.get_user_by_email(email)
    if not existing_user:
        raise HTTPException(status_code=404, detail=f"User with email {email} not found")
    
    try:
        updated_user = repo.update_user(
            existing_user.id,
            name=user_update.name,
            title=user_update.title,
            background=user_update.background,
            content_preferences=user_update.content_preferences,
            preferences=user_update.preferences,
            expertise_level=user_update.expertise_level,
            is_active=user_update.is_active
        )
        
        if not updated_user:
            raise HTTPException(status_code=500, detail="Failed to update user")
        
        return UserResponse(
            id=updated_user.id,
            email=updated_user.email,
            name=updated_user.name,
            title=updated_user.title,
            background=updated_user.background,
            content_preferences=updated_user.content_preferences or [],
            preferences=updated_user.preferences or {},
            expertise_level=updated_user.expertise_level,
            is_active=updated_user.is_active,
            created_at=updated_user.created_at.isoformat() if updated_user.created_at else "",
            updated_at=updated_user.updated_at.isoformat() if updated_user.updated_at else ""
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating user: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update user: {str(e)}")


@app.delete("/api/users/{email}", status_code=204)
async def delete_user(email: str, repo: UserRepository = Depends(get_user_repo)):
    """Delete user profile (soft delete by setting is_active=False)."""
    user = repo.get_user_by_email(email)
    if not user:
        raise HTTPException(status_code=404, detail=f"User with email {email} not found")
    
    try:
        repo.update_user(user.id, is_active=False)
        return None
    except Exception as e:
        logger.error(f"Error deleting user: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete user: {str(e)}")


@app.get("/api/users", response_model=List[UserResponse])
async def list_users(
    active_only: bool = True,
    repo: UserRepository = Depends(get_user_repo)
):
    """List all users (optionally filter by active status)."""
    if active_only:
        users = repo.get_all_active_users()
    else:
        users = repo.get_all_active_users()  # For now, just return active
    
    return [
        UserResponse(
            id=user.id,
            email=user.email,
            name=user.name,
            title=user.title,
            background=user.background,
            content_preferences=user.content_preferences or [],
            preferences=user.preferences or {},
            expertise_level=user.expertise_level,
            is_active=user.is_active,
            created_at=user.created_at.isoformat() if user.created_at else "",
            updated_at=user.updated_at.isoformat() if user.updated_at else ""
        )
        for user in users
    ]


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    # CRITICAL: Bind to 0.0.0.0, not localhost
    uvicorn.run(app, host="0.0.0.0", port=port)

