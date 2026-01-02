"""
Lambda handler for generating digests with relevance scores.
Retrieves database URL from AWS Secrets Manager and processes digests.
"""

import json
import os
import boto3
import logging
from app.services.process_digest import process_digests

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    """
    Lambda handler for digest generation.
    
    Args:
        event: Lambda event (can contain 'hours' parameter)
        context: Lambda context
        
    Returns:
        dict: Status code and digest processing results
    """
    try:
        secrets_client = boto3.client('secretsmanager')
        
        # Retrieve database URL
        try:
            response = secrets_client.get_secret_value(SecretId='ai-frontier/database-url')
            os.environ['DATABASE_URL'] = response['SecretString']
            logger.info("Retrieved database URL from Secrets Manager")
        except Exception as e:
            logger.error(f"Error retrieving database URL: {e}")
            raise
        
        # Set environment
        os.environ['ENVIRONMENT'] = 'PRODUCTION'
        
        # Get hours parameter from event (default 24)
        hours = event.get('hours', 24)
        logger.info(f"Starting digest processing for last {hours} hours")
        
        # Process digests
        result = process_digests(hours=hours)
        
        logger.info(f"Digest processing completed: {result}")
        
        return {
            'statusCode': 200,
            'body': result
        }
    except Exception as e:
        logger.error(f"Error in digest handler: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'body': {'error': str(e)}
        }

