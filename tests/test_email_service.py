"""
Test suite for email service module.
Tests email formatting with sample data, retry logic with mock SMTP failures,
and file saving fallback.
"""

import os
# Set TESTING environment variable before importing modules
os.environ['TESTING'] = '1'

import asyncio
import pytest
import json
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
from email.mime.multipart import MIMEMultipart
import smtplib

from src.email_service import (
    format_email_body,
    send_meeting_report,
    send_email_with_retry,
    save_report_to_file
)


class TestEmailFormatting:
    """Test suite for email formatting functionality."""
    
    def test_format_email_with_complete_data(self):
        """Test email formatting with complete meeting data."""
        meeting_data = {
            'meeting_start_time': datetime(2024, 11, 19, 10, 0, 0),
            'meeting_end_time': datetime(2024, 11, 19, 11, 30, 0),
            'total_duration': 5400,  # 1.5 hours
            'sessions': [
                {
                    'member_id': '123',
                    'member_name': 'TestUser1',
                    'join_time': datetime(2024, 11, 19, 10, 0, 0),
                    'leave_time': datetime(2024, 11, 19, 10, 30, 0),
                    'duration': 1800
                },
                {
                    'member_id': '456',
                    'member_name': 'TestUser2',
                    'join_time': datetime(2024, 11, 19, 10, 15, 0),
                    'leave_time': datetime(2024, 11, 19, 11, 30, 0),
                    'duration': 4500
                }
            ],
            'member_summaries': [
                {
                    'member_id': '123',
                    'member_name': 'TestUser1',
                    'total_time': 1800,
                    'session_count': 1
                },
                {
                    'member_id': '456',
                    'member_name': 'TestUser2',
                    'total_time': 4500,
                    'session_count': 1
                }
            ]
        }
        
        html = format_email_body(meeting_data)
        
        # Verify HTML structure
        assert '<html>' in html
        assert '</html>' in html
        assert 'Discord Voice Channel Meeting Report' in html
        
        # Verify meeting summary data
        assert '2024-11-19 10:00:00' in html
        assert '2024-11-19 11:30:00' in html
        assert '1h 30m 0s' in html
        assert 'Total Participants:</strong> 2' in html
        assert 'Total Sessions:</strong> 2' in html
        
        # Verify member summaries
        assert 'TestUser1' in html
        assert 'TestUser2' in html
        assert '30m 0s' in html  # TestUser1 duration
        assert '1h 15m 0s' in html  # TestUser2 duration
        
        # Verify session details
        assert '10:00:00' in html
        assert '10:30:00' in html
        assert '11:30:00' in html

    
    def test_format_email_with_empty_sessions(self):
        """Test email formatting with no sessions."""
        meeting_data = {
            'meeting_start_time': datetime(2024, 11, 19, 10, 0, 0),
            'meeting_end_time': datetime(2024, 11, 19, 10, 5, 0),
            'total_duration': 300,
            'sessions': [],
            'member_summaries': []
        }
        
        html = format_email_body(meeting_data)
        
        assert '<html>' in html
        assert 'Discord Voice Channel Meeting Report' in html
        assert 'Total Participants:</strong> 0' in html
        assert 'Total Sessions:</strong> 0' in html
    
    def test_format_email_with_multiple_sessions_same_member(self):
        """Test email formatting with multiple sessions from same member."""
        meeting_data = {
            'meeting_start_time': datetime(2024, 11, 19, 10, 0, 0),
            'meeting_end_time': datetime(2024, 11, 19, 11, 0, 0),
            'total_duration': 3600,
            'sessions': [
                {
                    'member_id': '123',
                    'member_name': 'TestUser',
                    'join_time': datetime(2024, 11, 19, 10, 0, 0),
                    'leave_time': datetime(2024, 11, 19, 10, 20, 0),
                    'duration': 1200
                },
                {
                    'member_id': '123',
                    'member_name': 'TestUser',
                    'join_time': datetime(2024, 11, 19, 10, 30, 0),
                    'leave_time': datetime(2024, 11, 19, 11, 0, 0),
                    'duration': 1800
                }
            ],
            'member_summaries': [
                {
                    'member_id': '123',
                    'member_name': 'TestUser',
                    'total_time': 3000,
                    'session_count': 2
                }
            ]
        }
        
        html = format_email_body(meeting_data)
        
        assert 'TestUser' in html
        assert 'Total Participants:</strong> 1' in html
        assert 'Total Sessions:</strong> 2' in html
        # Member summary should show 2 sessions
        assert '<td>2</td>' in html
    
    def test_format_email_duration_formatting(self):
        """Test that durations are formatted correctly."""
        meeting_data = {
            'meeting_start_time': datetime(2024, 11, 19, 10, 0, 0),
            'meeting_end_time': datetime(2024, 11, 19, 10, 0, 45),
            'total_duration': 45,  # 45 seconds
            'sessions': [
                {
                    'member_id': '123',
                    'member_name': 'TestUser',
                    'join_time': datetime(2024, 11, 19, 10, 0, 0),
                    'leave_time': datetime(2024, 11, 19, 10, 0, 45),
                    'duration': 45
                }
            ],
            'member_summaries': [
                {
                    'member_id': '123',
                    'member_name': 'TestUser',
                    'total_time': 45,
                    'session_count': 1
                }
            ]
        }
        
        html = format_email_body(meeting_data)
        
        # Should show minutes and seconds (no hours for short duration)
        assert '0m 45s' in html


