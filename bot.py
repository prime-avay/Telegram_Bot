import os
import sqlite3
import logging
import threading
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters

# ---------------- WEB SERVER FOR UPTIME ----------------
flask_app = Flask(__name__)
@flask_app.route('/')
def index(): return "Prime Avay Bot is Online!", 200

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    flask_app.run(host='0.0.0.0', port=port)

# ---------------- CONFIG ----------------
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 5832196298 # সরাসরি আপনার আইডি

INSTAGRAM_URL = "https://www.instagram.com/prime_avay"
YT_URL = "https://youtube.com/@prime_avay"
WHATSAPP_URL = "https://whatsapp.com/channel/0029Vb6m4r60QeakFUmaSO3p"
TELEGRAM_URL = "https://t.me/+80I0Jqq_9Hc3NGE9"
APPROVED_LINK = "https://t.me/primeavay"
REQUIRED_APPROVALS = 4

logging.basicConfig(level=logging.INFO)

# ---------------- DATABASE ----------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'bot_data.db')

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, status TEXT, approvals INTEGER DEFAULT 0)')
    conn.commit()
    conn.close()

def get_user(user_id):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT status, approvals FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        conn.close()
        return row if row else ("start", 0)
    except:
        return ("start", 0)

def update_user(user_id, status=None, approvals=None):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    if status is not None and approvals is not None:
        cursor.execute("INSERT OR REPLACE INTO users (user_id, status, approvals) VALUES (?, ?, ?)", (user_id, status, approvals))
    elif status is not None:
        cursor.execute("UPDATE users SET status = ? WHERE user_id = ?", (status, user_id))
    elif approvals is not None:
        cursor.execute("UPDATE users SET approvals = ? WHERE user_id = ?", (approvals, user_id))
    conn.commit()
    conn.close()

# ---------------- HANDLERS ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    status, count = get_user(user_id)
    
    if status == "verified":
        await update.message.reply_text(f"✅ You are already verified!\n🔗 Link: {APPROVED_LINK}")
        return

    progress_bar = "✅" * count + "⏳" * (REQUIRED_APPROVALS - count)

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📷 Follow Instagram", url=INSTAGRAM_URL)],
        [InlineKeyboardButton("🔔 Subscribe YouTube", url=YT_URL)],
        [InlineKeyboardButton("💬 Join WhatsApp Channel", url=WHATSAPP_URL)],
        [InlineKeyboardButton("👥 Join Telegram Group", url=TELEGRAM_URL)],
        [InlineKeyboardButton(f"📸 Submit Screenshot ({count}/{REQUIRED_APPROVALS})", callback_data="submit")]
    ])
    
    welcome_text = (
        f"👋 **Welcome to 𝙋𝙍𝙄𝙈𝙀 𝘼𝙑𝘼𝙔 Verification!**\n\n"
        f"Your Progress: {count}/{REQUIRED_APPROVALS}\n"
        f"Status: {progress_bar}\n\n"
        f"👇 Complete tasks, then press **Submit Screenshot**."
    )
    
    await update.message.reply_text(welcome_text, reply_markup=keyboard, parse_mode="Markdown")

async def submit_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    status, count = get_user(user_id)
    
    # স্ট্যাটাস আপডেট নিশ্চিত করা
    update_user(user_id, status="pending_submission")
    
    await query.message.reply_text(f"📸 Please send the screenshot for **Step {count + 1}** now:")

async def receive_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    status, count = get_user(user.id)
    
    # যদি ডাটাবেস থেকে স্ট্যাটাস মিস হয়, আমরা সরাসরি চেক করব
    if status != "pending_submission":
        # ইউজারকে আবার সুযোগ দেওয়া
        update_user(user.id, status="pending_submission")
        await update.message.reply_text("⚠️ Verification mode was off. I've turned it on. **Please send the screenshot again.**")
        return
    
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Approve", callback_data=f"appr_{user.id}"),
        InlineKeyboardButton("❌ Reject", callback_data=f"rejt_{user.id}")
    ]])
    
    try:
        await context.bot.send_photo(
            chat_id=ADMIN_ID, 
            photo=update.message.photo[-1].file_id, 
            caption=f"📝 User: @{user.username}\n🆔 ID: {user.id}\n📍 Verifying Step: {count + 1}/{REQUIRED_APPROVALS}", 
            reply_markup=keyboard
        )
        # ছবি পাঠানোর পর স্ট্যাটাস 'awaiting_review' করে দেওয়া যাতে বারবার একই ছবি না পাঠাতে পারে
        update_user(user.id, status="awaiting_review")
        await update.message.reply_text(f"✅ Step {count + 1} screenshot sent to Admin! Please wait.")
    except Exception as e:
        await update.message.reply_text("❌ Admin not found. Please make sure @prime_avay has started the bot.")

async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.from_user.id != ADMIN_ID: return
    
    action, user_id = query.data.split("_")
    user_id = int(user_id)
    _, count = get_user(user_id)

    if action == "appr":
        new_count = count + 1
        if new_count >= REQUIRED_APPROVALS:
            update_user(user_id, status="verified", approvals=new_count)
            await context.bot.send_message(user_id, f"🎉 Verified!\n🔗 Link: {APPROVED_LINK}")
            await query.edit_message_caption(f"✅ VERIFIED (4/4)")
        else:
            update_user(user_id, status="start", approvals=new_count)
            await context.bot.send_message(user_id, f"✅ Step {new_count} approved! Press 'Submit' for the next one.")
            await query.edit_message_caption(f"🟢 Approved {new_count}/4")
    
    elif action == "rejt":
        update_user(user_id, status="start")
        await context.bot.send_message(user_id, f"❌ Step {count + 1} was rejected. Send again.")
        await query.edit_message_caption(f"🔴 Rejected Step {count + 1}")

def main():
    init_db()
    threading.Thread(target=run_flask, daemon=True).start()
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(submit_handler, pattern="^submit$"))
    app.add_handler(MessageHandler(filters.PHOTO, receive_photo))
    app.add_handler(CallbackQueryHandler(admin_callback, pattern="^(appr|rejt)_"))
    app.run_polling()

if __name__ == "__main__":
    main()
