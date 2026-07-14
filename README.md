# Gist Bot 🤖

A Telegram bot that creates GitHub Gists directly from Telegram messages.

## Features
- Create Gists from any text message
- Auto-detect file types (Python, HTML, JSON, SQL, CSS)
- Set custom descriptions
- Public/Private toggle
- Quick action buttons
- User preferences saved per session

## Commands
- `/start` - Welcome message
- `/help` - Detailed help
- `/gist filename content` - Create Gist
- `/setdescription text` - Set description
- `/public` - Make Gists public
- `/private` - Make Gists private
- `/status` - View settings

## Deploy on Render
1. Add environment variables:
   - `TELEGRAM_BOT_TOKEN`
   - `GITHUB_TOKEN`
2. Deploy!
