import os
import sqlite3
import logging
import threading
import asyncio
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters

# ---------------- WEB SERVER FOR UPTIME ----------------
flask_app = Flask(__name__)

@flask_app.route('/')
def index():
    return "Prime Avay Bot is Online!", 200

def run_flask():
    # Render provides a PORT environment variable
    port = int(os.environ.get("PORT", 10000))
    flask_app.run(host='0.0.0.0', port=port)

# ---------------- CONFIGURATION ----------------
# Ensure BOT_TOKEN is set in your Render Environment Variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
# Fixed Admin ID for Prime Avay
ADMIN_ID = 5832196298 

# Social Media Links
INSTAGRAM_URL = "https://www.instagram.com/prime_avay"
YT_URL = "https://www.youtube.com/@prime_avay"
WHATSAPP_URL = "https://whatsapp.com/channel/0029Vb6m4r60QeakFUmaSO3p"
TELEGRAM_URL = "https://t.me/+80I0Jqq_9Hc3NGE9"
APPROVED_LINK = "https://t.me/primeavay"

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# ---------------- DATABASE LOGIC ----------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'bot_data.db')

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, approvals INTEGER DEFAULT 0)')
    conn.commit()
    conn.close()

def get_approvals(user_id):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT approvals FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else 0
    except Exception as e:
        logging.error(f"Database error: {e}")
        return 0

def add_approval(user_id):
    count = get_approvals(user_id) + 1
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO users (user_id, approvals) VALUES (?, ?)", (user_id, count))
    conn.commit()
    conn.close()
    return count

# ---------------- BOT HANDLERS ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    count = get_approvals(user_id)
    
    # Visual Progress Bar
    progress_bar = "✅" * count + "⏳" * (4 - count)
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📷 Instagram", url=INSTAGRAM_URL), InlineKeyboardButton("🔔 YouTube", url=YT_URL)],
        [InlineKeyboardButton("💬 WhatsApp", url=WHATSAPP_URL), InlineKeyboardButton("👥 Group Chat", url=TELEGRAM_URL)],
        [InlineKeyboardButton(f"🚀 Submit Photo ({count}/4)", callback_data="instruction")]
    ])
    
    await update.message.reply_text(
        f"👋 **Prime Avay Verification**\n\n"
        f"Progress: {count}/4\n"
        f"Status: {progress_bar}\n\n"
        f"Complete the tasks and send your screenshots directly to me.",
        reply_markup=keyboard, parse_mode="Markdown"
    )

async def instruction_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.message.reply_text("📸 Please send your screenshot now. I will forward it to the Admin.")

async def receive_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    count = get_approvals(user.id)
    
    if count >= 4:
        await update.message.reply_text(f"✅ You are already verified!\nLink: {APPROVED_LINK}")
        return

    admin_keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Approve", callback_data=f"appr_{user.id}"),
        InlineKeyboardButton("❌ Reject", callback_data=f"rejt_{user.id}")
    ]])
    
    try:
        await context.bot.send_photo(
            chat_id=ADMIN_ID, 
            photo=update.message.photo[-1].file_id, 
            caption=f"📝 User: @{user.username}\n🆔 ID: {user.id}\n📍 Verifying Step: {count + 1}/4", 
            reply_markup=admin_keyboard
        )
        await update.message.reply_text(f"✅ Screenshot for Step {count + 1} sent to Admin! Please wait.")
    except Exception as e:
        logging.error(f"Failed to send to admin: {e}")
        await update.message.reply_text("❌ Failed to contact Admin. Ensure @prime_avay has started the bot.")

async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.from_user.id != ADMIN_ID: return
    
    action, user_id = query.data.split("_")
    user_id = int(user_id)
    count = get_approvals(user_id)

    if action == "appr":
        new_count = add_approval(user_id)
        if new_count >= 4:
            await context.bot.send_message(user_id, f"🎉 Congratulations! All steps approved.\nLink: {APPROVED_LINK}")
            await query.edit_message_caption("✅ VERIFIED (4/4)")
        else:
            await context.bot.send_message(user_id, f"✅ Step {new_count} approved! Send the next screenshot.")
            await query.edit_message_caption(f"🟢 Approved {new_count}/4")
    
    elif action == "rejt":
        # Show specific step number in rejection
        rejected_step = count + 1
        await context.bot.send_message(user_id, f"❌ Your screenshot for **Step {rejected_step}** was rejected. Please resubmit a valid screenshot.")
        await query.edit_message_caption(f"🔴 Rejected (Step {rejected_step})")

# ---------------- MAIN EXECUTION ----------------
def main():
    init_db()
    threading.Thread(target=run_flask, daemon=True).start()
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(instruction_callback, pattern="^instruction$"))
    app.add_handler(MessageHandler(filters.PHOTO, receive_photo))
    app.add_handler(CallbackQueryHandler(admin_callback, pattern="^(appr|rejt)_"))
    
    print("Prime Avay Bot is starting...")
    app.run_polling(close_loop=False)

if __name__ == "__main__":
    main()
