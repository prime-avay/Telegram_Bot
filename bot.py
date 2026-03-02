import os
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

# Logging setup
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# ---------------- CONFIG ----------------
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

INSTAGRAM_URL = "https://www.instagram.com/prime_avay"
YT_URL = "https://www.youtube.com/@prime_avay"
WHATSAPP_URL = "https://whatsapp.com/channel/0029Vb6m4r60QeakFUmaSO3p"
TELEGRAM_URL = "https://t.me/+80I0Jqq_9Hc3NGE9"

APPROVED_LINK = "https://t.me/primeavay"
REQUIRED_APPROVALS = 4
# ----------------------------------------

# Storage (Temporary)
submitted_users = set()
approval_count = {}
completed_users = set()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📷 Follow Instagram", url=INSTAGRAM_URL)],
        [InlineKeyboardButton("🔔 Subscribe YouTube", url=YT_URL)],
        [InlineKeyboardButton("💬 Join WhatsApp Group", url=WHATSAPP_URL)],
        [InlineKeyboardButton("👥 Group Chat", url=TELEGRAM_URL)],
        [InlineKeyboardButton("📸 Submit Screenshot", callback_data="submit")]
    ])
    await update.message.reply_text(
        "👋 Welcome! Complete 4 tasks and submit screenshots to get the link.\n\n"
        "Press 'Submit Screenshot' before sending each photo.",
        reply_markup=keyboard
    )

async def submit_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if user_id in completed_users:
        await query.message.reply_text("✅ Verification already complete!")
        return

    submitted_users.add(user_id)
    approval_count.setdefault(user_id, 0)
    await query.message.reply_text("📸 Now send your screenshot (as a photo).")

async def receive_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id

    if user_id not in submitted_users:
        await update.message.reply_text("❌ Please click 'Submit Screenshot' first.")
        return

    # Store user's original message ID for rejection reference
    photo_file_id = update.message.photo[-1].file_id
    original_msg_id = update.message.message_id

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Approve", callback_data=f"app_{user_id}"),
            # Rejection callback now includes the message ID to reply back to the user
            InlineKeyboardButton("❌ Reject", callback_data=f"rej_{user_id}_{original_msg_id}")
        ]
    ])

    await context.bot.send_photo(
        chat_id=ADMIN_ID,
        photo=photo_file_id,
        caption=(
            f"👤 User: @{user.username}\n"
            f"🆔 ID: {user_id}\n"
            f"📈 Progress: {approval_count[user_id]}/{REQUIRED_APPROVALS}"
        ),
        parse_mode="Markdown",
        reply_markup=keyboard
    )
    await update.message.reply_text("✅ Received! Admin is checking...")

async def admin_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.from_user.id != ADMIN_ID: return

    data = query.data.split("_")
    action = data[0]
    user_id = int(data[1])

    if action == "app":
        approval_count[user_id] += 1
        count = approval_count[user_id]

        if count >= REQUIRED_APPROVALS:
            await context.bot.send_message(user_id, f"🎉 Verified! Your Link: {APPROVED_LINK}")
            completed_users.add(user_id)
            await query.edit_message_caption(f"✅ Full Approved ({REQUIRED_APPROVALS}/{REQUIRED_APPROVALS})")
        else:
            await query.edit_message_caption(f"✅ Approved ({count}/{REQUIRED_APPROVALS})")
    
    elif action == "rej":
        msg_id = int(data[2])
        # Sends a reply to the specific rejected screenshot
        await context.bot.send_message(
            chat_id=user_id,
            text="❌ This screenshot was rejected. Please send a valid one.",
            reply_to_message_id=msg_id
        )
        await query.edit_message_caption("❌ Rejected and User Notified")

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(submit_handler, pattern="^submit$"))
    app.add_handler(MessageHandler(filters.PHOTO, receive_photo))
    app.add_handler(CallbackQueryHandler(admin_action, pattern="^(app|rej)_"))
    app.run_polling()

if __name__ == "__main__":

    main()
