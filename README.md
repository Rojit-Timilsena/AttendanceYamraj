# Discord Voice Tracker Bot

A Discord bot that monitors voice channel activity, tracks member join/leave events, and sends detailed attendance reports via email when meetings conclude.

## Features

- Real-time monitoring of Discord voice channel activity
- Tracks member join/leave timestamps and session durations
- Supports multiple sessions per member during a meeting
- Automatic meeting end detection (5-minute timeout after last member leaves)
- Email reports with detailed attendance summaries
- Automatic retry logic for email delivery
- Fallback to local file storage if email fails
- Comprehensive error handling and logging

## Requirements

- **Python**: 3.8 or higher
- **Discord Bot**: A Discord bot with appropriate permissions
- **SMTP Email Account**: For sending reports (Gmail, Outlook, etc.)

## Installation

1. Clone or download this repository

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment variables (see Configuration section below)

## Configuration

### Environment Variables

Create a `.env` file in the project root by copying `.env.example`:

```bash
cp .env.example .env
```

Then edit `.env` with your actual values:

| Variable | Description | Required | Example |
|----------|-------------|----------|---------|
| `DISCORD_TOKEN` | Your Discord bot token | Yes | `MTIzNDU2Nzg5MDEyMzQ1Njc4OQ.GhIjKl.MnOpQrStUvWxYzAbCdEfGhIjKlMnOpQrStUv` |
| `VOICE_CHANNEL_ID` | ID of the voice channel to monitor | Yes | `1437071975632605205` |
| `SMTP_HOST` | SMTP server hostname | Yes | `smtp.gmail.com` |
| `SMTP_PORT` | SMTP server port | Yes | `587` |
| `SMTP_USER` | SMTP authentication username | Yes | `your_email@gmail.com` |
| `SMTP_PASS` | SMTP authentication password | Yes | `your_app_password` |
| `EMAIL_FROM` | Email address to send from | Yes | `your_email@gmail.com` |
| `EMAIL_TO` | Email address to send reports to | Yes | `recipient@example.com` |
| `MEETING_END_TIMEOUT` | Timeout in seconds before ending meeting | No | `300` (5 minutes) |

### Discord Bot Setup

