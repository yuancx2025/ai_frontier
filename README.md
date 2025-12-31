# AI News Aggregator

An intelligent news aggregation system that scrapes AI-related content from multiple sources (YouTube channels, RSS feeds), processes them with LLM-powered summarization, curates personalized digests based on user preferences, and delivers daily email summaries.

## Overview

This project aggregates AI news from multiple sources:
- **YouTube Channels**: Scrapes videos and transcripts from configured channels
- **RSS Feeds**: Monitors OpenAI and Anthropic blog posts
- **Processing**: Converts content to markdown, generates summaries, and creates digests
- **Curation**: Ranks articles by relevance to user profile using LLM
- **Delivery**: Sends personalized daily email digests

## Architecture

```mermaid
graph LR
    A[Sources<br/>YouTube<br/>RSS Feeds] --> B[Scrapers<br/>BaseScraper<br/>Registry Pattern]
    B --> C[(Database<br/>PostgreSQL)]
    C --> D[Processors<br/>Markdown<br/>Transcripts<br/>Digests]
    D --> C
    C --> E[Curator<br/>LLM Ranking]
    E --> F[Email<br/>Personalized Digest]
    F --> G[Delivery<br/>Gmail SMTP]
    
    style A fill:#e1f5ff
    style B fill:#fff4e1
    style C fill:#e8f5e9,stroke:#4caf50,stroke-width:3px
    style D fill:#fff4e1
    style E fill:#f3e5f5
    style F fill:#f3e5f5
    style G fill:#ffe1f5
```

## How It Works

### Pipeline Flow

1. **Scraping** (`app/runner.py`)
   - Runs all registered scrapers
   - Fetches articles/videos from configured sources
   - Saves raw content to database

2. **Processing** (`app/services/process_*.py`)
   - **Anthropic**: Converts HTML articles to markdown
   - **YouTube**: Fetches video transcripts
   - **Digests**: Generates summaries using LLM

3. **Curation** (`app/services/process_curator.py`)
   - Ranks digests by relevance to user profile
   - Uses LLM to score and rank articles

4. **Email Generation** (`app/services/process_email.py`)
   - Creates personalized email digest
   - Selects top N articles
   - Generates introduction and formats content
   - Marks digests as sent to prevent duplicates

5. **Delivery** (`app/services/email.py`)
   - Sends HTML email via Gmail SMTP

### Daily Pipeline

The `run_daily_pipeline()` function orchestrates all steps:
- Ensures database tables exist
- Scrapes all sources
- Processes content (markdown, transcripts)
- Creates digests
- Sends email

## Project Structure

```
app/
├── agent/              # LLM agents for processing
│   ├── base.py        # Base agent class
│   ├── curator_agent.py   # Article ranking
│   ├── digest_agent.py    # Summary generation
│   └── email_agent.py     # Email content generation
├── database/          # Database layer
│   ├── models.py      # SQLAlchemy models
│   ├── repository.py # Data access layer
│   └── connection.py  # DB connection & environment
├── profiles/          # User profile configuration
│   └── user_profile.py
├── scrapers/          # Content scrapers
│   ├── base.py        # Base scraper for RSS feeds
│   ├── anthropic.py   # Anthropic RSS scraper
│   ├── openai.py      # OpenAI RSS scraper
│   └── youtube.py     # YouTube channel scraper
├── services/          # Processing services
│   ├── base.py        # Base process service
│   ├── process_anthropic.py
│   ├── process_youtube.py
│   ├── process_digest.py
│   ├── process_curator.py
│   ├── process_email.py
│   └── email.py       # Email sending
├── daily_runner.py    # Main pipeline orchestrator
└── runner.py          # Scraper registry & execution
```

## Adding New Scrapers

### RSS Feed Scraper (Easiest)

Create a new file in `app/scrapers/`:

```python
from typing import List
from .base import BaseScraper, Article

class MyArticle(Article):
    pass

class MyScraper(BaseScraper):
    @property
    def rss_urls(self) -> List[str]:
        return ["https://example.com/feed.xml"]

    def get_articles(self, hours: int = 24) -> List[MyArticle]:
        return [MyArticle(**a.model_dump()) for a in super().get_articles(hours)]
```

Then register it in `app/runner.py`:

```python
from .scrapers.my_scraper import MyScraper

def _save_my_articles(scraper, repo, hours):
    return _save_rss_articles(scraper, repo, hours, repo.bulk_create_my_articles)

SCRAPER_REGISTRY = [
    # ... existing scrapers
    ("my_source", MyScraper(), _save_my_articles),
]
```

### Custom Scraper

For non-RSS sources, inherit from the base pattern:

