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
    Format meeting data into an attractive HTML email body.
    
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
    start_date = meeting_start.strftime('%B %d, %Y') if meeting_start else 'N/A'
    start_time = meeting_start.strftime('%I:%M %p') if meeting_start else 'N/A'
    end_time = meeting_end.strftime('%I:%M %p') if meeting_end else 'N/A'
    
    # Format total duration
    hours = int(total_duration // 3600)
    minutes = int((total_duration % 3600) // 60)
    seconds = int(total_duration % 60)
    duration_str = f'{hours}h {minutes}m' if hours > 0 else f'{minutes}m {seconds}s'
    
    # Build attractive HTML email
    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background-color: #f5f7fa;
            padding: 20px;
            line-height: 1.6;
        }}
        .container {{
            max-width: 800px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }}
        .header {{
            background: linear-gradient(135deg, #5865F2 0%, #4752C4 100%);
            color: white;
            padding: 40px 30px;
            text-align: center;
        }}
        .header h1 {{
            font-size: 28px;
            font-weight: 600;
            margin-bottom: 8px;
        }}
        .header p {{
            font-size: 16px;
            opacity: 0.9;
        }}
        .summary-cards {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            padding: 30px;
            background: #f8f9fb;
        }}
        .card {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
            border: 1px solid #e3e5e8;
        }}
        .card-value {{
            font-size: 24px;
            font-weight: 700;
            color: #5865F2;
            margin-bottom: 5px;
        }}
        .card-label {{
            font-size: 12px;
            color: #6c757d;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        .content {{
            padding: 30px;
        }}
        .section-title {{
            font-size: 20px;
            font-weight: 600;
            color: #2c3e50;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid #5865F2;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 30px;
            background: white;
            border-radius: 8px;
            overflow: hidden;
        }}
        thead {{
            background: #5865F2;
            color: white;
        }}
        th {{
            padding: 15px;
            text-align: left;
            font-weight: 600;
            font-size: 14px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        td {{
            padding: 15px;
            border-bottom: 1px solid #e3e5e8;
            color: #495057;
        }}
        tbody tr:last-child td {{
            border-bottom: none;
        }}
        tbody tr:hover {{
            background-color: #f8f9fb;
        }}
        .member-info {{
            display: flex;
            flex-direction: column;
        }}
        .member-nickname {{
            font-weight: 600;
            color: #2c3e50;
            font-size: 15px;
        }}
        .member-username {{
            font-size: 13px;
            color: #6c757d;
            margin-top: 2px;
        }}
        .duration-badge {{
            display: inline-block;
            padding: 6px 12px;
            background: #e7f3ff;
            color: #0066cc;
            border-radius: 20px;
            font-weight: 600;
            font-size: 13px;
        }}
        .session-count {{
            display: inline-block;
            padding: 6px 12px;
            background: #f0f0f0;
            color: #495057;
            border-radius: 20px;
            font-weight: 600;
            font-size: 13px;
        }}
        .footer {{
            background: #f8f9fb;
            padding: 20px 30px;
            text-align: center;
            color: #6c757d;
            font-size: 13px;
            border-top: 1px solid #e3e5e8;
        }}
        .footer p {{
            margin: 5px 0;
        }}
        .emoji {{
            font-size: 20px;
            margin-right: 8px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎙️ Voice Meeting Report</h1>
            <p>{start_date}</p>
        </div>
        
        <div class="summary-cards">
            <div class="card">
                <div class="card-value">{start_time}</div>
                <div class="card-label">Start Time</div>
            </div>
            <div class="card">
                <div class="card-value">{end_time}</div>
                <div class="card-label">End Time</div>
            </div>
            <div class="card">
                <div class="card-value">{duration_str}</div>
                <div class="card-label">Duration</div>
            </div>
            <div class="card">
                <div class="card-value">{len(member_summaries)}</div>
                <div class="card-label">Participants</div>
            </div>
        </div>
        
        <div class="content">
"""
    
    # Add member summaries table
    if member_summaries:
        html += """
            <h2 class="section-title">👥 Participant Summary</h2>
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
            member_nickname = member.get('member_nickname', member.get('member_name', 'Unknown'))
            member_username = member.get('member_tag', member.get('member_name', 'Unknown'))
            total_time = member.get('total_time', 0)
            session_count = member.get('session_count', 0)
            
            # Format member total time
            m_hours = int(total_time // 3600)
            m_minutes = int((total_time % 3600) // 60)
            m_seconds = int(total_time % 60)
            time_str = f'{m_hours}h {m_minutes}m' if m_hours > 0 else f'{m_minutes}m {m_seconds}s'
            
            html += f"""
                    <tr>
                        <td>
                            <div class="member-info">
                                <span class="member-nickname">{member_nickname}</span>
                                <span class="member-username">{member_username}</span>
                            </div>
                        </td>
                        <td><span class="duration-badge">{time_str}</span></td>
                        <td><span class="session-count">{session_count}</span></td>
                    </tr>
"""
        
        html += """
                </tbody>
            </table>
"""
    
    # Add detailed sessions table
    if sessions:
        html += """
            <h2 class="section-title">📋 Detailed Session Log</h2>
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
            member_nickname = session.get('member_nickname', session.get('member_name', 'Unknown'))
            member_username = session.get('member_tag', session.get('member_name', 'Unknown'))
            join_time = session.get('join_time')
            leave_time = session.get('leave_time')
            duration = session.get('duration', 0)
            
            join_str = join_time.strftime('%I:%M:%S %p') if join_time else 'N/A'
            leave_str = leave_time.strftime('%I:%M:%S %p') if leave_time else 'N/A'
            
            # Format session duration
            s_minutes = int(duration // 60)
            s_seconds = int(duration % 60)
            duration_str = f'{s_minutes}m {s_seconds}s'
            
            html += f"""
                    <tr>
                        <td>
                            <div class="member-info">
                                <span class="member-nickname">{member_nickname}</span>
                                <span class="member-username">{member_username}</span>
                            </div>
                        </td>
                        <td>{join_str}</td>
                        <td>{leave_str}</td>
                        <td><span class="duration-badge">{duration_str}</span></td>
                    </tr>
"""
        
        html += """
                </tbody>
            </table>
"""
    
    html += """
        </div>
        
        <div class="footer">
            <p>🤖 Automatically generated by Discord Voice Tracker Bot</p>
            <p>Tracking voice channel activity with precision</p>
        </div>
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

