import logging
from dotenv import load_dotenv

load_dotenv()

from app.profiles.user_profile import USER_PROFILE
from app.database.digest_repository import DigestRepository

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


def curate_digests(hours: int = 24) -> dict:
    """
    Display ranked digests that already have relevance scores.
    Note: Digests are now scored during creation (process_digest.py),
    so this function just sorts and displays existing scored digests.
    """
    digests_repo = DigestRepository()
    
    digests = digests_repo.get_recent_digests(hours=hours)
    total = len(digests)
    
    if total == 0:
        logger.warning(f"No digests found from the last {hours} hours")
        return {"total": 0, "ranked": 0}
    
    # Filter and sort digests by relevance score
    scored_digests = [
        d for d in digests 
        if d.get("relevance_score") is not None
    ]
    
    if not scored_digests:
        logger.warning(f"No digests with relevance scores found. Digests are now scored during creation.")
        return {"total": total, "ranked": 0, "message": "No scored digests found. Run process_digests first."}
    
    # Sort by relevance_score descending
    scored_digests.sort(
        key=lambda x: x.get("relevance_score", 0.0) or 0.0,
        reverse=True
    )
    
    logger.info(f"Found {len(scored_digests)} digests with scores (out of {total} total)")
    logger.info(f"User profile: {USER_PROFILE['name']} - {USER_PROFILE['background']}")
    logger.info("\n=== Top 10 Ranked Articles ===")
    
    for idx, digest in enumerate(scored_digests[:10], 1):
        score = digest.get("relevance_score", 0.0) or 0.0
        logger.info(f"\nRank {idx} | Score: {score:.1f}/10.0")
        logger.info(f"Title: {digest['title']}")
        logger.info(f"Type: {digest['article_type']}")
        logger.info(f"Reasoning: {digest.get('reasoning', 'N/A')}")
    
    return {
        "total": total,
        "ranked": len(scored_digests),
        "articles": [
            {
                "digest_id": d["id"],
                "rank": idx + 1,
                "relevance_score": d.get("relevance_score", 0.0) or 0.0,
                "reasoning": d.get("reasoning", "")
            }
            for idx, d in enumerate(scored_digests)
        ]
    }


if __name__ == "__main__":
    result = curate_digests(hours=24)
    print(f"\n=== Curation Results ===")
    print(f"Total digests: {result['total']}")
    print(f"Ranked: {result['ranked']}")