```python
class CustomScraper:
    def get_articles(self, hours: int = 24) -> List[Article]:
        # Your custom scraping logic
        pass
```

## Setup

### Prerequisites

- Python 3.11+
- PostgreSQL database
- Google Gemini API key
- Gmail app password (for email sending)
- Webshare proxy credentials (optional, for YouTube transcript fetching)


### UV Environment Quick Reference

**Install UV:**
```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# Or with pip/brew
pip install uv  # or: brew install uv
```

**Core Commands:**

```bash
# Install dependencies (creates .venv/ automatically)
uv sync

# Run Python scripts (no activation needed)
uv run main.py
uv run python -m app.runner

# Add/remove dependencies
uv add package-name          # Adds to pyproject.toml and installs
uv add --dev package-name    # Add dev dependency
uv remove package-name       # Remove dependency

# Update dependencies
uv sync --upgrade            # Update all packages
uv add package-name@latest   # Update specific package

# View installed packages
uv pip list
```


**Optional: Activate Environment (for IDEs)**
```bash
source .venv/bin/activate     # macOS/Linux
.venv\Scripts\activate        # Windows
```

### Installation

1. Clone the repository
2. Install UV
3. Install dependencies:
   ```bash
   uv sync
   ```
   
   This will:
   - Create a virtual environment (`.venv/`)
   - Install Python 3.11+ if needed
   - Install all dependencies from `pyproject.toml`

3. Configure environment variables (copy `app/example.env` to `.env`):
   ```bash
   GEMINI_API_KEY=your_key
   MY_EMAIL=your_email@gmail.com
   APP_PASSWORD=your_gmail_app_password
   DATABASE_URL=postgresql://user:pass@host:port/db
   ENVIRONMENT=LOCAL  # Optional: auto-detected from DATABASE_URL if contains cloud provider domains
   
   # Optional: Webshare Proxy (for YouTube transcript fetching)
   # Get credentials from https://www.webshare.io/
   WEBSHARE_USERNAME=your_username
   WEBSHARE_PASSWORD=your_password
   ```
   
   **Note**: Webshare proxy is optional. If not provided, YouTube transcript fetching will work without a proxy but may be rate-limited.
   
   **Note**: Get your Gemini API key from [Google AI Studio](https://makersuite.google.com/app/apikey)

4. **Initialize database tables** (REQUIRED before running scrapers):
   ```bash
   uv run python -m app.database.create_tables
   ```
   
   **Important**: The database tables must be created before running scrapers, otherwise you'll get 0 results.
   
   Or check database connection:
   ```bash
   uv run python -m app.database.check_connection
   ```

5. Configure YouTube channels in your `.env` file (see `app/example.env` for format)

6. Update user profile in `app/profiles/user_profile.py`

### Running

**Full pipeline:**
```bash
uv run main.py
```

**Individual steps:**
```bash
# Scraping
uv run python -m app.runner

# Processing
uv run python -m app.services.process_anthropic
uv run python -m app.services.process_youtube
uv run python -m app.services.process_digest

# Curation
uv run python -m app.services.process_curator

# Email
uv run python -m app.services.process_email
```

## Deployment

The project can be deployed to various cloud platforms. See the `deployment/` folder for detailed deployment guides:

- **AWS**: ECS Fargate + EventBridge + RDS (see `deployment/AWS_DEPLOYMENT.md`)
- **Google Cloud**: Cloud Run + Cloud SQL (see `deployment/GCP_DEPLOYMENT.md`)
- **General Cloud**: Step-by-step guide for any cloud provider (see `deployment/GENERAL_CLOUD_DEPLOYMENT.md`)

### Docker

**For local development with database:**

Use Docker Compose to run both the application and PostgreSQL:
```bash
cd deployment
docker-compose up -d
```

**For standalone container:**

Build and run:
```bash
docker build -f deployment/Dockerfile -t ai-frontier .
docker run --env-file .env ai-frontier
```

**Note**: See `deployment/README.md` for details on Docker Compose vs cloud deployments.

## Key Features

- **Modular Architecture**: Base classes make it easy to extend
- **Scraper Registry**: Add new sources with minimal code
- **LLM-Powered**: Uses Google Gemini for summarization and curation
- **Personalized**: User profile-based ranking
- **Duplicate Prevention**: Tracks sent digests
- **Environment Aware**: Supports LOCAL and PRODUCTION environments

## Technology Stack

- **Python 3.11+**: Core language
- **PostgreSQL**: Database
- **SQLAlchemy**: ORM
- **Pydantic**: Data validation
- **Google Gemini API**: LLM processing
- **feedparser**: RSS parsing
- **youtube-transcript-api**: Video transcripts
- **UV**: Package management

## License

MIT
