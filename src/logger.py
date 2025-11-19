"""
Logging module that provides structured logging with console and file handlers.
Logs include timestamps and context for debugging and monitoring.
"""

import logging
import os
from datetime import datetime

# Create logs directory if it doesn't exist
LOGS_DIR = 'logs'
os.makedirs(LOGS_DIR, exist_ok=True)

# Generate log filename with timestamp
log_filename = os.path.join(LOGS_DIR, f'discord_bot_{datetime.now().strftime("%Y%m%d")}.log')

# Create logger
logger = logging.getLogger('discord_voice_tracker')
logger.setLevel(logging.DEBUG)

# Prevent duplicate handlers if module is imported multiple times
if not logger.handlers:
    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    console_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # Console handler (INFO and above)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_formatter)
    
    # File handler (DEBUG and above)
    file_handler = logging.FileHandler(log_filename, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(detailed_formatter)
    
    # Add handlers to logger
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

# Export logger instance
__all__ = ['logger']
