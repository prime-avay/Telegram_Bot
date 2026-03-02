import os
import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters
)

# Logging setup for debugging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
    level=logging.INFO
)

# ---------------- CONFIG (Environment Variables) ----------------
# Render-এর Environment Settings থেকে এই মানগুলো নেওয়া হবে
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

# Social Media Links
INSTAGRAM_URL = "https://www.instagram.com/prime_avay"
YT_URL = "https://www.youtube.com/@prime_avay"
WHATSAPP_URL = "https://whatsapp.com/channel/0029Vb6m4r60QeakFUmaSO3p"
TELEGRAM_URL = "https://t.me/+80I0Jqq_9Hc3NGE9"

APPROVED_LINK = "https://t.me/primeavay"
REQUIRED_APPROVALS = 4
# ---------------------------------------------------------------

# Temporary In-memory Storage
submitted_users = set()
approval_count = {}
completed_users = set()

# --- Command: /start ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📷 Follow Instagram", url=INSTAGRAM_URL)],
        [InlineKeyboardButton("🔔 Subscribe YouTube", url=YT_URL)],
        [InlineKeyboardButton("💬 Join WhatsApp Group", url=WHATSAPP_URL)],
        [InlineKeyboardButton("👥 Group Chat", url=TELEGRAM_URL)],
        [InlineKeyboardButton("📸 Submit Screenshot", callback_data="submit")]
    ])
    
    await update.message.reply_text(
        "👋 Welcome! To get the exclusive link, please complete all 4 tasks above.\n\n"
        "After completing, click the 'Submit Screenshot' button and send your proof.",
        reply_markup=keyboard
    )

# --- Callback: Submit Button ---
async def submit_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if user_id in completed_users:
        await query.message.reply_text("✅ You are already verified! Enjoy the link.")
        return

    submitted_users.add(user_id)
    approval_count.setdefault(user_id, 0)
    await query.message.reply_text("📸 Please send your screenshot now (as a photo).")

# --- Handler: Receive Photo ---
async def receive_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id

    if user_id not in submitted_users:
        await update.message.reply_text("❌ Please click the 'Submit Screenshot' button first.")
        return

    photo_file_id = update.message.photo[-1].file_id
    original_msg_id = update.message.message_id

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Approve", callback_data=f"app_{user_id}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"rej_{user_id}_{original_msg_id}")
        ]
    ])

    try:
        await context.bot.send_photo(
            chat_id=ADMIN_ID,
            photo=photo_file_id,
            caption=(
                f"🚨 *New Verification Request*\n\n"
                f"👤 User: @{user.username}\n"
                f"🆔 ID: `{user_id}`\n"
                f"📈 Progress: {approval_count.get(user_id, 0)}/{REQUIRED_APPROVALS}"
            ),
            parse_mode="Markdown",
            reply_markup=keyboard
        )
        await update.message.reply_text("✅ Received! Please wait for admin approval.")
    except Exception as e:
        logging.error(f"Error sending to admin: {e}")
        await update.message.reply_text("⚠️ Admin notification failed. Check ADMIN_ID.")

# --- Callback: Admin Action (Approve/Reject) ---
async def admin_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.from_user.id != ADMIN_ID:
        await query.answer("Unauthorized!", show_alert=True)
        return

    data = query.data.split("_")
    action = data[0]
    user_id = int(data[1])

    if action == "app":
        approval_count[user_id] = approval_count.get(user_id, 0) + 1
        count = approval_count[user_id]

        if count >= REQUIRED_APPROVALS:
            await context.bot.send_message(user_id, f"🎉 Verified! Your Link: {APPROVED_LINK}")
            completed_users.add(user_id)
            await query.edit_message_caption(f"✅ Full Approved ({REQUIRED_APPROVALS}/{REQUIRED_APPROVALS})")
        else:
            await query.edit_message_caption(f"✅ Approved ({count}/{REQUIRED_APPROVALS})")
    
    elif action == "rej":
        msg_id = int(data[2])
        # Specific rejection notification
        await context.bot.send_message(
            chat_id=user_id,
            text="❌ This screenshot was rejected. Please send a valid one.",
            reply_to_message_id=msg_id
        )
        await query.edit_message_caption("❌ Rejected & User Notified")

# --- Main Async Runner for Python 3.11+ ---
async def main():
    if not BOT_TOKEN:
        logging.error("BOT_TOKEN not found!")
        return

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(submit_handler, pattern="^submit$"))
    app.add_handler(MessageHandler(filters.PHOTO, receive_photo))
    app.add_handler(CallbackQueryHandler(admin_action, pattern="^(app|rej)_"))

    # Proper Startup for Modern Python Environment
    async with app:
        await app.initialize()
        await app.start()
        await app.updater.start_polling()
        logging.info("Bot is running...")
        await asyncio.Event().wait()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot stopped.")
