"""
Main bot entry point that initializes the Discord client and registers event handlers.
Handles bot lifecycle including startup, connection, and event processing.
"""

import signal
import sys
import asyncio
import discord
from src.logger import logger
from src.config import DISCORD_TOKEN, VOICE_CHANNEL_ID
from src.meeting_tracker import MeetingTracker
from src.voice_state_handler import VoiceStateHandler


class DiscordVoiceTrackerBot:
    """Main Discord bot client for voice channel tracking."""
    
    def __init__(self):
        """Initialize the Discord bot with required intents and components."""
        # Configure intents - we need guilds and voice_states
        intents = discord.Intents.default()
        intents.guilds = True
        intents.voice_states = True
        
        # Initialize Discord client
        self.client = discord.Client(intents=intents)
        
        # Initialize meeting tracker
        self.meeting_tracker = MeetingTracker()
        
        # Initialize voice state handler
        self.voice_handler = VoiceStateHandler(self.meeting_tracker)
        
        # Register event handlers
        self._register_event_handlers()
        
        logger.info('Discord Voice Tracker Bot initialized')
    
    def _register_event_handlers(self):
        """Register Discord event handlers with error handling."""
        
        @self.client.event
        async def on_ready():
            """Handle bot ready event - called when bot successfully connects."""
            try:
                logger.info(f'Bot connected as {self.client.user.name}#{self.client.user.discriminator}')
                logger.info(f'Bot ID: {self.client.user.id}')
                logger.info(f'Monitoring voice channel ID: {VOICE_CHANNEL_ID}')
                logger.info('Bot is online and ready')
            except Exception as e:
                logger.error(f'Error in on_ready handler: {e}', exc_info=True)
        
        @self.client.event
        async def on_voice_state_update(member, before, after):
            """Handle voice state update events with error handling."""
            try:
                await self.voice_handler.on_voice_state_update(member, before, after)
            except Exception as e:
                logger.error(f'Error in on_voice_state_update handler: {e}', exc_info=True)
    
    async def start(self):
        """Start the bot and connect to Discord."""
        logger.info('Starting Discord bot...')
        await self.client.start(DISCORD_TOKEN)
    
    async def close(self):
        """Close the bot connection gracefully."""
        logger.info('Closing Discord bot connection...')
        await self.client.close()


async def main():
    """Main entry point for the bot application with reconnection logic."""
    bot = None
    max_reconnect_time = 300  # 5 minutes in seconds
    reconnect_interval = 10  # 10 seconds between attempts
    
    # Setup signal handlers for graceful shutdown
    shutdown_event = asyncio.Event()
    
    def signal_handler(signum, frame):
        """Handle shutdown signals (SIGINT, SIGTERM)."""
        signal_name = 'SIGINT' if signum == signal.SIGINT else 'SIGTERM'
        logger.info(f'Received {signal_name}, initiating graceful shutdown...')
        shutdown_event.set()
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        bot = DiscordVoiceTrackerBot()
        
        # Create a task for the bot
        bot_task = asyncio.create_task(bot.start())
        
        # Wait for either the bot to finish or shutdown signal
        shutdown_task = asyncio.create_task(shutdown_event.wait())
        done, pending = await asyncio.wait(
            [bot_task, shutdown_task],
            return_when=asyncio.FIRST_COMPLETED
        )
        
        # Cancel pending tasks
        for task in pending:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        
        # Check if bot task raised an exception
        if bot_task in done:
            try:
                bot_task.result()
            except Exception as e:
                logger.error(f'Bot task failed: {e}', exc_info=True)
                raise
        
    except discord.LoginFailure as e:
        logger.error(f'Failed to login to Discord: {e}')
        logger.error('Please check your DISCORD_TOKEN in the .env file')
        sys.exit(1)
        
    except discord.ConnectionClosed as e:
        logger.error(f'Discord connection closed unexpectedly: {e}')
        
        # Attempt reconnection with timeout
        logger.info(f'Attempting to reconnect for up to {max_reconnect_time} seconds...')
        start_time = asyncio.get_event_loop().time()
        
        while (asyncio.get_event_loop().time() - start_time) < max_reconnect_time:
            try:
                logger.info(f'Reconnection attempt...')
                bot = DiscordVoiceTrackerBot()
                await bot.start()
                break  # Successfully reconnected
                
            except Exception as reconnect_error:
                logger.error(f'Reconnection failed: {reconnect_error}')
                
                # Check if we should continue trying
                elapsed = asyncio.get_event_loop().time() - start_time
                if elapsed < max_reconnect_time:
                    logger.info(f'Waiting {reconnect_interval} seconds before next attempt...')
                    await asyncio.sleep(reconnect_interval)
                else:
                    logger.error(f'Failed to reconnect after {max_reconnect_time} seconds')
                    sys.exit(1)
    
    except Exception as e:
        logger.error(f'Fatal error: {e}', exc_info=True)
        sys.exit(1)
    
    finally:
        # Ensure clean shutdown
        if bot:
            try:
                await bot.close()
                logger.info('Bot shutdown complete')
            except Exception as e:
                logger.error(f'Error during shutdown: {e}', exc_info=True)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info('Bot stopped by user')
    except Exception as e:
        logger.error(f'Unhandled exception: {e}', exc_info=True)
        sys.exit(1)
