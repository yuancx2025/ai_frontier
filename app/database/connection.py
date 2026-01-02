import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()


def get_environment() -> str:
    return os.getenv("ENVIRONMENT", "LOCAL").upper()


def get_database_url() -> str:
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql://", 1)
        return database_url

    user = os.getenv("POSTGRES_USER", "postgres")
    password = os.getenv("POSTGRES_PASSWORD", "postgres")
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5433")
    db = os.getenv("POSTGRES_DB", "ai-frontiers")
    return f"postgresql://{user}:{password}@{host}:{port}/{db}"


def get_database_info() -> dict:
    url = get_database_url()
    env = get_environment()

    if (
        "amazonaws.com" in url.lower()
        or "cloudsql" in url.lower()
        or "googleapis.com" in url.lower()
        or env == "PRODUCTION"
    ):
        env_type = "PRODUCTION"
    else:
        env_type = "LOCAL"

    masked_url = url
    if "@" in url:
        parts = url.split("@")
        if len(parts) == 2:
            masked_url = f"{parts[0].split('://')[0]}://***@{parts[1]}"

    return {
        "environment": env_type,
        "url_masked": masked_url,
        "host": url.split("@")[-1].split("/")[0] if "@" in url else "localhost",
    }


engine = create_engine(get_database_url())
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_session():
    return SessionLocal()


def create_all_tables():
    """Create all tables defined in models."""
    from .models import Base
    Base.metadata.create_all(engine)
    print("Tables created successfully")


def check_connection():
    """
    Check database connection and show connection info.
    Returns True if connection successful, False otherwise.
    """
    from sqlalchemy import text
    
    db_info = get_database_info()
    
    print("\n" + "=" * 60)
    print("Database Connection Check")
    print(f"Environment: {db_info['environment']}")
    print(f"Database URL: {db_info['url_masked']}")
    print(f"Host: {db_info['host']}")
    print("=" * 60 + "\n")
    
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.scalar()
            print("✓ Connection successful!")
            print(f"✓ PostgreSQL version: {version.split(',')[0]}")
            
            # Check if digests table exists
            try:
                result = conn.execute(text("SELECT COUNT(*) FROM digests"))
                count = result.scalar()
                print(f"✓ Digests table exists with {count} records")
                
                # Check for sent_at column
                result = conn.execute(
                    text("""
                        SELECT column_name 
                        FROM information_schema.columns 
                        WHERE table_name = 'digests' AND column_name = 'sent_at'
                    """)
                )
                has_sent_at = result.fetchone() is not None
                if has_sent_at:
                    print("✓ sent_at column exists")
                else:
                    print("⚠ sent_at column does not exist (run migration)")
            except Exception as e:
                print(f"⚠ Could not check tables: {e}")
            
            return True
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        return False


if __name__ == "__main__":
    # Allow running connection.py directly to check connection
    success = check_connection()
    sys.exit(0 if success else 1)