1. **Create a Discord Application**:
   - Go to [Discord Developer Portal](https://discord.com/developers/applications)
   - Click "New Application" and give it a name
   - Navigate to the "Bot" section
   - Click "Add Bot"

2. **Get Your Bot Token**:
   - In the Bot section, click "Reset Token"
   - Copy the token and paste it into your `.env` file as `DISCORD_TOKEN`
   - **Important**: Never share this token or commit it to version control

3. **Enable Required Intents**:
   - In the Bot section, scroll to "Privileged Gateway Intents"
   - Enable "Server Members Intent"
   - Enable "Presence Intent" (optional, but recommended)

4. **Set Bot Permissions**:
   - Navigate to the "OAuth2" > "URL Generator" section
   - Select scopes: `bot`
   - Select bot permissions:
     - View Channels
     - Connect (to monitor voice state)
     - Read Message History
   - Copy the generated URL and open it in your browser to invite the bot to your server

5. **Get Voice Channel ID**:
   - In Discord, enable Developer Mode: User Settings > Advanced > Developer Mode
   - Right-click on the voice channel you want to monitor
   - Click "Copy ID"
   - Paste this ID into your `.env` file as `VOICE_CHANNEL_ID`

### Email Setup (Gmail Example)

If using Gmail, you'll need to use an App Password:

1. Enable 2-Factor Authentication on your Google account
2. Go to [Google App Passwords](https://myaccount.google.com/apppasswords)
3. Generate a new app password for "Mail"
4. Use this app password as `SMTP_PASS` in your `.env` file

For other email providers, consult their documentation for SMTP settings.

## Running the Bot

Start the bot with:

```bash
python src/bot.py
```

The bot will:
- Connect to Discord
- Start monitoring the configured voice channel
- Log activity to console and `logs/` directory
- Send email reports when meetings end

To run in the background (Linux/Mac):

```bash
nohup python src/bot.py &
```

## How It Works

1. **Meeting Start**: When the first member joins the monitored voice channel, a new meeting session begins
2. **Activity Tracking**: The bot records every join/leave event with timestamps
3. **Session Calculation**: When a member leaves, the bot calculates their session duration
4. **Meeting End**: After the channel is empty for 5 minutes, the meeting is marked as ended
5. **Report Generation**: An email report is generated with all session data and member summaries
6. **Email Delivery**: The report is sent via email with automatic retry (3 attempts)
7. **Fallback Storage**: If email fails, the report is saved to `reports/meeting-{timestamp}.json`

## Email Report Format

The email report includes:
- Meeting start and end times
- Total meeting duration
- For each session:
  - Member name
  - Join time
  - Leave time
  - Session duration
- Member summaries:
  - Total participation time per member
  - Number of sessions per member

## Troubleshooting

### Bot won't start

**Problem**: `Configuration error: Missing required environment variable`

**Solution**: Ensure all required variables are set in your `.env` file. Check for typos.

---

**Problem**: `discord.errors.LoginFailure: Improper token has been passed`

**Solution**: Verify your `DISCORD_TOKEN` is correct. Generate a new token if needed.

---

### Bot connects but doesn't track activity

**Problem**: Bot is online but doesn't respond to voice channel events

**Solution**: 
- Verify `VOICE_CHANNEL_ID` is correct
- Ensure the bot has "Server Members Intent" enabled in Discord Developer Portal
- Check that the bot has permission to view the voice channel

---

### Email not sending

**Problem**: `Email sending failed` in logs

**Solution**:
- Verify SMTP credentials are correct
- For Gmail, ensure you're using an App Password, not your regular password
- Check SMTP_HOST and SMTP_PORT are correct for your provider
- Verify your email provider allows SMTP access
- Check `reports/` directory for saved reports as fallback

---

**Problem**: `SMTPAuthenticationError`

**Solution**:
- For Gmail: Use an App Password instead of your regular password
- For other providers: Check if "less secure app access" needs to be enabled
- Verify SMTP_USER and SMTP_PASS are correct

---

### Connection issues

**Problem**: Bot keeps disconnecting

**Solution**:
- Check your internet connection
- The bot will automatically retry connection for up to 5 minutes
- Check Discord API status at [Discord Status](https://discordstatus.com)

---

### Logs not appearing

**Problem**: No log files in `logs/` directory

**Solution**:
- The `logs/` directory is created automatically
- Check file permissions in the project directory
- Look for console output if file logging fails

## Project Structure

```
discord-voice-tracker/
├── src/
│   ├── bot.py                    # Main entry point
│   ├── config.py                 # Configuration management
│   ├── logger.py                 # Logging setup
│   ├── meeting_tracker.py        # Meeting state management
│   ├── voice_state_handler.py    # Discord event handler
│   └── email_service.py          # Email report service
├── logs/                         # Log files (auto-created)
├── reports/                      # Fallback report storage (auto-created)
├── .env                          # Your configuration (not in git)
├── .env.example                  # Example configuration
├── .gitignore                    # Git ignore rules
├── requirements.txt              # Python dependencies
└── README.md                     # This file
```

## Logs

Logs are stored in `logs/discord_bot_YYYYMMDD.log` with the following levels:
- **ERROR**: Critical issues that need attention
- **WARNING**: Important events (connection issues, retry attempts)
- **INFO**: Normal operation events (joins, leaves, meeting end)
- **DEBUG**: Detailed diagnostic information

## Security Notes

- Never commit your `.env` file to version control
- Keep your Discord bot token secret
- Use app-specific passwords for email services
- Regularly rotate credentials
- Review bot permissions to ensure minimum required access

## License

This project is provided as-is for monitoring Discord voice channel activity.

## Support

For issues or questions:
1. Check the Troubleshooting section above
2. Review logs in the `logs/` directory
3. Verify all configuration values are correct
4. Check Discord API status and email provider status
