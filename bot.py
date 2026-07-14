import logging
import os
import requests
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Get environment variables
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

if not TOKEN:
    raise ValueError("No TELEGRAM_BOT_TOKEN set in environment variables")
if not GITHUB_TOKEN:
    raise ValueError("No GITHUB_TOKEN set in environment variables")

# GitHub API endpoint
GITHUB_API = "https://api.github.com/gists"

# Store user sessions
user_sessions = {}

# ============ COMMAND HANDLERS ============

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send welcome message when /start is issued."""
    user = update.effective_user
    welcome_text = (
        f"👋 Hello {user.first_name}!\n\n"
        "I'm a **Gist Bot** that creates GitHub Gists directly from Telegram.\n\n"
        "📝 **How to use:**\n"
        "1. Send me any text message or code snippet\n"
        "2. I'll create a Gist with your content\n"
        "3. You'll receive the Gist URL\n\n"
        "🔧 **Commands:**\n"
        "/start - Show this message\n"
        "/help - Get detailed help\n"
        "/gist - Create a Gist with custom filename\n"
        "/setdescription - Set description for your Gist\n"
        "/public - Make Gists public (default is secret)\n"
        "/private - Make Gists private/secret\n"
        "/status - Check your current settings\n\n"
        "💡 **Example:** `/gist main.py print('Hello World!')`"
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send help message."""
    help_text = (
        "📚 **Help & Commands**\n\n"
        "**Create a Gist:**\n"
        "• Simply send any text message\n"
        "• Or use: `/gist filename content`\n\n"
        "**Examples:**\n"
        "`/gist hello.py print('Hello World!')`\n"
        "`/gist style.css .container { display: flex; }`\n\n"
        "**Set Description:**\n"
        "`/setdescription My awesome code`\n\n"
        "**Toggle Privacy:**\n"
        "/public - Make Gists public\n"
        "/private - Make Gists private (default)\n\n"
        "**Check Status:**\n"
        "/status - View current settings\n\n"
        "**Manage Gists:**\n"
        "• All Gists are saved to your GitHub account\n"
        "• You can edit/delete them on GitHub\n"
        "• Share the URL with anyone"
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")

async def set_description(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Set description for the Gist."""
    user_id = update.effective_user.id
    description = update.message.text.replace("/setdescription", "", 1).strip()
    
    if not description:
        await update.message.reply_text(
            "❌ Please provide a description.\n"
            "Example: `/setdescription My awesome Python script`"
        )
        return
    
    if user_id not in user_sessions:
        user_sessions[user_id] = {}
    
    user_sessions[user_id]['description'] = description
    await update.message.reply_text(
        f"✅ Description set to:\n\n"
        f"📝 {description}"
    )

async def set_public(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Make Gists public."""
    user_id = update.effective_user.id
    if user_id not in user_sessions:
        user_sessions[user_id] = {}
    user_sessions[user_id]['public'] = True
    await update.message.reply_text("🌍 Gists will now be **PUBLIC** (visible to everyone)", parse_mode="Markdown")

async def set_private(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Make Gists private."""
    user_id = update.effective_user.id
    if user_id not in user_sessions:
        user_sessions[user_id] = {}
    user_sessions[user_id]['public'] = False
    await update.message.reply_text("🔒 Gists will now be **PRIVATE/SECRET** (only you can see them)", parse_mode="Markdown")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show current settings."""
    user_id = update.effective_user.id
    session = user_sessions.get(user_id, {})
    
    description = session.get('description', 'Not set (using default)')
    visibility = "Public" if session.get('public', False) else "Private/Secret"
    
    status_text = (
        "📊 **Your Current Settings**\n\n"
        f"📝 **Description:** {description}\n"
        f"👁️ **Visibility:** {visibility}\n\n"
        "🔧 **To change:**\n"
        "• `/setdescription` - Change description\n"
        "• `/public` - Make Gists public\n"
        "• `/private` - Make Gists private"
    )
    await update.message.reply_text(status_text, parse_mode="Markdown")

async def gist_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Create a Gist using /gist command."""
    user_id = update.effective_user.id
    
    # Get command arguments
    text = update.message.text.replace("/gist", "", 1).strip()
    
    if not text:
        await update.message.reply_text(
            "❌ Please provide filename and content.\n"
            "Example: `/gist main.py print('Hello World!')`"
        )
        return
    
    # Split filename and content
    parts = text.split(" ", 1)
    if len(parts) < 2:
        await update.message.reply_text(
            "❌ Please provide both filename and content.\n"
            "Example: `/gist main.py print('Hello World!')`"
        )
        return
    
    filename = parts[0]
    content = parts[1]
    
    # Show typing indicator
    await update.message.chat.send_action(action="typing")
    
    # Get user settings
    session = user_sessions.get(user_id, {})
    description = session.get('description', f'Gist from Telegram by {update.effective_user.username or "User"}')
    public = session.get('public', False)
    
    # Create the Gist
    success, result = create_gist(filename, content, description, public)
    
    if success:
        keyboard = [
            [InlineKeyboardButton("🔗 Open Gist", url=result)],
            [InlineKeyboardButton("📝 New Gist", callback_data="new_gist")],
            [InlineKeyboardButton("⚙️ Settings", callback_data="settings")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"✅ **Gist created successfully!**\n\n"
            f"📂 **Filename:** `{filename}`\n"
            f"📝 **Description:** {description}\n"
            f"👁️ **Visibility:** {'Public' if public else 'Private'}\n\n"
            f"🔗 **URL:** {result}\n\n"
            f"📊 **Stats:**\n"
            f"• Lines: {len(content.splitlines())}\n"
            f"• Characters: {len(content)}\n"
            f"• Size: {len(content.encode('utf-8'))} bytes",
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            f"❌ Failed to create Gist: {result}\n\n"
            "Please check:\n"
            "• Your GitHub token is valid\n"
            "• You have internet connection\n"
            "• The content is valid"
        )

# ============ MESSAGE HANDLER ============

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle text messages - create Gist from plain text."""
    user_id = update.effective_user.id
    text = update.message.text
    
    # Skip if it's a command
    if text.startswith('/'):
        return
    
    # Show typing indicator
    await update.message.chat.send_action(action="typing")
    
    # Get user settings
    session = user_sessions.get(user_id, {})
    description = session.get('description', f'Gist from Telegram by {update.effective_user.username or "User"}')
    public = session.get('public', False)
    
    # Auto-detect file extension based on content
    filename = detect_filename(text)
    
    # Create the Gist
    success, result = create_gist(filename, text, description, public)
    
    if success:
        keyboard = [
            [InlineKeyboardButton("🔗 Open Gist", url=result)],
            [InlineKeyboardButton("📝 New Gist", callback_data="new_gist")],
            [InlineKeyboardButton("⚙️ Settings", callback_data="settings")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"✅ **Gist created successfully!**\n\n"
            f"📂 **Filename:** `{filename}`\n"
            f"📝 **Description:** {description}\n"
            f"👁️ **Visibility:** {'Public' if public else 'Private'}\n\n"
            f"🔗 **URL:** {result}\n\n"
            f"📊 **Stats:**\n"
            f"• Lines: {len(text.splitlines())}\n"
            f"• Characters: {len(text)}\n"
            f"• Size: {len(text.encode('utf-8'))} bytes",
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            f"❌ Failed to create Gist: {result}\n\n"
            "Please check your GitHub token is valid."
        )

# ============ CALLBACK HANDLER ============

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle button clicks."""
    query = update.callback_query
    await query.answer()
    
    if query.data == "new_gist":
        await query.edit_message_text(
            "📝 **Create a New Gist**\n\n"
            "Send me any text message or code snippet!\n\n"
            "You can also use:\n"
            "• `/gist filename content` - Create with specific filename\n"
            "• `/setdescription` - Set a description\n"
            "• `/status` - Check your current settings",
            parse_mode="Markdown"
        )
    elif query.data == "settings":
        user_id = update.effective_user.id
        session = user_sessions.get(user_id, {})
        
        description = session.get('description', 'Not set (using default)')
        visibility = "Public" if session.get('public', False) else "Private/Secret"
        
        settings_text = (
            "⚙️ **Your Settings**\n\n"
            f"📝 **Description:** {description}\n"
            f"👁️ **Visibility:** {visibility}\n\n"
            "🔧 **Quick Commands:**\n"
            "• `/setdescription` - Change description\n"
            "• `/public` - Make Gists public\n"
            "• `/private` - Make Gists private"
        )
        await query.edit_message_text(settings_text, parse_mode="Markdown")

# ============ HELPER FUNCTIONS ============

def detect_filename(content):
    """Detect the best filename based on content."""
    # Check for common programming language indicators
    if 'import' in content or 'def ' in content or 'class ' in content:
        if 'def main' in content:
            return 'main.py'
        return 'code.py'
    elif 'SELECT' in content.upper() or 'INSERT' in content.upper():
        return 'query.sql'
    elif '<html' in content.lower() or '<div' in content.lower():
        return 'index.html'
    elif '{' in content and '}' in content:
        if ':' in content:
            return 'config.json'
        return 'style.css'
    else:
        return 'gist.txt'

def create_gist(filename, content, description, public=False):
    """Create a Gist on GitHub."""
    try:
        payload = {
            "description": description,
            "public": public,
            "files": {
                filename: {
                    "content": content
                }
            }
        }
        
        headers = {
            "Authorization": f"token {GITHUB_TOKEN}",
            "Content-Type": "application/json"
        }
        
        response = requests.post(GITHUB_API, json=payload, headers=headers)
        
        if response.status_code == 201:
            data = response.json()
            return True, data['html_url']
        else:
            error_msg = f"GitHub API error: {response.status_code}"
            try:
                error_data = response.json()
                if 'message' in error_data:
                    error_msg += f" - {error_data['message']}"
            except:
                pass
            return False, error_msg
            
    except requests.exceptions.RequestException as e:
        return False, f"Network error: {str(e)}"
    except Exception as e:
        return False, f"Unexpected error: {str(e)}"

# ============ ERROR HANDLER ============

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log errors and prevent the bot from crashing."""
    logger.error(f"Update {update} caused error {context.error}")
    try:
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "❌ An error occurred. Please try again later."
            )
    except:
        pass

# ============ MAIN FUNCTION ============

def main() -> None:
    """Start the bot."""
    application = Application.builder().token(TOKEN).build()
    
    # Command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("gist", gist_command))
    application.add_handler(CommandHandler("setdescription", set_description))
    application.add_handler(CommandHandler("public", set_public))
    application.add_handler(CommandHandler("private", set_private))
    application.add_handler(CommandHandler("status", status))
    
    # Message handlers
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    # Callback handler
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Error handler
    application.add_error_handler(error_handler)
    
    logger.info("Gist Bot started and polling for updates...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
