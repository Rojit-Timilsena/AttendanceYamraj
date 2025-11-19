"""
Voice state handler module that processes Discord voice state update events.
Filters events for the target voice channel and delegates to meeting tracker.
"""

from typing import Optional
import asyncio
import discord
from src.logger import logger
from src.config import VOICE_CHANNEL_ID
from src.meeting_tracker import MeetingTracker
from src.email_service import send_meeting_report


class VoiceStateHandler:
    """Handles Discord voice state update events for meeting tracking."""
    
    def __init__(self, meeting_tracker: MeetingTracker):
        """
        Initialize voice state handler.
        
        Args:
            meeting_tracker: MeetingTracker instance to delegate events to
        """
        self.meeting_tracker = meeting_tracker
        self.target_channel_id = VOICE_CHANNEL_ID
        self._original_end_meeting = meeting_tracker.end_meeting
        
        # Wrap the end_meeting method to intercept and send email
        meeting_tracker.end_meeting = self._wrapped_end_meeting
    
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState
    ) -> None:
        """
        Handle voice state update events from Discord.
        
        Filters events for the target voice channel and detects join/leave events.
        Delegates to meeting tracker and triggers email report when meeting ends.
        
        Args:
            member: Discord member whose voice state changed
            before: Voice state before the change
            after: Voice state after the change
        """
        try:
            # Check if this is a join event
            if self._is_join_event(before, after):
                logger.debug(f'Join event detected for {member.name}#{member.discriminator}')
                self.meeting_tracker.handle_member_join(
                    member_id=str(member.id),
                    member_name=member.name,
                    member_tag=f'{member.name}#{member.discriminator}',
                    member_nickname=member.display_name
                )
            
            # Check if this is a leave event
            elif self._is_leave_event(before, after):
                logger.debug(f'Leave event detected for {member.name}#{member.discriminator}')
                self.meeting_tracker.handle_member_leave(
                    member_id=str(member.id),
                    member_name=member.name,
                    member_tag=f'{member.name}#{member.discriminator}',
                    member_nickname=member.display_name
                )
                
                # The meeting tracker will handle starting the end timer
                # When the timer completes, our wrapped end_meeting will be called
        
        except Exception as e:
            logger.error(f'Error handling voice state update: {e}', exc_info=True)
    
    def _is_join_event(
        self,
        before: discord.VoiceState,
        after: discord.VoiceState
    ) -> bool:
        """
        Determine if the voice state change represents a join event.
        
        A join event occurs when:
        - Member moves from no channel (None) to target channel
        - Member moves from a different channel to target channel
        
        Args:
            before: Voice state before the change
            after: Voice state after the change
            
        Returns:
            True if this is a join event for the target channel
        """
        # Member is now in target channel
        is_in_target = after.channel and after.channel.id == self.target_channel_id
        
        # Member was not in target channel before
        was_not_in_target = (
            before.channel is None or 
            before.channel.id != self.target_channel_id
        )
        
        return is_in_target and was_not_in_target
    
    def _is_leave_event(
        self,
        before: discord.VoiceState,
        after: discord.VoiceState
    ) -> bool:
        """
        Determine if the voice state change represents a leave event.
        
        A leave event occurs when:
        - Member moves from target channel to no channel (None)
        - Member moves from target channel to a different channel
        
        Args:
            before: Voice state before the change
            after: Voice state after the change
            
        Returns:
            True if this is a leave event from the target channel
        """
        # Member was in target channel before
        was_in_target = before.channel and before.channel.id == self.target_channel_id
        
        # Member is not in target channel now
        is_not_in_target = (
            after.channel is None or 
            after.channel.id != self.target_channel_id
        )
        
        return was_in_target and is_not_in_target
    
    async def _wrapped_end_meeting(self):
        """
        Wrapped version of meeting_tracker.end_meeting that sends email report.
        
        This method calls the original end_meeting, captures the report,
        and sends it via email.
        
        Returns:
            Meeting report dictionary
        """
        try:
            # Call the original end_meeting method
            report = await self._original_end_meeting()
            
            # Send email report if we have data
            if report and report.get('sessions'):
                logger.info('Sending meeting report via email')
                await send_meeting_report(report)
            else:
                logger.warning('No meeting data to report')
            
            return report
            
        except Exception as e:
            logger.error(f'Error in wrapped end_meeting: {e}', exc_info=True)
            return {}


async def create_voice_state_handler(meeting_tracker: MeetingTracker) -> VoiceStateHandler:
    """
    Factory function to create a VoiceStateHandler instance.
    
    Args:
        meeting_tracker: MeetingTracker instance to use
        
    Returns:
        Configured VoiceStateHandler instance
    """
    return VoiceStateHandler(meeting_tracker)
