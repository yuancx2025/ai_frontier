"""
AWS SES email service implementation.
Provides email sending functionality using AWS Simple Email Service (SES).
"""

import os
import logging
from typing import List, Optional
import boto3
from botocore.exceptions import ClientError, BotoCoreError
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# AWS SES Configuration
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
SES_FROM_EMAIL = os.getenv("SES_FROM_EMAIL")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")


def get_ses_client():
    """
    Create and return a boto3 SES client.
    
    Returns:
        boto3.client: SES client instance
        
    Raises:
        ValueError: If AWS credentials are not configured
    """
    try:
        # If credentials are provided via environment variables, use them
        # Otherwise, boto3 will use default credential chain (IAM role, ~/.aws/credentials, etc.)
        if AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY:
            return boto3.client(
                'ses',
                region_name=AWS_REGION,
                aws_access_key_id=AWS_ACCESS_KEY_ID,
                aws_secret_access_key=AWS_SECRET_ACCESS_KEY
            )
        else:
            # Use default credential chain (for Lambda, EC2, etc.)
            return boto3.client('ses', region_name=AWS_REGION)
    except Exception as e:
        logger.error(f"Failed to create SES client: {e}")
        raise ValueError(f"Failed to initialize AWS SES client: {e}")


def send_email(
    subject: str,
    body_text: str,
    body_html: Optional[str] = None,
    recipients: Optional[List[str]] = None,
    from_email: Optional[str] = None
) -> dict:
    """
    Send email using AWS SES API.
    
    Args:
        subject: Email subject line
        body_text: Plain text email body
        body_html: Optional HTML email body
        recipients: List of recipient email addresses
        from_email: Sender email address (defaults to SES_FROM_EMAIL env var)
        
    Returns:
        dict: Response from SES API containing MessageId
        
    Raises:
        ValueError: If required parameters are missing
        ClientError: If SES API call fails
    """
    if not recipients:
        raise ValueError("No recipients provided")
    
    recipients = [r for r in recipients if r is not None]
    if not recipients:
        raise ValueError("No valid recipients provided")
    
    # Use provided from_email or fall back to environment variable
    sender = from_email or SES_FROM_EMAIL
    if not sender:
        raise ValueError(
            "SES_FROM_EMAIL environment variable is not set and no from_email provided. "
            "Please set SES_FROM_EMAIL in your .env file or provide from_email parameter."
        )
    
    # Validate sender email format
    if "@" not in sender or "." not in sender.split("@")[1]:
        raise ValueError(f"Invalid sender email address: {sender}")
    
    # Validate recipient emails
    for recipient in recipients:
        if "@" not in recipient or "." not in recipient.split("@")[1]:
            raise ValueError(f"Invalid recipient email address: {recipient}")
    
    try:
        ses_client = get_ses_client()
        
        # Prepare email destination
        destination = {
            'ToAddresses': recipients
        }
        
        # Prepare message
        message = {
            'Subject': {
                'Data': subject,
                'Charset': 'UTF-8'
            },
            'Body': {
                'Text': {
                    'Data': body_text,
                    'Charset': 'UTF-8'
                }
            }
        }
        
        # Add HTML body if provided
        if body_html:
            message['Body']['Html'] = {
                'Data': body_html,
                'Charset': 'UTF-8'
            }
        
        # Send email
        logger.info(f"Sending email via SES from {sender} to {recipients}")
        response = ses_client.send_email(
            Source=sender,
            Destination=destination,
            Message=message
        )
        
        message_id = response.get('MessageId')
        logger.info(f"Email sent successfully via SES. MessageId: {message_id}")
        
        return {
            'success': True,
            'message_id': message_id,
            'response': response
        }
        
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        error_message = e.response.get('Error', {}).get('Message', str(e))
        
        # Handle common SES errors
        if error_code == 'MessageRejected':
            logger.error(f"SES MessageRejected: {error_message}")
            raise ValueError(
                f"Email rejected by SES: {error_message}. "
                "Make sure the sender email is verified in SES (sandbox mode) "
                "or you have production access."
            )
        elif error_code == 'MailFromDomainNotVerified':
            logger.error(f"SES MailFromDomainNotVerified: {error_message}")
            raise ValueError(
                f"Sender domain not verified: {error_message}. "
                "Please verify your sender email/domain in SES."
            )
        elif error_code == 'ConfigurationSetDoesNotExist':
            logger.error(f"SES ConfigurationSetDoesNotExist: {error_message}")
            raise ValueError(f"SES configuration error: {error_message}")
        else:
            logger.error(f"SES ClientError ({error_code}): {error_message}")
            raise ValueError(f"Failed to send email via SES: {error_message}")
            
    except BotoCoreError as e:
        logger.error(f"AWS BotoCoreError: {e}")
        raise ValueError(f"AWS service error: {str(e)}")
        
    except Exception as e:
        logger.error(f"Unexpected error sending email via SES: {e}")
        raise ValueError(f"Unexpected error: {str(e)}")


def verify_email_address(email: str) -> bool:
    """
    Verify an email address in SES (for sandbox mode).
    
    Args:
        email: Email address to verify
        
    Returns:
        bool: True if verification request was sent successfully
        
    Raises:
        ValueError: If verification fails
    """
    try:
        ses_client = get_ses_client()
        response = ses_client.verify_email_identity(EmailAddress=email)
        logger.info(f"Verification email sent to {email}")
        return True
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        error_message = e.response.get('Error', {}).get('Message', str(e))
        logger.error(f"Failed to verify email {email}: {error_code} - {error_message}")
        raise ValueError(f"Failed to verify email address: {error_message}")
    except Exception as e:
        logger.error(f"Unexpected error verifying email: {e}")
        raise ValueError(f"Unexpected error: {str(e)}")


def get_ses_send_quota() -> dict:
    """
    Get SES sending quota and statistics.
    
    Returns:
        dict: Contains Max24HourSend, MaxSendRate, SentLast24Hours
    """
    try:
        ses_client = get_ses_client()
        response = ses_client.get_send_quota()
        return {
            'max_24_hour_send': response.get('Max24HourSend', 0),
            'max_send_rate': response.get('MaxSendRate', 0),
            'sent_last_24_hours': response.get('SentLast24Hours', 0)
        }
    except Exception as e:
        logger.error(f"Failed to get SES quota: {e}")
        return {}


def check_ses_status() -> dict:
    """
    Check SES account status and configuration.
    
    Returns:
        dict: Status information including sandbox mode, verified emails, etc.
    """
    try:
        ses_client = get_ses_client()
        
        # Get verified email addresses
        verified_emails = ses_client.list_verified_email_addresses()
        
        # Get send quota
        quota = get_ses_send_quota()
        
        # Check if in sandbox mode (sandbox has very low limits)
        is_sandbox = quota.get('max_24_hour_send', 0) < 200
        
        return {
            'is_sandbox_mode': is_sandbox,
            'verified_emails': verified_emails.get('VerifiedEmailAddresses', []),
            'quota': quota,
            'region': AWS_REGION,
            'from_email': SES_FROM_EMAIL
        }
    except Exception as e:
        logger.error(f"Failed to check SES status: {e}")
        return {'error': str(e)}


def send_email_to_self(subject: str, body: str):
    """
    Send email to the configured sender email address.
    
    Args:
        subject: Email subject line
        body: Email body text
        
    Raises:
        ValueError: If SES_FROM_EMAIL is not set
    """
    if not SES_FROM_EMAIL:
        raise ValueError("SES_FROM_EMAIL environment variable is not set. Please set it in your .env file.")
    send_email(subject, body, recipients=[SES_FROM_EMAIL])

