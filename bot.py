import os
import sqlite3
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters
)

# ---------------- CONFIG (Hidden via Environment Variables) ----------------
# Render-এর Environment Variables থেকে এই মানগুলো আসবে
BOT_TOKEN = os.getenv("BOT_TOKEN")
# ADMIN_ID স্ট্রিং হিসেবে আসে, তাই এটিকে integer-এ রূপান্তর করতে হবে
ADMIN_ID = int(os.getenv("ADMIN_ID")) if os.getenv("ADMIN_ID") else None

INSTAGRAM_URL = "https://www.instagram.com/prime_avay"
YT_URL = "https://youtube.com/@prime_avay"
WHATSAPP_URL = "https://whatsapp.com/channel/0029Vb6m4r60QeakFUmaSO3p"
TELEGRAM_URL = "https://t.me/+80I0Jqq_9Hc3NGE9"
APPROVED_LINK = "https://t.me/primeavay"
REQUIRED_APPROVALS = 4

# Logging setup
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# ---------------- DATABASE SETUP ----------------
def init_db():
    conn = sqlite3.connect('bot_data.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users 
                      (user_id INTEGER PRIMARY KEY, status TEXT, approvals INTEGER DEFAULT 0)''')
    conn.commit()
    conn.close()

def update_user(user_id, status=None, approvals=None):
    conn = sqlite3.connect('bot_data.db')
    cursor = conn.cursor()
    if status is not None and approvals is not None:
        cursor.execute("INSERT OR REPLACE INTO users (user_id, status, approvals) VALUES (?, ?, ?)", (user_id, status, approvals))
    elif status is not None:
        cursor.execute("UPDATE users SET status = ? WHERE user_id = ?", (status, user_id))
    elif approvals is not None:
        cursor.execute("UPDATE users SET approvals = ? WHERE user_id = ?", (approvals, user_id))
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = sqlite3.connect('bot_data.db')
    cursor = conn.cursor()
    cursor.execute("SELECT status, approvals FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row if row else ("start", 0)

# ---------------- HANDLERS ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status, _ = get_user(update.effective_user.id)
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📷 Follow Instagram", url=INSTAGRAM_URL)],
        [InlineKeyboardButton("🔔 Subscribe YouTube", url=YT_URL)],
        [InlineKeyboardButton("💬 Join WhatsApp", url=WHATSAPP_URL)],
        [InlineKeyboardButton("👥 Group Chat", url=TELEGRAM_URL)],
        [InlineKeyboardButton("📸 Submit Screenshot", callback_data="submit")]
    ])

    text = "👋 Welcome to 𝑷𝑹𝑰𝑴𝑬 𝑨𝑽𝑨𝒀 一☪ Verification!\n\n👇 Complete all tasks above, then press Submit Screenshot..!!"
    if status == "verified":
        text = f"✅ You are already verified!\nAccess Link: {APPROVED_LINK}"
    
    await update.message.reply_text(text, reply_markup=keyboard)

async def submit_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    status, _ = get_user(user_id)

    if status == "verified":
        await query.answer("Already verified!", show_alert=True)
        return

    update_user(user_id, status="pending_submission", approvals=0)
    await query.edit_message_text("📸 Now send a screenshot of your task completion (as a photo).")

async def receive_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    status, count = get_user(user.id)

    if status != "pending_submission":
        await update.message.reply_text("❌ Please click 'Submit Screenshot' first.")
        return

    if not ADMIN_ID:
        await update.message.reply_text("⚠️ Admin is not configured. Contact support.")
        return

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Approve", callback_data=f"appr_{user.id}"),
         InlineKeyboardButton("❌ Reject", callback_data=f"rejt_{user.id}")]
    ])

    await context.bot.send_photo(
        chat_id=ADMIN_ID,
        photo=update.message.photo[-1].file_id,
        caption=f"📝 Verification Request\n👤 User: @{user.username}\n🆔 ID: {user.id}\n📈 Progress: {count}/{REQUIRED_APPROVALS}",
        reply_markup=keyboard
    )
    await update.message.reply_text("✅ Screenshot sent! Admin will review it.")

async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.from_user.id != ADMIN_ID: return
    
    data = query.data.split("_")
    action, user_id = data[0], int(data[1])
    status, count = get_user(user_id)

    if action == "appr":
        new_count = count + 1
        if new_count >= REQUIRED_APPROVALS:
            update_user(user_id, status="verified", approvals=new_count)
            await context.bot.send_message(user_id, f"🎉 Congratulations! You are verified.\n🔗 Link: {APPROVED_LINK}")
            await query.edit_message_caption(f"✅ Full Approved ({new_count}/{REQUIRED_APPROVALS})")
        else:
            update_user(user_id, status="pending_submission", approvals=new_count)
            await query.edit_message_caption(f"🟡 Approved ({new_count}/{REQUIRED_APPROVALS})")
            await context.bot.send_message(user_id, f"✅ Step {new_count} approved! Send the next screenshot.")
    
    elif action == "rejt":
        update_user(user_id, status="start", approvals=0)
        await query.edit_message_caption("❌ Rejected")
        await context.bot.send_message(user_id, "❌ Verification rejected. Please try again from the start.")

def main():
    if not BOT_TOKEN:
        print("Error: BOT_TOKEN not found in environment variables!")
        return

    init_db()
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(submit_handler, pattern="^submit$"))
    app.add_handler(MessageHandler(filters.PHOTO, receive_photo))
    app.add_handler(CallbackQueryHandler(admin_callback, pattern="^(appr|rejt)_"))
    
    print("Prime Avay Verification Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()