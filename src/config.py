"""
Configuration module that loads and validates environment variables.
Exits with error code 1 if required configuration is missing.
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Define required configuration keys
REQUIRED_CONFIG = [
    'DISCORD_TOKEN',
    'VOICE_CHANNEL_ID',
    'SMTP_HOST',
    'SMTP_PORT',
    'SMTP_USER',
    'SMTP_PASS',
    'EMAIL_TO',
    'EMAIL_FROM'
]

def validate_config():
    """Validate that all required environment variables are present."""
    missing = [key for key in REQUIRED_CONFIG if not os.getenv(key)]
    
    if missing:
        print('ERROR: Missing required configuration:', file=sys.stderr)
        for key in missing:
            print(f'  - {key}', file=sys.stderr)
        print('\nPlease ensure all required environment variables are set in your .env file', 
              file=sys.stderr)
        sys.exit(1)

# Validate configuration on module import (skip if in test mode)
if not os.getenv('TESTING'):
    validate_config()

# Discord configuration
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
VOICE_CHANNEL_ID = int(os.getenv('VOICE_CHANNEL_ID')) if os.getenv('VOICE_CHANNEL_ID') else 0

# Email configuration
SMTP_HOST = os.getenv('SMTP_HOST')
SMTP_PORT = int(os.getenv('SMTP_PORT')) if os.getenv('SMTP_PORT') else 0
SMTP_USER = os.getenv('SMTP_USER')
SMTP_PASS = os.getenv('SMTP_PASS')
EMAIL_FROM = os.getenv('EMAIL_FROM')
EMAIL_TO = os.getenv('EMAIL_TO')

# Meeting configuration
MEETING_END_TIMEOUT = int(os.getenv('MEETING_END_TIMEOUT', '300'))  # Default 5 minutes (in seconds)
