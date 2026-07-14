import logging
import os
import asyncio
import threading
import requests
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

# Suppress httpx logs so token never shows in logs
logging.getLogger("httpx").setLevel(logging.WARNING)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

if not TOKEN:
    raise ValueError("❌ No TELEGRAM_BOT_TOKEN set!")
if not GITHUB_TOKEN:
    raise ValueError("❌ No GITHUB_TOKEN set!")

GITHUB_API = "https://api.github.com/gists"
user_sessions = {}

# ============================================================
# 🌐 FLASK - Keeps Render alive
# ============================================================
flask_app = Flask(__name__)

@flask_app.route('/')
def health_check():
    return "🤖 Gist Bot is running!", 200

# ============ COMMAND HANDLERS ============

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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
        "/status - View current settings"
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")

async def set_description(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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
    await update.message.reply_text(f"✅ Description set to:\n\n📝 {description}")

async def set_public(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if user_id not in user_sessions:
        user_sessions[user_id] = {}
    user_sessions[user_id]['public'] = True
    await update.message.reply_text("🌍 Gists will now be **PUBLIC**", parse_mode="Markdown")

async def set_private(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if user_id not in user_sessions:
        user_sessions[user_id] = {}
    user_sessions[user_id]['public'] = False
    await update.message.reply_text("🔒 Gists will now be **PRIVATE/SECRET**", parse_mode="Markdown")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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
    user_id = update.effective_user.id
    text = update.message.text.replace("/gist", "", 1).strip()
    if not text:
        await update.message.reply_text(
            "❌ Please provide filename and content.\n"
            "Example: `/gist main.py print('Hello World!')`"
        )
        return
    parts = text.split(" ", 1)
    if len(parts) < 2:
        await update.message.reply_text(
            "❌ Please provide both filename and content.\n"
            "Example: `/gist main.py print('Hello World!')`"
        )
        return
    filename = parts[0]
    content = parts[1]
    await update.message.chat.send_action(action="typing")
    session = user_sessions.get(user_id, {})
    description = session.get('description', f'Gist from Telegram by {update.effective_user.username or "User"}')
    public = session.get('public', False)
    success, result = create_gist(filename, content, description, public)
    if success:
        keyboard = [
            [InlineKeyboardButton("🔗 Open Gist", url=result)],
            [InlineKeyboardButton("📝 New Gist", callback_data="new_gist")],
            [InlineKeyboardButton("⚙️ Settings", callback_data="settings")]
        ]
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
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await update.message.reply_text(f"❌ Failed to create Gist: {result}")

# ============ MESSAGE HANDLER ============

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    text = update.message.text
    if text.startswith('/'):
        return
    await update.message.chat.send_action(action="typing")
    session = user_sessions.get(user_id, {})
    description = session.get('description', f'Gist from Telegram by {update.effective_user.username or "User"}')
    public = session.get('public', False)
    filename = detect_filename(text)
    success, result = create_gist(filename, text, description, public)
    if success:
        keyboard = [
            [InlineKeyboardButton("🔗 Open Gist", url=result)],
            [InlineKeyboardButton("📝 New Gist", callback_data="new_gist")],
            [InlineKeyboardButton("⚙️ Settings", callback_data="settings")]
        ]
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
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await update.message.reply_text(f"❌ Failed to create Gist: {result}")

# ============ CALLBACK HANDLER ============

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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
        await query.edit_message_text(
            "⚙️ **Your Settings**\n\n"
            f"📝 **Description:** {description}\n"
            f"👁️ **Visibility:** {visibility}\n\n"
            "🔧 **Quick Commands:**\n"
            "• `/setdescription` - Change description\n"
            "• `/public` - Make Gists public\n"
            "• `/private` - Make Gists private",
            parse_mode="Markdown"
        )

# ============ HELPER FUNCTIONS ============

def detect_filename(content):
    if 'import' in content or 'def ' in content or 'class ' in content:
        return 'main.py' if 'def main' in content else 'code.py'
    elif 'SELECT' in content.upper() or 'INSERT' in content.upper():
        return 'query.sql'
    elif '<html' in content.lower() or '<div' in content.lower():
        return 'index.html'
    elif '{' in content and '}' in content:
        return 'config.json' if ':' in content else 'style.css'
    return 'gist.txt'

def create_gist(filename, content, description, public=False):
    try:
        payload = {
            "description": description,
            "public": public,
            "files": {filename: {"content": content}}
        }
        headers = {
            "Authorization": f"token {GITHUB_TOKEN}",
            "Content-Type": "application/json"
        }
        response = requests.post(GITHUB_API, json=payload, headers=headers)
        if response.status_code == 201:
            return True, response.json()['html_url']
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
    logger.error(f"Update {update} caused error {context.error}")
    try:
        if update and update.effective_message:
            await update.effective_message.reply_text("❌ An error occurred. Please try again later.")
    except:
        pass

# ============================================================
# 🚀 BOT STARTUP
# ============================================================
async def run_bot_async():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("gist", gist_command))
    app.add_handler(CommandHandler("setdescription", set_description))
    app.add_handler(CommandHandler("public", set_public))
    app.add_handler(CommandHandler("private", set_private))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_error_handler(error_handler)

    await app.initialize()
    await app.start()
    await app.updater.start_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True
    )

    logger.info("✅ Gist Bot is polling and ready!")

    while True:
        await asyncio.sleep(1)

def run_bot():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(run_bot_async())

# Start bot thread when Gunicorn loads
bot_thread = threading.Thread(target=run_bot, daemon=True)
bot_thread.start()
