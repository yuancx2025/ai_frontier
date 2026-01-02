"""
Lambda handler for scraping content from RSS feeds and YouTube.
Retrieves secrets from AWS Secrets Manager and calls the scraper.
"""

import json
import os
import boto3
import logging
from app.runner import run_scrapers

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    """
    Lambda handler for scraping content.
    
    Args:
        event: Lambda event (can contain 'hours' parameter)
        context: Lambda context
        
    Returns:
        dict: Status code and scraping results
    """
    try:
        secrets_client = boto3.client('secretsmanager')
        
        # Retrieve secrets and set as environment variables
        secrets_to_retrieve = {
            'gemini-api-key': 'GEMINI_API_KEY',
            'youtube-api-key': 'YOUTUBE_API_KEY',
            'database-url': 'DATABASE_URL'
        }
        
        for secret_name, env_key in secrets_to_retrieve.items():
            try:
                response = secrets_client.get_secret_value(SecretId=f'ai-frontier/{secret_name}')
                os.environ[env_key] = response['SecretString']
                logger.info(f"Retrieved secret: {secret_name}")
            except secrets_client.exceptions.ResourceNotFoundException:
                logger.warning(f"Secret {secret_name} not found, skipping")
            except Exception as e:
                logger.error(f"Error retrieving secret {secret_name}: {e}")
                # Continue execution - some secrets might be optional
        
        # Set AWS region and environment
        os.environ['AWS_REGION'] = os.environ.get('AWS_REGION', 'us-east-1')
        os.environ['ENVIRONMENT'] = 'PRODUCTION'
        
        # Get hours parameter from event (default 24)
        hours = event.get('hours', 24)
        logger.info(f"Starting scraper for last {hours} hours")
        
        # Run scraper
        results = run_scrapers(hours=hours)
        summary = results.get_summary()
        
        logger.info(f"Scraping completed: {summary}")
        
        return {
            'statusCode': 200,
            'body': summary
        }
    except Exception as e:
        logger.error(f"Error in scrape handler: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'body': {'error': str(e)}
        }

