import logging
import os
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)
from flask import Flask

# --- Keep Render alive by opening a web port ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running fine!"

# --- Telegram Bot Setup ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# --- Steps in registration ---
NAME, GENDER, YEAR, STATE, LIKES, DISLIKES, INSTAGRAM, PHOTO = range(8)

# --- Your Telegram ID (admin) ---
ADMIN_CHAT_ID = 6371731528

# --- Start command ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome to the MatchMate Bot!\n\n"
        "Let's set up your profile.\n\n"
        "Please tell me your *name*.",
        parse_mode="Markdown"
    )
    return NAME


async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["name"] = update.message.text
    await update.message.reply_text(
        "🚻 Please select your gender:",
        reply_markup=ReplyKeyboardMarkup([["Male", "Female"]], one_time_keyboard=True)
    )
    return GENDER


async def get_gender(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["gender"] = update.message.text
    await update.message.reply_text("🎓 Enter your college year (e.g. 1st, 2nd, 3rd, 4th):")
    return YEAR


async def get_year(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["year"] = update.message.text
    await update.message.reply_text("📍 Enter your *state* name:", parse_mode="Markdown")
    return STATE


async def get_state(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["state"] = update.message.text
    await update.message.reply_text("💬 Tell me a few of your *likes*:", parse_mode="Markdown")
    return LIKES


async def get_likes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["likes"] = update.message.text
    await update.message.reply_text("🚫 Now tell me some of your *dislikes*:", parse_mode="Markdown")
    return DISLIKES


async def get_dislikes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["dislikes"] = update.message.text
    await update.message.reply_text(
        "📱 Share your *Instagram ID* (or type 'none' if you don’t want to):",
        parse_mode="Markdown"
    )
    return INSTAGRAM


async def get_instagram(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["instagram"] = update.message.text
    await update.message.reply_text(
        "📸 Please upload a *selfie* for verification.\n\n"
        "Users who upload a selfie get a ⭐⭐⭐ (3-star) verified profile!",
        parse_mode="Markdown"
    )
    return PHOTO


async def get_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["photo_uploaded"] = True

    await update.message.reply_text("✅ Registration complete! You now have a ⭐⭐⭐ verified profile!")

    # Send user info to admin
    msg = (
        f"🆕 *New Registration*\n\n"
        f"👤 Name: {context.user_data.get('name')}\n"
        f"🚻 Gender: {context.user_data.get('gender')}\n"
        f"🎓 Year: {context.user_data.get('year')}\n"
        f"📍 State: {context.user_data.get('state')}\n"
        f"💬 Likes: {context.user_data.get('likes')}\n"
        f"🚫 Dislikes: {context.user_data.get('dislikes')}\n"
        f"📱 Instagram: {context.user_data.get('instagram')}\n"
        f"📸 Photo: Uploaded ✅"
    )

    await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=msg, parse_mode="Markdown")

    if update.message.photo:
        file_id = update.message.photo[-1].file_id
        await context.bot.send_photo(chat_id=ADMIN_CHAT_ID, photo=file_id, caption=f"Selfie of {context.user_data.get('name')}")

    return ConversationHandler.END


async def skip_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["photo_uploaded"] = False
    await update.message.reply_text("✅ Registration complete! You now have a ⭐⭐ (2-star) profile.")

    msg = (
        f"🆕 *New Registration*\n\n"
        f"👤 Name: {context.user_data.get('name')}\n"
        f"🚻 Gender: {context.user_data.get('gender')}\n"
        f"🎓 Year: {context.user_data.get('year')}\n"
        f"📍 State: {context.user_data.get('state')}\n"
        f"💬 Likes: {context.user_data.get('likes')}\n"
        f"🚫 Dislikes: {context.user_data.get('dislikes')}\n"
        f"📱 Instagram: {context.user_data.get('instagram')}\n"
        f"📸 Photo: Not uploaded ❌"
    )

    await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=msg, parse_mode="Markdown")
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Registration cancelled.")
    return ConversationHandler.END


def main():
    TOKEN = os.getenv("BOT_TOKEN")  # Get bot token from environment variable
    if not TOKEN:
        print("❌ BOT_TOKEN not set in environment variables.")
        return

    application = ApplicationBuilder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            GENDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_gender)],
            YEAR: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_year)],
            STATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_state)],
            LIKES: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_likes)],
            DISLIKES: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_dislikes)],
            INSTAGRAM: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_instagram)],
            PHOTO: [
                MessageHandler(filters.PHOTO, get_photo),
                CommandHandler("skip", skip_photo),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(conv_handler)
    application.run_polling(stop_signals=None)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
    main()
