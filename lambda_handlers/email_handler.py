"""
Lambda handler for sending email digests.
Retrieves secrets from AWS Secrets Manager and sends personalized emails.
"""

import json
import os
import boto3
import logging
from app.services.process_email import send_digest_email

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    """
    Lambda handler for email sending.
    
    Args:
        event: Lambda event (can contain 'hours' and 'top_n' parameters)
        context: Lambda context
        
    Returns:
        dict: Status code and email sending results
    """
    try:
        secrets_client = boto3.client('secretsmanager')
        
        # Retrieve secrets
        try:
            db_response = secrets_client.get_secret_value(SecretId='ai-frontier/database-url')
            os.environ['DATABASE_URL'] = db_response['SecretString']
            logger.info("Retrieved database URL from Secrets Manager")
        except Exception as e:
            logger.error(f"Error retrieving database URL: {e}")
            raise
        
        try:
            ses_response = secrets_client.get_secret_value(SecretId='ai-frontier/ses-from-email')
            os.environ['SES_FROM_EMAIL'] = ses_response['SecretString']
            logger.info("Retrieved SES from email from Secrets Manager")
        except Exception as e:
            logger.warning(f"Error retrieving SES from email: {e}")
            # SES_FROM_EMAIL might be optional if using IAM role
        
        # Set AWS region and environment
        os.environ['AWS_REGION'] = os.environ.get('AWS_REGION', 'us-east-1')
        os.environ['ENVIRONMENT'] = 'PRODUCTION'
        
        # Get parameters from event
        hours = event.get('hours', 24)
        top_n = event.get('top_n', 10)
        logger.info(f"Starting email sending for last {hours} hours, top {top_n} articles")
        
        # Send email digest
        result = send_digest_email(hours=hours, top_n=top_n)
        
        logger.info(f"Email sending completed: {result}")
        
        return {
            'statusCode': 200,
            'body': result
        }
    except Exception as e:
        logger.error(f"Error in email handler: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'body': {'error': str(e)}
        }