class TestEmailRetryLogic:
    """Test suite for email retry logic with mock SMTP failures."""
    
    @pytest.mark.asyncio
    async def test_send_email_success_first_attempt(self):
        """Test successful email send on first attempt."""
        message = MIMEMultipart()
        message['Subject'] = 'Test'
        message['From'] = 'test@example.com'
        message['To'] = 'recipient@example.com'
        
        with patch('smtplib.SMTP') as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value.__enter__.return_value = mock_server
            
            result = await send_email_with_retry(message, max_retries=3)
            
            assert result is True
            assert mock_smtp.call_count == 1
            mock_server.starttls.assert_called_once()
            mock_server.login.assert_called_once()
            mock_server.send_message.assert_called_once_with(message)
    
    @pytest.mark.asyncio
    async def test_send_email_retry_on_smtp_exception(self):
        """Test retry logic when SMTP exception occurs."""
        message = MIMEMultipart()
        message['Subject'] = 'Test'
        
        with patch('smtplib.SMTP') as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value.__enter__.return_value = mock_server
            
            # First two attempts fail, third succeeds
            mock_server.send_message.side_effect = [
                smtplib.SMTPException('Connection error'),
                smtplib.SMTPException('Timeout'),
                None  # Success
            ]
            
            with patch('asyncio.sleep', return_value=None):  # Speed up test
                result = await send_email_with_retry(message, max_retries=3)
            
            assert result is True
            assert mock_smtp.call_count == 3
    
    @pytest.mark.asyncio
    async def test_send_email_fails_after_max_retries(self):
        """Test that email sending fails after max retries."""
        message = MIMEMultipart()
        message['Subject'] = 'Test'
        
        with patch('smtplib.SMTP') as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value.__enter__.return_value = mock_server
            
            # All attempts fail
            mock_server.send_message.side_effect = smtplib.SMTPException('Connection error')
            
            with patch('asyncio.sleep', return_value=None):  # Speed up test
                result = await send_email_with_retry(message, max_retries=3)
            
            assert result is False
            assert mock_smtp.call_count == 3
    
    @pytest.mark.asyncio
    async def test_send_email_no_retry_on_auth_error(self):
        """Test that authentication errors don't trigger retries."""
        message = MIMEMultipart()
        message['Subject'] = 'Test'
        
        with patch('smtplib.SMTP') as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value.__enter__.return_value = mock_server
            
            # Authentication error on first attempt
            mock_server.login.side_effect = smtplib.SMTPAuthenticationError(535, 'Invalid credentials')
            
            result = await send_email_with_retry(message, max_retries=3)
            
            assert result is False
            # Should only try once, no retries for auth errors
            assert mock_smtp.call_count == 1
    
    @pytest.mark.asyncio
    async def test_send_email_retry_delay(self):
        """Test that retry delay is applied between attempts."""
        message = MIMEMultipart()
        message['Subject'] = 'Test'
        
        with patch('smtplib.SMTP') as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value.__enter__.return_value = mock_server
            mock_server.send_message.side_effect = smtplib.SMTPException('Error')
            
            with patch('asyncio.sleep') as mock_sleep:
                result = await send_email_with_retry(message, max_retries=3)
                
                # Should sleep twice (between 3 attempts)
                assert mock_sleep.call_count == 2
                # Each sleep should be 30 seconds
                mock_sleep.assert_called_with(30)


