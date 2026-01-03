import logging
from datetime import datetime
from dotenv import load_dotenv

from app.runner import run_scrapers
from app.services.process_digest import process_digests, process_digests_for_user
from app.services.process_email import send_digest_email, send_digest_email_for_user
from app.database.models import Base
from app.database.connection import engine
from app.database.user_repository import UserRepository, user_to_profile_dict

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
        "emails": {},  # Changed to plural - will track per user
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
        # Get all active users for personalized digest generation
        user_repo = UserRepository()
        active_users = user_repo.get_all_active_users()
        
        if not active_users:
            logger.warning("No active users found. Skipping digest generation.")
            results["digests"] = {"processed": 0, "total": 0, "failed": 0}
        else:
            # Process digests for each user with their personalized profile
            total_processed = 0
            total_failed = 0
            
            logger.info(f"Processing digests for {len(active_users)} active user(s)...")
            for user in active_users:
                user_profile = user_to_profile_dict(user)
                logger.info(f"  → Processing digests for user: {user.email} ({user.name})")
                
                try:
                    digest_result = process_digests_for_user(
                        hours=hours, 
                        user_profile=user_profile
                    )
                    total_processed += digest_result.get('processed', 0)
                    total_failed += digest_result.get('failed', 0)
                    logger.info(
                        f"    ✓ User {user.email}: {digest_result.get('processed', 0)} processed, "
                        f"{digest_result.get('failed', 0)} failed"
                    )
                except Exception as e:
                    logger.error(f"    ✗ Error processing digests for {user.email}: {e}", exc_info=True)
                    total_failed += 1
            
            results["digests"] = {
                "processed": total_processed,
                "total": total_processed + total_failed,
                "failed": total_failed,
                "users_processed": len(active_users)
            }
            logger.info(
                f"✓ Created {total_processed} digests with relevance scores "
                f"({total_failed} failed out of {total_processed + total_failed} total) "
                f"across {len(active_users)} user(s)"
            )

        logger.info("\n[3/3] Generating and sending email digests...")
        # Send personalized emails to all active users
        user_repo = UserRepository()
        active_users = user_repo.get_all_active_users()
        
        if not active_users:
            logger.warning("No active users found. Skipping email sending.")
            results["emails"] = {"sent": 0, "skipped": 0, "failed": 0, "details": []}
        else:
            email_results = []
            logger.info(f"Sending personalized emails to {len(active_users)} active user(s)...")
            
            for user in active_users:
                user_profile = user_to_profile_dict(user)
                logger.info(f"  → Sending digest email to: {user.email} ({user.name})")
                
                try:
                    email_result = send_digest_email_for_user(
                        hours=hours,
                        top_n=top_n,
                        user_email=user.email,
                        user_profile=user_profile
                    )
                    email_results.append({
                        "user": user.email,
                        "user_name": user.name,
                        "result": email_result
                    })
                    
                    if email_result.get("skipped"):
                        logger.info(f"    ✓ Skipped: {email_result.get('message', 'No new digests')}")
                    elif email_result.get("success"):
                        logger.info(
                            f"    ✓ Email sent successfully with {email_result.get('articles_count', 0)} articles"
                        )
                    else:
                        logger.error(
                            f"    ✗ Failed to send email: {email_result.get('error', 'Unknown error')}"
                        )
                except Exception as e:
                    logger.error(f"    ✗ Error sending email to {user.email}: {e}", exc_info=True)
                    email_results.append({
                        "user": user.email,
                        "user_name": user.name,
                        "result": {"success": False, "error": str(e)}
                    })
            
            # Aggregate email results
            sent_count = sum(1 for r in email_results if r["result"].get("success") and not r["result"].get("skipped"))
            failed_count = sum(1 for r in email_results if not r["result"].get("success"))
            skipped_count = sum(1 for r in email_results if r["result"].get("skipped"))
            
            results["emails"] = {
                "sent": sent_count,
                "failed": failed_count,
                "skipped": skipped_count,
                "details": email_results
            }
            
            logger.info(
                f"✓ Email summary: {sent_count} sent, {skipped_count} skipped, {failed_count} failed "
                f"across {len(active_users)} user(s)"
            )
            
            # Success if at least one email was sent or skipped (no new digests is OK)
            results["success"] = sent_count > 0 or skipped_count > 0

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
    
    # Determine email status
    emails_info = results.get("emails", {})
    if emails_info.get("sent", 0) > 0:
        email_status = f"Sent ({emails_info['sent']})"
        if emails_info.get("skipped", 0) > 0:
            email_status += f", Skipped ({emails_info['skipped']})"
        if emails_info.get("failed", 0) > 0:
            email_status += f", Failed ({emails_info['failed']})"
    elif emails_info.get("skipped", 0) > 0:
        email_status = f"Skipped ({emails_info['skipped']})"
        if emails_info.get("failed", 0) > 0:
            email_status += f", Failed ({emails_info['failed']})"
    elif emails_info.get("failed", 0) > 0:
        email_status = f"Failed ({emails_info['failed']})"
    else:
        email_status = "No users"
    logger.info(f"Emails: {email_status}")
    logger.info("=" * 60)

    return results


if __name__ == "__main__":
    result = run_daily_pipeline(hours=24*7, top_n=10)
    exit(0 if result["success"] else 1)
