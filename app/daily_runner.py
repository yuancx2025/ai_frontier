import logging
from datetime import datetime
from dotenv import load_dotenv

from app.runner import run_scrapers
from app.services.process_digest import process_digests
from app.services.process_email import send_digest_email
from app.database.models import Base
from app.database.connection import engine

load_dotenv()


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def run_daily_pipeline(hours: int = 24, top_n: int = 10) -> dict:
    start_time = datetime.now()
    logger.info("=" * 60)
    logger.info("Starting Daily AI News Aggregator Pipeline")
    logger.info("=" * 60)

    results = {
        "start_time": start_time.isoformat(),
        "scraping": {},
        "digests": {},
        "email": {},
        "success": False,
    }

    try:
        logger.info("\n[0/3] Ensuring database tables exist...")
        try:
            with engine.connect() as conn:
                Base.metadata.create_all(engine)
                logger.info("✓ Database tables verified/created")
        except Exception as e:
            logger.error(f"Failed to create database tables: {e}")
            raise

        logger.info("\n[1/3] Scraping articles from sources...")
        scraping_results = run_scrapers(hours=hours)
        results["scraping"] = scraping_results.get_summary()
        logger.info(
            f"✓ Scraped {scraping_results.youtube.count} YouTube videos, "
            f"{scraping_results.openai.count} OpenAI articles, "
            f"{scraping_results.anthropic.count} Anthropic articles, "
            f"{scraping_results.cursor.count} Cursor articles, "
            f"{scraping_results.windsurf.count} Windsurf articles, "
            f"{scraping_results.deepmind.count} DeepMind articles, "
            f"{scraping_results.xai.count} XAI articles, "
            f"{scraping_results.nvdia.count} NVIDIA articles"
        )

        logger.info("\n[2/3] Creating digests with relevance scores for articles...")
        digest_result = process_digests(hours=hours)
        results["digests"] = digest_result
        logger.info(
            f"✓ Created {digest_result['processed']} digests with relevance scores "
            f"({digest_result['failed']} failed out of {digest_result['total']} total)"
        )

        logger.info("\n[3/3] Generating and sending email digest...")
        email_result = send_digest_email(hours=hours, top_n=top_n)
        results["email"] = email_result

        if email_result.get("skipped"):
            logger.info(f"✓ {email_result.get('message', 'No new digests to send')}")
            results["success"] = True
        elif email_result["success"]:
            logger.info(
                f"✓ Email sent successfully with {email_result['articles_count']} articles"
            )
            results["success"] = True
        else:
            logger.error(
                f"✗ Failed to send email: {email_result.get('error', 'Unknown error')}"
            )

    except Exception as e:
        logger.error(f"Pipeline failed with error: {e}", exc_info=True)
        results["error"] = str(e)

    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    results["end_time"] = end_time.isoformat()
    results["duration_seconds"] = duration

    logger.info("\n" + "=" * 60)
    logger.info("Pipeline Summary")
    logger.info("=" * 60)
    logger.info(f"Duration: {duration:.1f} seconds")
    logger.info(f"Scraped: {results['scraping']}")
    logger.info(f"Digests: {results['digests']}")
    if results.get("email", {}).get("skipped"):
        email_status = "Skipped"
    elif results["success"]:
        email_status = "Sent"
    else:
        email_status = "Failed"
    logger.info(f"Email: {email_status}")
    logger.info("=" * 60)

    return results


if __name__ == "__main__":
    result = run_daily_pipeline(hours=24*7, top_n=10)
    exit(0 if result["success"] else 1)