class TestFileSavingFallback:
    """Test suite for file saving fallback functionality."""
    
    @pytest.mark.asyncio
    async def test_save_report_to_file_creates_directory(self):
        """Test that save_report_to_file creates reports directory."""
        meeting_data = {
            'meeting_start_time': datetime(2024, 11, 19, 10, 0, 0),
            'meeting_end_time': datetime(2024, 11, 19, 11, 0, 0),
            'total_duration': 3600,
            'sessions': [],
            'member_summaries': []
        }
        
        # Clean up any existing reports directory
        import shutil
        if os.path.exists('reports'):
            shutil.rmtree('reports')
        
        await save_report_to_file(meeting_data)
        
        # Verify directory was created
        assert os.path.exists('reports')
        assert os.path.isdir('reports')
        
        # Verify file was created
        files = os.listdir('reports')
        assert len(files) == 1
        assert files[0].startswith('meeting-')
        assert files[0].endswith('.json')
        
        # Clean up
        shutil.rmtree('reports')
    
    @pytest.mark.asyncio
    async def test_save_report_to_file_content(self):
        """Test that saved report contains correct data."""
        meeting_data = {
            'meeting_start_time': datetime(2024, 11, 19, 10, 0, 0),
            'meeting_end_time': datetime(2024, 11, 19, 11, 0, 0),
            'total_duration': 3600,
            'sessions': [
                {
                    'member_id': '123',
                    'member_name': 'TestUser',
                    'join_time': datetime(2024, 11, 19, 10, 0, 0),
                    'leave_time': datetime(2024, 11, 19, 11, 0, 0),
                    'duration': 3600
                }
            ],
            'member_summaries': [
                {
                    'member_id': '123',
                    'member_name': 'TestUser',
                    'total_time': 3600,
                    'session_count': 1
                }
            ]
        }
        
        # Clean up any existing reports directory
        import shutil
        if os.path.exists('reports'):
            shutil.rmtree('reports')
        
        await save_report_to_file(meeting_data)
        
        # Read the saved file
        files = os.listdir('reports')
        filepath = os.path.join('reports', files[0])
        
        with open(filepath, 'r') as f:
            saved_data = json.load(f)
        
        # Verify data structure
        assert 'meeting_start_time' in saved_data
        assert 'meeting_end_time' in saved_data
        assert 'total_duration' in saved_data
        assert saved_data['total_duration'] == 3600
        assert len(saved_data['sessions']) == 1
        assert saved_data['sessions'][0]['member_name'] == 'TestUser'
        
        # Clean up
        shutil.rmtree('reports')
    
    @pytest.mark.asyncio
    async def test_save_report_datetime_serialization(self):
        """Test that datetime objects are properly serialized to JSON."""
        meeting_data = {
            'meeting_start_time': datetime(2024, 11, 19, 10, 0, 0),
            'meeting_end_time': datetime(2024, 11, 19, 11, 0, 0),
            'total_duration': 3600,
            'sessions': [
                {
                    'member_id': '123',
                    'member_name': 'TestUser',
                    'join_time': datetime(2024, 11, 19, 10, 0, 0),
                    'leave_time': datetime(2024, 11, 19, 11, 0, 0),
                    'duration': 3600
                }
            ],
            'member_summaries': []
        }
        
        # Clean up any existing reports directory
        import shutil
        if os.path.exists('reports'):
            shutil.rmtree('reports')
        
        await save_report_to_file(meeting_data)
        
        # Read the saved file
        files = os.listdir('reports')
        filepath = os.path.join('reports', files[0])
        
        with open(filepath, 'r') as f:
            saved_data = json.load(f)
        
        # Verify datetime objects were converted to ISO format strings
        assert isinstance(saved_data['meeting_start_time'], str)
        assert '2024-11-19T10:00:00' in saved_data['meeting_start_time']
        assert isinstance(saved_data['sessions'][0]['join_time'], str)
        
        # Clean up
        shutil.rmtree('reports')


class TestSendMeetingReport:
    """Test suite for send_meeting_report integration."""
    
    @pytest.mark.asyncio
    async def test_send_meeting_report_success(self):
        """Test successful meeting report sending."""
        meeting_data = {
            'meeting_start_time': datetime(2024, 11, 19, 10, 0, 0),
            'meeting_end_time': datetime(2024, 11, 19, 11, 0, 0),
            'total_duration': 3600,
            'sessions': [],
            'member_summaries': []
        }
        
        with patch('smtplib.SMTP') as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value.__enter__.return_value = mock_server
            
            result = await send_meeting_report(meeting_data)
            
            assert result is True
            mock_server.send_message.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_meeting_report_fallback_on_failure(self):
        """Test that report is saved to file when email fails."""
        meeting_data = {
            'meeting_start_time': datetime(2024, 11, 19, 10, 0, 0),
            'meeting_end_time': datetime(2024, 11, 19, 11, 0, 0),
            'total_duration': 3600,
            'sessions': [],
            'member_summaries': []
        }
        
        # Clean up any existing reports directory
        import shutil
        if os.path.exists('reports'):
            shutil.rmtree('reports')
        
        with patch('smtplib.SMTP') as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value.__enter__.return_value = mock_server
            mock_server.send_message.side_effect = smtplib.SMTPException('Error')
            
            with patch('asyncio.sleep', return_value=None):  # Speed up test
                result = await send_meeting_report(meeting_data)
            
            assert result is False
            # Verify file was saved as fallback
            assert os.path.exists('reports')
            files = os.listdir('reports')
            assert len(files) == 1
            
            # Clean up
            shutil.rmtree('reports')
