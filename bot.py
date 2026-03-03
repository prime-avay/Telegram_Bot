import os
import sqlite3
import logging
import threading
import asyncio
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters

# ---------------- WEB SERVER ----------------
flask_app = Flask(__name__)
@flask_app.route('/')
def index(): return "Bot is Online!", 200

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    flask_app.run(host='0.0.0.0', port=port)

# ---------------- CONFIG ----------------
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 5832196298 

# Social Links
INSTAGRAM_URL = "https://www.instagram.com/prime_avay"
YT_URL = "https://www.youtube.com/@prime_avay"
WHATSAPP_URL = "https://whatsapp.com/channel/0029Vb6m4r60QeakFUmaSO3p"
TELEGRAM_URL = "https://t.me/+80I0Jqq_9Hc3NGE9"
APPROVED_LINK = "https://t.me/primeavay"

logging.basicConfig(level=logging.INFO)

# ---------------- DATABASE ----------------
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
    except: return 0

def add_approval(user_id):
    count = get_approvals(user_id) + 1
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO users (user_id, approvals) VALUES (?, ?)", (user_id, count))
    conn.commit()
    conn.close()
    return count

# ---------------- HANDLERS ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    count = get_approvals(user_id)
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📷 Instagram", url=INSTAGRAM_URL), InlineKeyboardButton("🔔 YouTube", url=YT_URL)],
        [InlineKeyboardButton("💬 WhatsApp", url=WHATSAPP_URL), InlineKeyboardButton("👥 Group Chat", url=TELEGRAM_URL)],
        [InlineKeyboardButton(f"🚀 Submit Photo ({count}/4)", callback_data="instruction")]
    ])
    await update.message.reply_text(f"👋 **Prime Avay Verification**\n\nProgress: {count}/4", reply_markup=keyboard, parse_mode="Markdown")

async def instruction_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.message.reply_text("📸 Please send your screenshot now.")

async def receive_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    count = get_approvals(user.id)
    if count >= 4: return
    admin_keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("✅ Approve", callback_data=f"appr_{user.id}"), InlineKeyboardButton("❌ Reject", callback_data=f"rejt_{user.id}")]])
    try:
        await context.bot.send_photo(chat_id=ADMIN_ID, photo=update.message.photo[-1].file_id, caption=f"📝 User: @{user.username}\n📍 Step: {count+1}/4", reply_markup=admin_keyboard)
        await update.message.reply_text(f"✅ Step {count+1} sent to Admin!")
    except: await update.message.reply_text("❌ Admin error.")

async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.from_user.id != ADMIN_ID: return
    action, user_id = query.data.split("_")
    user_id = int(user_id)
    if action == "appr":
        new_count = add_approval(user_id)
        if new_count >= 4:
            await context.bot.send_message(user_id, f"🎉 Verified!\nLink: {APPROVED_LINK}")
            await query.edit_message_caption("✅ VERIFIED (4/4)")
        else:
            await context.bot.send_message(user_id, f"✅ Step {new_count} approved!")
            await query.edit_message_caption(f"🟢 Approved {new_count}/4")
    elif action == "rejt":
        await context.bot.send_message(user_id, "❌ Step rejected. Try again.")

def main():
    init_db()
    threading.Thread(target=run_flask, daemon=True).start()
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(instruction_callback, pattern="^instruction$"))
    app.add_handler(MessageHandler(filters.PHOTO, receive_photo))
    app.add_handler(CallbackQueryHandler(admin_callback, pattern="^(appr|rejt)_"))
    app.run_polling(close_loop=False)

if __name__ == "__main__":
    main()
