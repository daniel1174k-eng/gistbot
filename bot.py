# ============ HIDE TOKEN FROM LOGS (MUST BE FIRST) ============
import logging
logging.getLogger("httpx").setLevel(logging.WARNING)

# ============ IMPORTS ============
import os
import asyncio
import threading
from datetime import datetime
import pytz
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

# ============ LOGGING ============
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ============ ENVIRONMENT VARIABLES ============
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise ValueError("❌ No TELEGRAM_BOT_TOKEN set!")

# ============ WORLD CLOCKS ============
COUNTRIES = {
    "🇺🇸 USA (New York)": "America/New_York",
    "🇺🇸 USA (Los Angeles)": "America/Los_Angeles",
    "🇺🇸 USA (Chicago)": "America/Chicago",
    "🇬🇧 UK (London)": "Europe/London",
    "🇫🇷 France (Paris)": "Europe/Paris",
    "🇩🇪 Germany (Berlin)": "Europe/Berlin",
    "🇷🇺 Russia (Moscow)": "Europe/Moscow",
    "🇦🇪 UAE (Dubai)": "Asia/Dubai",
    "🇮🇳 India (Mumbai)": "Asia/Kolkata",
    "🇨🇳 China (Beijing)": "Asia/Shanghai",
    "🇯🇵 Japan (Tokyo)": "Asia/Tokyo",
    "🇦🇺 Australia (Sydney)": "Australia/Sydney",
    "🇧🇷 Brazil (São Paulo)": "America/Sao_Paulo",
    "🇨🇦 Canada (Toronto)": "America/Toronto",
    "🇿🇦 South Africa": "Africa/Johannesburg",
    "🇳🇬 Nigeria (Lagos)": "Africa/Lagos",
    "🇰🇪 Kenya (Nairobi)": "Africa/Nairobi",
    "🇸🇬 Singapore": "Asia/Singapore",
    "🇹🇷 Turkey (Istanbul)": "Europe/Istanbul",
    "🇲🇽 Mexico (Mexico City)": "America/Mexico_City",
}

def get_time(timezone):
    tz = pytz.timezone(timezone)
    now = datetime.now(tz)
    return now.strftime("%I:%M %p"), now.strftime("%A, %B %d %Y")

# ============ FLASK - KEEPS RENDER ALIVE ============
flask_app = Flask(__name__)

@flask_app.route('/')
def health_check():
    return "🌍 World Clock Bot is running!", 200

# ============ COMMANDS ============

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [
        [InlineKeyboardButton("🌍 Show All Times", callback_data="all_times")],
        [InlineKeyboardButton("🇺🇸 USA", callback_data="usa"),
         InlineKeyboardButton("🇬🇧 UK", callback_data="uk")],
        [InlineKeyboardButton("🇦🇪 Dubai", callback_data="dubai"),
         InlineKeyboardButton("🇮🇳 India", callback_data="india")],
        [InlineKeyboardButton("🇯🇵 Japan", callback_data="japan"),
         InlineKeyboardButton("🇦🇺 Australia", callback_data="australia")],
        [InlineKeyboardButton("🇳🇬 Nigeria", callback_data="nigeria"),
         InlineKeyboardButton("🇨🇳 China", callback_data="china")],
    ]
    await update.message.reply_text(
        "🌍 <b>World Clock Bot</b>\n\n"
        "Get the current time in any country!\n\n"
        "🔧 <b>Commands:</b>\n"
        "/time - Show all world times\n"
        "/usa - USA time\n"
        "/uk - UK time\n"
        "/search [country] - Search any country\n"
        "/help - Show help\n\n"
        "Or tap a button below 👇",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "📚 <b>World Clock Bot Help</b>\n\n"
        "<b>Commands:</b>\n"
        "/time - Show all world times\n"
        "/usa - Get USA times\n"
        "/uk - Get UK time\n"
        "/search Nigeria - Search a country\n\n"
        "<b>Examples:</b>\n"
        "<code>/search Japan</code>\n"
        "<code>/search Dubai</code>\n"
        "<code>/search Brazil</code>\n\n"
        "Or just send a country name directly!",
        parse_mode="HTML"
    )

