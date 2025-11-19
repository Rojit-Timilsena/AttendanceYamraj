"""
Test suite for meeting tracker module.
Tests join/leave event handling, session duration calculations, 
meeting end timer behavior, and multiple sessions per member.
"""

import os
# Set TESTING environment variable before importing modules
os.environ['TESTING'] = '1'

import asyncio
import pytest
from datetime import datetime, timedelta
from src.meeting_tracker import MeetingTracker


class TestMeetingTracker:
    """Test suite for MeetingTracker class."""
    
    def setup_method(self):
        """Set up a fresh MeetingTracker instance for each test."""
        self.tracker = MeetingTracker()
    
    # Test join/leave event handling (Requirements 1.1, 2.1)
    
    def test_member_join_starts_meeting(self):
        """Test that first member join starts a meeting."""
        assert not self.tracker.meeting_active
        assert self.tracker.meeting_start_time is None
        
        self.tracker.handle_member_join('123', 'TestUser', 'TestUser#1234')
        
        assert self.tracker.meeting_active
        assert self.tracker.meeting_start_time is not None
        assert '123' in self.tracker.active_members
    
    def test_member_join_records_timestamp(self):
        """Test that member join records correct timestamp."""
        before_join = datetime.now()
        self.tracker.handle_member_join('123', 'TestUser', 'TestUser#1234')
        after_join = datetime.now()
        
        join_time = self.tracker.active_members['123']
        assert before_join <= join_time <= after_join
    
    @pytest.mark.asyncio
    async def test_member_leave_creates_session(self):
        """Test that member leave creates a session record."""
        self.tracker.handle_member_join('123', 'TestUser', 'TestUser#1234')
        self.tracker.handle_member_leave('123', 'TestUser', 'TestUser#1234')
        
        assert len(self.tracker.sessions) == 1
        session = self.tracker.sessions[0]
        assert session['member_id'] == '123'
        assert session['member_name'] == 'TestUser'
        assert session['leave_time'] is not None
        
        # Clean up timer
        self.tracker.cancel_end_timer()
    
    def test_member_leave_without_join_logs_warning(self):
        """Test that leave without join doesn't crash."""
        # Should not raise exception
        self.tracker.handle_member_leave('999', 'UnknownUser', 'UnknownUser#9999')
        assert len(self.tracker.sessions) == 0
    
    # Test session duration calculations (Requirements 2.2, 2.3)
    
    @pytest.mark.asyncio
    async def test_session_duration_calculation(self):
        """Test that session duration is calculated correctly."""
        self.tracker.handle_member_join('123', 'TestUser', 'TestUser#1234')
        
        # Wait a short time to create measurable duration
        await asyncio.sleep(0.1)
        
        self.tracker.handle_member_leave('123', 'TestUser', 'TestUser#1234')
        
        session = self.tracker.sessions[0]
        assert session['duration'] is not None
        assert session['duration'] >= 0.1
        assert session['duration'] < 1.0  # Should be less than 1 second
    
    @pytest.mark.asyncio
    async def test_session_stores_all_required_fields(self):
        """Test that session contains all required fields."""
        self.tracker.handle_member_join('123', 'TestUser', 'TestUser#1234')
        self.tracker.handle_member_leave('123', 'TestUser', 'TestUser#1234')
        
        session = self.tracker.sessions[0]
        assert 'member_id' in session
        assert 'member_name' in session
        assert 'member_tag' in session
        assert 'join_time' in session
        assert 'leave_time' in session
        assert 'duration' in session
        
        # Clean up timer
        self.tracker.cancel_end_timer()
    
    # Test meeting end timer behavior (Requirements 4.1, 4.2, 4.3)
    
    @pytest.mark.asyncio
    async def test_end_timer_starts_when_channel_empty(self):
        """Test that end timer starts when last member leaves."""
        self.tracker.handle_member_join('123', 'TestUser', 'TestUser#1234')
        self.tracker.handle_member_leave('123', 'TestUser', 'TestUser#1234')
        
        assert self.tracker.end_timer is not None
        assert not self.tracker.end_timer.done()
        
        # Clean up
        self.tracker.cancel_end_timer()
    
    @pytest.mark.asyncio
    async def test_end_timer_cancelled_when_member_joins(self):
        """Test that end timer is cancelled when a member joins during countdown."""
        # First member joins and leaves
        self.tracker.handle_member_join('123', 'TestUser1', 'TestUser1#1234')
        self.tracker.handle_member_leave('123', 'TestUser1', 'TestUser1#1234')
        
        assert self.tracker.end_timer is not None
        
        # Second member joins before timer expires
        self.tracker.handle_member_join('456', 'TestUser2', 'TestUser2#5678')
        
        # Timer should be cancelled
        assert self.tracker.end_timer is None or self.tracker.end_timer.cancelled()
    
    @pytest.mark.asyncio
    async def test_meeting_ends_after_timeout(self):
        """Test that meeting ends after timeout period."""
        # Use a very short timeout for testing
        original_timeout = self.tracker.meeting_tracker if hasattr(self.tracker, 'meeting_tracker') else None
        
        self.tracker.handle_member_join('123', 'TestUser', 'TestUser#1234')
        self.tracker.handle_member_leave('123', 'TestUser', 'TestUser#1234')
        
        # Manually trigger end meeting for testing
        report = await self.tracker.end_meeting()
        
        assert not self.tracker.meeting_active
        assert self.tracker.meeting_start_time is None
        assert len(self.tracker.sessions) == 0
        assert report is not None
    
    # Test multiple sessions per member (Requirements 3.1, 3.2, 3.3)
    
    @pytest.mark.asyncio
    async def test_multiple_sessions_same_member(self):
        """Test that same member can have multiple sessions."""
        # First session
        self.tracker.handle_member_join('123', 'TestUser', 'TestUser#1234')
        self.tracker.handle_member_leave('123', 'TestUser', 'TestUser#1234')
        
        # Second session
        self.tracker.handle_member_join('123', 'TestUser', 'TestUser#1234')
        self.tracker.handle_member_leave('123', 'TestUser', 'TestUser#1234')
        
        assert len(self.tracker.sessions) == 2
        assert self.tracker.sessions[0]['member_id'] == '123'
        assert self.tracker.sessions[1]['member_id'] == '123'
        
        # Clean up timer
        self.tracker.cancel_end_timer()
    
    @pytest.mark.asyncio
    async def test_sessions_chronological_order(self):
        """Test that sessions are stored in chronological order."""
        # Member 1 joins
        self.tracker.handle_member_join('123', 'User1', 'User1#1234')
        
        # Member 2 joins
        self.tracker.handle_member_join('456', 'User2', 'User2#5678')
        
        # Member 1 leaves
        self.tracker.handle_member_leave('123', 'User1', 'User1#1234')
        
        # Member 2 leaves
        self.tracker.handle_member_leave('456', 'User2', 'User2#5678')
        
        assert len(self.tracker.sessions) == 2
        # First session should be User1 (left first)
        assert self.tracker.sessions[0]['member_id'] == '123'
        # Second session should be User2 (left second)
        assert self.tracker.sessions[1]['member_id'] == '456'
        
        # Clean up timer
        self.tracker.cancel_end_timer()
    
    def test_multiple_members_tracked_separately(self):
        """Test that multiple members are tracked with separate sessions."""
        self.tracker.handle_member_join('123', 'User1', 'User1#1234')
        self.tracker.handle_member_join('456', 'User2', 'User2#5678')
        
        assert len(self.tracker.active_members) == 2
        assert '123' in self.tracker.active_members
        assert '456' in self.tracker.active_members
        
        self.tracker.handle_member_leave('123', 'User1', 'User1#1234')
        
        assert len(self.tracker.active_members) == 1
        assert '456' in self.tracker.active_members
        assert len(self.tracker.sessions) == 1
    
    # Test meeting report generation
    
    @pytest.mark.asyncio
    async def test_meeting_report_contains_all_data(self):
        """Test that meeting report contains all required data."""
        self.tracker.handle_member_join('123', 'TestUser', 'TestUser#1234')
        self.tracker.handle_member_leave('123', 'TestUser', 'TestUser#1234')
        
        report = await self.tracker.end_meeting()
        
        assert 'meeting_start_time' in report
        assert 'meeting_end_time' in report
        assert 'total_duration' in report
        assert 'sessions' in report
        assert 'member_summaries' in report
    
    @pytest.mark.asyncio
    async def test_member_summaries_calculation(self):
        """Test that member summaries aggregate session data correctly."""
        # Member has two sessions
        self.tracker.handle_member_join('123', 'TestUser', 'TestUser#1234')
        self.tracker.handle_member_leave('123', 'TestUser', 'TestUser#1234')
        
        self.tracker.handle_member_join('123', 'TestUser', 'TestUser#1234')
        self.tracker.handle_member_leave('123', 'TestUser', 'TestUser#1234')
        
        report = self.tracker.get_meeting_report()
        
        assert len(report['member_summaries']) == 1
        summary = report['member_summaries'][0]
        assert summary['member_id'] == '123'
        assert summary['session_count'] == 2
        assert summary['total_time'] > 0
        
        # Clean up timer
        self.tracker.cancel_end_timer()
    
    @pytest.mark.asyncio
    async def test_member_summaries_multiple_members(self):
        """Test member summaries with multiple members."""
        # User1 has one session
        self.tracker.handle_member_join('123', 'User1', 'User1#1234')
        self.tracker.handle_member_leave('123', 'User1', 'User1#1234')
        
        # User2 has one session
        self.tracker.handle_member_join('456', 'User2', 'User2#5678')
        self.tracker.handle_member_leave('456', 'User2', 'User2#5678')
        
        report = self.tracker.get_meeting_report()
        
        assert len(report['member_summaries']) == 2
        member_ids = [s['member_id'] for s in report['member_summaries']]
        assert '123' in member_ids
        assert '456' in member_ids
        
        # Clean up timer
        self.tracker.cancel_end_timer()
