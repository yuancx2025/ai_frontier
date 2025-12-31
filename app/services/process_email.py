import logging
from dotenv import load_dotenv

load_dotenv()

from app.agent.email_agent import EmailAgent, RankedArticleDetail, EmailDigestResponse
from app.profiles.user_profile import USER_PROFILE
from app.database.digest_repository import DigestRepository
from app.services.email import send_email, digest_to_html

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def generate_email_digest(hours: int = 24, top_n: int = 10) -> EmailDigestResponse:
    """
    Generate email digest from digests that already have relevance scores.
    Digests are sorted by relevance_score (descending) and top N are selected.
    """
    email_agent = EmailAgent(USER_PROFILE)
    digests_repo = DigestRepository()

    digests = digests_repo.get_recent_digests(hours=hours)
    total = len(digests)

    if total == 0:
        raise ValueError("No digests available")

    # Filter out digests without relevance scores and sort by score (descending)
    scored_digests = [
        d for d in digests 
        if d.get("relevance_score") is not None
    ]
    
    if not scored_digests:
        logger.warning("No digests with relevance scores found. All digests will be included.")
        scored_digests = digests
    
    # Sort by relevance_score descending, then by created_at descending
    scored_digests.sort(
        key=lambda x: (
            x.get("relevance_score", 0.0) if x.get("relevance_score") is not None else 0.0,
            x.get("created_at", "").isoformat() if x.get("created_at") else ""
        ),
        reverse=True
    )

    logger.info(f"Found {len(scored_digests)} digests with scores (out of {total} total)")
    logger.info(f"Generating email digest with top {top_n} articles")

    # Create ranked article details with rank based on sorted position
    article_details = [
        RankedArticleDetail(
            digest_id=d["id"],
            rank=idx + 1,
            relevance_score=d.get("relevance_score", 0.0) or 0.0,
            reasoning=d.get("reasoning", ""),
            title=d["title"],
            summary=d["summary"],
            url=d["url"],
            article_type=d["article_type"],
        )
        for idx, d in enumerate(scored_digests)
    ]

    email_digest = email_agent.create_email_digest_response(
        ranked_articles=article_details, total_ranked=len(scored_digests), limit=top_n
    )

    logger.info("Email digest generated successfully")
    logger.info("\n=== Email Introduction ===")
    logger.info(email_digest.introduction.greeting)
    logger.info(f"\n{email_digest.introduction.introduction}")

    return email_digest


def send_digest_email(hours: int = 24, top_n: int = 10) -> dict:
    digests_repo = DigestRepository()
    digests = digests_repo.get_recent_digests(hours=hours)

    if len(digests) == 0:
        logger.info("No new digests to send. Nothing to send.")
        return {
            "success": True,
            "skipped": True,
            "message": "No new digests available",
            "articles_count": 0,
        }

    try:
        result = generate_email_digest(hours=hours, top_n=top_n)
        markdown_content = result.to_markdown()
        html_content = digest_to_html(result)

        subject = f"Daily AI News Digest - {result.introduction.greeting.split('for ')[-1] if 'for ' in result.introduction.greeting else 'Today'}"

        send_email(subject=subject, body_text=markdown_content, body_html=html_content)

        digest_ids = [article.digest_id for article in result.articles]
        marked_count = digests_repo.mark_digests_as_sent(digest_ids)

        logger.info(f"Email sent successfully! Marked {marked_count} digests as sent.")
        return {
            "success": True,
            "subject": subject,
            "articles_count": len(result.articles),
            "marked_as_sent": marked_count,
        }
    except ValueError as e:
        logger.error(f"Error sending email: {e}")
        return {"success": False, "error": str(e)}


if __name__ == "__main__":
    result = send_digest_email(hours=24, top_n=10)
    if result["success"]:
        print("\n=== Email Digest Sent ===")
        print(f"Subject: {result['subject']}")
        print(f"Articles: {result['articles_count']}")
    else:
        print(f"Error: {result['error']}")
