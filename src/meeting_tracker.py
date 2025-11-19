"""
Meeting tracker module that manages meeting state and tracks member sessions.
Handles join/leave events, calculates durations, and generates meeting reports.
"""

import asyncio
from datetime import datetime
from typing import Optional, Dict, List
from src.logger import logger
from src.config import MEETING_END_TIMEOUT


class MeetingTracker:
    """Tracks voice channel meeting state and member sessions."""
    
    def __init__(self):
        """Initialize meeting tracker with empty state."""
        self.meeting_active = False
        self.meeting_start_time: Optional[datetime] = None
        self.sessions: List[Dict] = []
        self.end_timer: Optional[asyncio.Task] = None
        self.active_members: Dict[str, datetime] = {}  # member_id -> join_time
        
    def handle_member_join(self, member_id: str, member_name: str, member_tag: str, member_nickname: str = None) -> None:
        """
        Record a member joining the voice channel.
        
        Args:
            member_id: Discord user ID
            member_name: Discord username
            member_tag: Discord username#discriminator
            member_nickname: Server nickname (display name)
        """
        join_time = datetime.now()
        
        # Start meeting if this is the first member
        if not self.meeting_active:
            self.meeting_active = True
            self.meeting_start_time = join_time
            logger.info(f'Meeting started at {join_time.strftime("%Y-%m-%d %H:%M:%S")}')
        
        # Cancel end timer if a member joins during countdown
        if self.end_timer and not self.end_timer.done():
            self.cancel_end_timer()
            logger.info('Meeting end timer cancelled - member joined')
        
        # Track active member with nickname
        self.active_members[member_id] = {
            'join_time': join_time,
            'member_name': member_name,
            'member_tag': member_tag,
            'member_nickname': member_nickname or member_name
        }
        
        logger.info(f'Member joined: {member_name} ({member_id}) at {join_time.strftime("%Y-%m-%d %H:%M:%S")}')

    def handle_member_leave(self, member_id: str, member_name: str, member_tag: str, member_nickname: str = None) -> None:
        """
        Record a member leaving the voice channel and calculate session duration.
        
        Args:
            member_id: Discord user ID
            member_name: Discord username
            member_tag: Discord username#discriminator
            member_nickname: Server nickname (display name)
        """
        leave_time = datetime.now()
        
        # Get member data for this member
        member_data = self.active_members.get(member_id)
        
        if member_data is None:
            logger.warning(f'Member leave event without join: {member_name} ({member_id})')
            return
        
        join_time = member_data['join_time']
        
        # Calculate session duration in seconds
        duration = (leave_time - join_time).total_seconds()
        
        # Create session record
        session = {
            'member_id': member_id,
            'member_name': member_data['member_name'],
            'member_tag': member_data['member_tag'],
            'member_nickname': member_data['member_nickname'],
            'join_time': join_time,
            'leave_time': leave_time,
            'duration': duration
        }
        
        self.sessions.append(session)
        
        # Remove from active members
        del self.active_members[member_id]
        
        logger.info(f'Member left: {member_name} ({member_id}) at {leave_time.strftime("%Y-%m-%d %H:%M:%S")} - Duration: {duration:.1f}s')
        
        # Start end timer if channel is now empty
        if len(self.active_members) == 0 and self.meeting_active:
            self.start_end_timer()

    def start_end_timer(self) -> None:
        """Start the meeting end timer (5-minute countdown)."""
        if self.end_timer and not self.end_timer.done():
            logger.warning('End timer already running')
            return
        
        logger.info(f'Voice channel empty - starting {MEETING_END_TIMEOUT}s end timer')
        self.end_timer = asyncio.create_task(self._end_timer_task())
    
    async def _end_timer_task(self) -> None:
        """Internal task that waits for timeout then ends the meeting."""
        try:
            await asyncio.sleep(MEETING_END_TIMEOUT)
            await self.end_meeting()
        except asyncio.CancelledError:
            logger.debug('End timer cancelled')
    
    def cancel_end_timer(self) -> None:
        """Cancel the meeting end timer."""
        if self.end_timer and not self.end_timer.done():
            self.end_timer.cancel()
            self.end_timer = None

    async def end_meeting(self) -> Dict:
        """
        End the current meeting and generate report.
        
        Returns:
            Meeting report dictionary
        """
        if not self.meeting_active:
            logger.warning('Attempted to end meeting that is not active')
            return {}
        
        meeting_end_time = datetime.now()
        
        logger.info(f'Meeting ended at {meeting_end_time.strftime("%Y-%m-%d %H:%M:%S")}')
        
        # Generate report before resetting state
        report = self.get_meeting_report(meeting_end_time)
        
        # Reset state for next meeting
        self.meeting_active = False
        self.meeting_start_time = None
        self.sessions = []
        self.active_members = {}
        self.end_timer = None
        
        return report

    def get_meeting_report(self, meeting_end_time: Optional[datetime] = None) -> Dict:
        """
        Generate a comprehensive meeting report with session data and member summaries.
        
        Args:
            meeting_end_time: End time of the meeting (defaults to now)
            
        Returns:
            Dictionary containing meeting report data
        """
        if meeting_end_time is None:
            meeting_end_time = datetime.now()
        
        if not self.meeting_start_time:
            logger.warning('Cannot generate report - no meeting start time')
            return {}
        
        # Calculate total meeting duration
        total_duration = (meeting_end_time - self.meeting_start_time).total_seconds()
        
        # Calculate member summaries
        member_summaries = self._calculate_member_summaries()
        
        report = {
            'meeting_start_time': self.meeting_start_time,
            'meeting_end_time': meeting_end_time,
            'total_duration': total_duration,
            'sessions': self.sessions.copy(),
            'member_summaries': member_summaries
        }
        
        logger.debug(f'Generated meeting report: {len(self.sessions)} sessions, {len(member_summaries)} unique members')
        
        return report

    def _calculate_member_summaries(self) -> List[Dict]:
        """
        Calculate summary statistics for each member across all their sessions.
        
        Returns:
            List of member summary dictionaries with total time and session count
        """
        member_data = {}
        
        # Aggregate data for each member
        for session in self.sessions:
            member_id = session['member_id']
            
            if member_id not in member_data:
                member_data[member_id] = {
                    'member_id': member_id,
                    'member_name': session['member_name'],
                    'member_tag': session['member_tag'],
                    'member_nickname': session.get('member_nickname', session['member_name']),
                    'total_time': 0.0,
                    'session_count': 0
                }
            
            member_data[member_id]['total_time'] += session['duration']
            member_data[member_id]['session_count'] += 1
        
        # Convert to list and sort by total time (descending)
        summaries = sorted(
            member_data.values(),
            key=lambda x: x['total_time'],
            reverse=True
        )
        
        return summaries
