"""
Email service module that handles meeting report generation and sending.
Formats meeting data into HTML emails and sends via SMTP with retry logic.
"""

import smtplib
import asyncio
import json
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Dict
from src.logger import logger
from src.config import (
    SMTP_HOST,
    SMTP_PORT,
    SMTP_USER,
    SMTP_PASS,
    EMAIL_FROM,
    EMAIL_TO
)


def format_email_body(meeting_data: Dict) -> str:
    """
    Format meeting data into an HTML email body.
    
    Args:
        meeting_data: Dictionary containing meeting report data
        
    Returns:
        HTML string for email body
    """
    meeting_start = meeting_data.get('meeting_start_time')
    meeting_end = meeting_data.get('meeting_end_time')
    total_duration = meeting_data.get('total_duration', 0)
    sessions = meeting_data.get('sessions', [])
    member_summaries = meeting_data.get('member_summaries', [])
    
    # Format timestamps
    start_str = meeting_start.strftime('%Y-%m-%d %H:%M:%S') if meeting_start else 'N/A'
    end_str = meeting_end.strftime('%Y-%m-%d %H:%M:%S') if meeting_end else 'N/A'
    
    # Format total duration
    hours = int(total_duration // 3600)
    minutes = int((total_duration % 3600) // 60)
    seconds = int(total_duration % 60)
    duration_str = f'{hours}h {minutes}m {seconds}s' if hours > 0 else f'{minutes}m {seconds}s'
    
    # Build HTML email
    html = f"""
    <html>
    <head>
        <style>
            body {{
                font-family: Arial, sans-serif;
                line-height: 1.6;
                color: #333;
            }}
            .header {{
                background-color: #5865F2;
                color: white;
                padding: 20px;
                border-radius: 5px;
            }}
            .summary {{
                background-color: #f4f4f4;
                padding: 15px;
                margin: 20px 0;
                border-radius: 5px;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin: 20px 0;
            }}
            th {{
                background-color: #5865F2;
                color: white;
                padding: 12px;
                text-align: left;
            }}
            td {{
                padding: 10px;
                border-bottom: 1px solid #ddd;
            }}
            tr:hover {{
                background-color: #f5f5f5;
            }}
            .footer {{
                margin-top: 30px;
                padding-top: 20px;
                border-top: 1px solid #ddd;
                color: #666;
                font-size: 12px;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>Discord Voice Channel Meeting Report</h1>
        </div>
        
        <div class="summary">
            <h2>Meeting Summary</h2>
            <p><strong>Start Time:</strong> {start_str}</p>
            <p><strong>End Time:</strong> {end_str}</p>
            <p><strong>Total Duration:</strong> {duration_str}</p>
            <p><strong>Total Participants:</strong> {len(member_summaries)}</p>
            <p><strong>Total Sessions:</strong> {len(sessions)}</p>
        </div>
"""
    
    # Add member summaries table
    if member_summaries:
        html += """
        <h2>Participant Summary</h2>
        <table>
            <thead>
                <tr>
                    <th>Member</th>
                    <th>Total Time</th>
                    <th>Sessions</th>
                </tr>
            </thead>
            <tbody>
"""
        
        for member in member_summaries:
            member_name = member.get('member_name', 'Unknown')
            total_time = member.get('total_time', 0)
            session_count = member.get('session_count', 0)
            
            # Format member total time
            m_hours = int(total_time // 3600)
            m_minutes = int((total_time % 3600) // 60)
            m_seconds = int(total_time % 60)
            time_str = f'{m_hours}h {m_minutes}m {m_seconds}s' if m_hours > 0 else f'{m_minutes}m {m_seconds}s'
            
            html += f"""
                <tr>
                    <td>{member_name}</td>
                    <td>{time_str}</td>
                    <td>{session_count}</td>
                </tr>
"""
        
        html += """
            </tbody>
        </table>
"""
    
    # Add detailed sessions table
    if sessions:
        html += """
        <h2>Detailed Session Log</h2>
        <table>
            <thead>
                <tr>
                    <th>Member</th>
                    <th>Join Time</th>
                    <th>Leave Time</th>
                    <th>Duration</th>
                </tr>
            </thead>
            <tbody>
"""
        
        for session in sessions:
            member_name = session.get('member_name', 'Unknown')
            join_time = session.get('join_time')
            leave_time = session.get('leave_time')
            duration = session.get('duration', 0)
            
            join_str = join_time.strftime('%H:%M:%S') if join_time else 'N/A'
            leave_str = leave_time.strftime('%H:%M:%S') if leave_time else 'N/A'
            
            # Format session duration
            s_minutes = int(duration // 60)
            s_seconds = int(duration % 60)
            duration_str = f'{s_minutes}m {s_seconds}s'
            
            html += f"""
                <tr>
                    <td>{member_name}</td>
                    <td>{join_str}</td>
                    <td>{leave_str}</td>
                    <td>{duration_str}</td>
                </tr>
"""
        
        html += """
            </tbody>
        </table>
"""
    
    html += """
        <div class="footer">
            <p>This report was automatically generated by Discord Voice Tracker Bot.</p>
        </div>
    </body>
    </html>
"""
    
    return html


async def send_meeting_report(meeting_data: Dict) -> bool:
    """
    Send meeting report via email with retry logic.
    
    Args:
        meeting_data: Dictionary containing meeting report data
        
    Returns:
        True if email sent successfully, False otherwise
    """
    logger.info('Preparing to send meeting report via email')
    
    # Format email content
    html_body = format_email_body(meeting_data)
    
    # Create email message
    message = MIMEMultipart('alternative')
    message['Subject'] = f'Meeting Report - {meeting_data.get("meeting_start_time", datetime.now()).strftime("%Y-%m-%d %H:%M")}'
    message['From'] = EMAIL_FROM
    message['To'] = EMAIL_TO
    
    # Attach HTML body
    html_part = MIMEText(html_body, 'html')
    message.attach(html_part)
    
    # Send with retry logic
    success = await send_email_with_retry(message, max_retries=3)
    
    if not success:
        # Save to file as fallback
        await save_report_to_file(meeting_data)
    
    return success


async def send_email_with_retry(message: MIMEMultipart, max_retries: int = 3) -> bool:
    """
    Send email with retry logic using asyncio delays.
    
    Args:
        message: MIMEMultipart email message to send
        max_retries: Maximum number of retry attempts (default: 3)
        
    Returns:
        True if email sent successfully, False otherwise
    """
    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f'Attempting to send email (attempt {attempt}/{max_retries})')
            
            # Connect to SMTP server
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
                server.starttls()  # Enable TLS encryption
                server.login(SMTP_USER, SMTP_PASS)
                server.send_message(message)
            
            logger.info('Email sent successfully')
            return True
            
        except smtplib.SMTPAuthenticationError as e:
            logger.error(f'SMTP authentication failed: {e}')
            # Don't retry on authentication errors
            return False
            
        except smtplib.SMTPException as e:
            logger.error(f'SMTP error on attempt {attempt}: {e}')
            
        except Exception as e:
            logger.error(f'Unexpected error sending email on attempt {attempt}: {e}')
        
        # Wait before retry (except on last attempt)
        if attempt < max_retries:
            logger.info(f'Waiting 30 seconds before retry...')
            await asyncio.sleep(30)
    
    logger.error(f'Failed to send email after {max_retries} attempts')
    return False


async def save_report_to_file(meeting_data: Dict) -> None:
    """
    Save meeting report to a JSON file as fallback when email fails.
    
    Args:
        meeting_data: Dictionary containing meeting report data
    """
    # Create reports directory if it doesn't exist
    reports_dir = 'reports'
    os.makedirs(reports_dir, exist_ok=True)
    
    # Generate filename with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = os.path.join(reports_dir, f'meeting-{timestamp}.json')
    
    # Convert datetime objects to strings for JSON serialization
    serializable_data = _make_serializable(meeting_data)
    
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(serializable_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f'Meeting report saved to file: {filename}')
        
    except Exception as e:
        logger.error(f'Failed to save report to file: {e}')


def _make_serializable(data):
    """
    Convert datetime objects to ISO format strings for JSON serialization.
    
    Args:
        data: Data structure that may contain datetime objects
        
    Returns:
        Data structure with datetime objects converted to strings
    """
    if isinstance(data, datetime):
        return data.isoformat()
    elif isinstance(data, dict):
        return {key: _make_serializable(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [_make_serializable(item) for item in data]
    else:
        return data