async def all_times(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = "🌍 <b>World Clock</b>\n\n"
    for country, timezone in COUNTRIES.items():
        time, _ = get_time(timezone)
        text += f"{country}: <b>{time}</b>\n"
    await update.message.reply_text(text, parse_mode="HTML")

async def usa_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    ny_time, ny_date = get_time("America/New_York")
    la_time, _ = get_time("America/Los_Angeles")
    ch_time, _ = get_time("America/Chicago")
    await update.message.reply_text(
        f"🇺🇸 <b>USA Times</b>\n\n"
        f"📅 {ny_date}\n\n"
        f"🗽 New York (EST): <b>{ny_time}</b>\n"
        f"🎬 Los Angeles (PST): <b>{la_time}</b>\n"
        f"🌆 Chicago (CST): <b>{ch_time}</b>",
        parse_mode="HTML"
    )

async def uk_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    time, date = get_time("Europe/London")
    await update.message.reply_text(
        f"🇬🇧 <b>UK Time</b>\n\n"
        f"📅 {date}\n"
        f"🕐 London: <b>{time}</b>",
        parse_mode="HTML"
    )

async def search_country(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = " ".join(context.args).strip().lower() if context.args else ""
    if not query:
        await update.message.reply_text(
            "❌ Please provide a country name.\n"
            "Example: <code>/search Japan</code>",
            parse_mode="HTML"
        )
        return
    results = {k: v for k, v in COUNTRIES.items() if query in k.lower()}
    if not results:
        await update.message.reply_text(
            f"❌ No results for <b>{query}</b>\n\n"
            "Try: USA, UK, Japan, Dubai, Nigeria, India, China, Australia...",
            parse_mode="HTML"
        )
        return
    text = f"🔍 <b>Results for '{query}':</b>\n\n"
    for country, timezone in results.items():
        time, date = get_time(timezone)
        text += f"{country}\n📅 {date}\n🕐 <b>{time}</b>\n\n"
    await update.message.reply_text(text, parse_mode="HTML")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.message.text.strip().lower()
    results = {k: v for k, v in COUNTRIES.items() if query in k.lower()}
    if results:
        text = f"🔍 <b>Results for '{query}':</b>\n\n"
        for country, timezone in results.items():
            time, date = get_time(timezone)
            text += f"{country}\n📅 {date}\n🕐 <b>{time}</b>\n\n"
        await update.message.reply_text(text, parse_mode="HTML")
    else:
        await update.message.reply_text(
            f"❌ No results for <b>{query}</b>\n\n"
            "Try: USA, UK, Japan, Dubai, Nigeria, India...\n\n"
            "Or use /time to see all countries",
            parse_mode="HTML"
        )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    if query.data == "all_times":
        text = "🌍 <b>World Clock</b>\n\n"
        for country, timezone in COUNTRIES.items():
            time, _ = get_time(timezone)
            text += f"{country}: <b>{time}</b>\n"
        await query.edit_message_text(text, parse_mode="HTML")

    elif query.data == "usa":
        ny_time, ny_date = get_time("America/New_York")
        la_time, _ = get_time("America/Los_Angeles")
        ch_time, _ = get_time("America/Chicago")
        await query.edit_message_text(
            f"🇺🇸 <b>USA Times</b>\n\n"
            f"📅 {ny_date}\n\n"
            f"🗽 New York: <b>{ny_time}</b>\n"
            f"🎬 Los Angeles: <b>{la_time}</b>\n"
            f"🌆 Chicago: <b>{ch_time}</b>",
            parse_mode="HTML"
        )

    elif query.data == "uk":
        time, date = get_time("Europe/London")
        await query.edit_message_text(
            f"🇬🇧 <b>UK Time</b>\n\n"
            f"📅 {date}\n🕐 London: <b>{time}</b>",
            parse_mode="HTML"
        )

    elif query.data == "dubai":
        time, date = get_time("Asia/Dubai")
        await query.edit_message_text(
            f"🇦🇪 <b>Dubai Time</b>\n\n"
            f"📅 {date}\n🕐 Dubai: <b>{time}</b>",
            parse_mode="HTML"
        )

    elif query.data == "india":
        time, date = get_time("Asia/Kolkata")
        await query.edit_message_text(
            f"🇮🇳 <b>India Time</b>\n\n"
            f"📅 {date}\n🕐 Mumbai: <b>{time}</b>",
            parse_mode="HTML"
        )

    elif query.data == "japan":
        time, date = get_time("Asia/Tokyo")
        await query.edit_message_text(
            f"🇯🇵 <b>Japan Time</b>\n\n"
            f"📅 {date}\n🕐 Tokyo: <b>{time}</b>",
            parse_mode="HTML"
        )

    elif query.data == "australia":
        time, date = get_time("Australia/Sydney")
        await query.edit_message_text(
            f"🇦🇺 <b>Australia Time</b>\n\n"
            f"📅 {date}\n🕐 Sydney: <b>{time}</b>",
            parse_mode="HTML"
        )

    elif query.data == "nigeria":
        time, date = get_time("Africa/Lagos")
        await query.edit_message_text(
            f"🇳🇬 <b>Nigeria Time</b>\n\n"
            f"📅 {date}\n🕐 Lagos: <b>{time}</b>",
            parse_mode="HTML"
        )

    elif query.data == "china":
        time, date = get_time("Asia/Shanghai")
        await query.edit_message_text(
            f"🇨🇳 <b>China Time</b>\n\n"
            f"📅 {date}\n🕐 Beijing: <b>{time}</b>",
            parse_mode="HTML"
        )

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(f"Update {update} caused error {context.error}")
    try:
        if update and update.effective_message:
            await update.effective_message.reply_text("❌ An error occurred. Please try again.")
    except:
        pass

# ============================================================
# 🚀 BOT STARTUP
# ============================================================
async def run_bot_async():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("time", all_times))
    app.add_handler(CommandHandler("usa", usa_time))
    app.add_handler(CommandHandler("uk", uk_time))
    app.add_handler(CommandHandler("search", search_country))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_error_handler(error_handler)

    await app.initialize()
    await app.start()
    await app.updater.start_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True
    )

    logger.info("✅ World Clock Bot is polling and ready!")

    while True:
        await asyncio.sleep(1)

def run_bot():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(run_bot_async())

bot_thread = threading.Thread(target=run_bot, daemon=True)
bot_thread.start()
