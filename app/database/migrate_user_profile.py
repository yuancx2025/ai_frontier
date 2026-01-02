# """
# Migration script to create a default user from the existing USER_PROFILE.
# Run this once to migrate from hardcoded USER_PROFILE to database-backed user.
# """

# import sys
# import uuid
# from app.database.connection import engine, get_session
# from app.database.models import Base, User
# from app.database.user_repository import UserRepository
# from app.profiles.user_profile import USER_PROFILE


# def migrate_user_profile():
#     """
#     Create a default user in the database from the existing USER_PROFILE.
#     """
#     # Ensure tables exist
#     Base.metadata.create_all(engine)
    
#     user_repo = UserRepository()
    
#     # Check if a user already exists
#     existing_user = user_repo.get_default_user()
#     if existing_user:
#         print(f"User already exists in database: {existing_user.email}")
#         print("Skipping migration. Delete existing user first if you want to recreate.")
#         return existing_user
    
#     # Extract email from USER_PROFILE or use a default
#     # Since USER_PROFILE doesn't have email, we'll need to prompt or use a default
#     email = input("Enter email address for the default user (or press Enter to use 'user@example.com'): ").strip()
#     if not email:
#         email = "user@example.com"
#         print(f"Using default email: {email}")
    
#     # Check if email already exists
#     existing_by_email = user_repo.get_user_by_email(email)
#     if existing_by_email:
#         print(f"User with email {email} already exists.")
#         return existing_by_email
    
#     # Create user from USER_PROFILE
#     try:
#         user = user_repo.create_user(
#             email=email,
#             name=USER_PROFILE["name"],
#             title=USER_PROFILE.get("title"),
#             background=USER_PROFILE.get("background"),
#             content_preferences=USER_PROFILE.get("interests", []),  # Map interests to content_preferences
#             preferences=USER_PROFILE.get("preferences", {}),
#             expertise_level=USER_PROFILE.get("expertise_level", "Medium"),
#             is_active=True
#         )
#         print(f"✓ Successfully created user: {user.email}")
#         print(f"  Name: {user.name}")
#         print(f"  Title: {user.title or 'N/A'}")
#         print(f"  Content Preferences: {user.content_preferences}")
#         print(f"  Expertise Level: {user.expertise_level}")
#         return user
#     except Exception as e:
#         print(f"✗ Error creating user: {e}")
#         sys.exit(1)


# if __name__ == "__main__":
#     print("=" * 60)
#     print("User Profile Migration Script")
#     print("=" * 60)
#     print("\nThis script will create a default user in the database")
#     print("from the existing USER_PROFILE configuration.\n")
    
#     user = migrate_user_profile()
    
#     print("\n" + "=" * 60)
#     print("Migration complete!")
#     print("=" * 60)

# create_user_quick.py
from app.database.user_repository import UserRepository
from app.database.connection import engine
from app.database.models import Base

# Ensure tables exist
Base.metadata.create_all(engine)

user_repo = UserRepository()

# Create a new user
new_user = user_repo.create_user(
    email="alice@example.com",
    name="Alice",
    title="Data Scientist",
    background="PhD in Machine Learning, 5 years experience",
    content_preferences=[
        "Deep Learning",
        "Computer Vision",
        "Natural Language Processing"
    ],
    preferences={
        "prefer_practical": True,
        "prefer_technical_depth": True,
        "prefer_research_breakthroughs": True,
        "prefer_production_focus": False,
        "avoid_marketing_hype": True
    },
    expertise_level="Advanced",
    is_active=True
)

print(f"✓ Created user: {new_user.name} ({new_user.email})")
print(f"  ID: {new_user.id}")