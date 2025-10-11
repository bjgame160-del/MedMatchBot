# medmatchbot.py
# MedMatchBot - Telegram bot with 3-star verification and photo upload
# Reads BOT_TOKEN and ADMIN_ID from environment variables.

import os
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, filters,
    ContextTypes, CallbackQueryHandler
)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))

if not BOT_TOKEN or ADMIN_ID == 0:
    raise RuntimeError("BOT_TOKEN and ADMIN_ID must be set as environment variables")

# ----------------- Database Setup -----------------
conn = sqlite3.connect("medmatchbot.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    name TEXT,
    gender TEXT,
    year TEXT,
    state TEXT,
    likes TEXT,
    dislikes TEXT,
    looking_for TEXT,
    bio TEXT,
    insta TEXT,
    insta_visible INTEGER DEFAULT -1,
    star INTEGER DEFAULT 0,
    selfie_uploaded INTEGER DEFAULT 0,
    selfie_verified INTEGER DEFAULT 0
)
''')
conn.commit()

# ----------------- Helper Functions -----------------
def get_user(user_id):
    cursor.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    return cursor.fetchone()

def update_star(user_id):
    user = get_user(user_id)
    if not user:
        return
    # indices:
    # 0 user_id,1 name,2 gender,3 year,4 state,5 likes,6 dislikes,7 looking_for,8 bio,
    # 9 insta,10 insta_visible,11 star,12 selfie_uploaded,13 selfie_verified
    star = 0
    # profile filled?
    profile_filled = all(user[i] and str(user[i]).strip() != "" for i in range(1,9))
    if profile_filled:
        star = 1
    insta_provided = user[9] and str(user[9]).strip() != ""
    if insta_provided:
        star = 2
    if user[13] == 1:
        star = 3
    cursor.execute("UPDATE users SET star=? WHERE user_id=?", (star, user_id))
    conn.commit()

def get_star_text(star):
    return {0: "⚪ Unverified", 1: "⭐ 1 Star - Profile Completed", 2: "⭐⭐ 2 Stars - Instagram Provided", 3: "⭐⭐⭐ 3 Stars - Fully Verified"}.get(star, "⚪ Unverified")

def ensure_user_row(user_id):
    if not get_user(user_id):
        cursor.execute("INSERT INTO users (user_id) VALUES (?)", (user_id,))
        conn.commit()

# ----------------- Commands / Handlers -----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    ensure_user_row(user_id)
    await update.message.reply_text("Welcome to MedMatchBot! Let's create your profile.\nWhat's your full name?")
    return

async def profile_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)
    if not user:
        await update.message.reply_text("You have no profile yet. Send /start to create one.")
        return
    insta_display = "Hidden"
    if user[9] and user[10] == 1:
        insta_display = user[9]
    text = (
        f"👤 Name: {user[1] or '-'}\n"
        f"Gender: {user[2] or '-'}\n"
        f"Year: {user[3] or '-'}\n"
        f"State: {user[4] or '-'}\n"
        f"Likes: {user[5] or '-'}\n"
        f"Dislikes: {user[6] or '-'}\n"
        f"Looking for: {user[7] or '-'}\n"
        f"Bio: {user[8] or '-'}\n"
        f"Instagram: {insta_display}\n"
        f"Verification: {get_star_text(user[11])}"
    )
    await update.message.reply_text(text)

# Message flow: fill fields one by one based on which is empty
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message is None or update.message.text is None:
        return
    user_id = update.effective_user.id
    ensure_user_row(user_id)
    user = get_user(user_id)
    text = update.message.text.strip()
    # 1: name
    if not user[1] or user[1].strip() == "":
        cursor.execute("UPDATE users SET name=? WHERE user_id=?", (text, user_id))
        conn.commit()
        await update.message.reply_text("Gender? (Male/Female/Other)")
        return
    # 2: gender
    if not user[2] or user[2].strip() == "":
        cursor.execute("UPDATE users SET gender=? WHERE user_id=?", (text, user_id))
        conn.commit()
        await update.message.reply_text("Your Year? (1st/2nd/3rd/Final/Intern)")
        return
    # 3: year
    if not user[3] or user[3].strip() == "":
        cursor.execute("UPDATE users SET year=? WHERE user_id=?", (text, user_id))
        conn.commit()
        await update.message.reply_text("Which state is your college in?")
        return
    # 4: state
    if not user[4] or user[4].strip() == "":
        cursor.execute("UPDATE users SET state=? WHERE user_id=?", (text, user_id))
        conn.commit()
        await update.message.reply_text("Which subjects do you like? (comma separated)")
        return
    # 5: likes
    if not user[5] or user[5].strip() == "":
        cursor.execute("UPDATE users SET likes=? WHERE user_id=?", (text, user_id))
        conn.commit()
        await update.message.reply_text("Which subjects do you dislike? (comma separated)")
        return
    # 6: dislikes
    if not user[6] or user[6].strip() == "":
        cursor.execute("UPDATE users SET dislikes=? WHERE user_id=?", (text, user_id))
        conn.commit()
        await update.message.reply_text("What are you looking for? (Friendship / Relationship / Study partner)")
        return
    # 7: looking_for
    if not user[7] or user[7].strip() == "":
        cursor.execute("UPDATE users SET looking_for=? WHERE user_id=?", (text, user_id))
        conn.commit()
        await update.message.reply_text("Write a short bio about yourself")
        return
    # 8: bio
    if not user[8] or user[8].strip() == "":
        cursor.execute("UPDATE users SET bio=? WHERE user_id=?", (text, user_id))
        conn.commit()
        await update.message.reply_text("Optional: Enter your Instagram username (for verification). Type 'skip' to skip.")
        return
    # 9: insta (optional)
    if not user[9] or str(user[9]).strip() == "":
        if text.lower() == "skip":
            cursor.execute("UPDATE users SET insta=? WHERE user_id=?", ("", user_id))
            conn.commit()
            update_star(user_id)
            await update.message.reply_text(f"Profile completed! {get_star_text(get_user(user_id)[11])}\nYou need at least 2 stars to find matches.")
            return
        # save insta and ask visibility
        insta_text = text
        cursor.execute("UPDATE users SET insta=? WHERE user_id=?", (insta_text, user_id))
        cursor.execute("UPDATE users SET insta_visible=? WHERE user_id=?", (-1, user_id))
        conn.commit()
        await update.message.reply_text("Do you want your Instagram username visible to matches? (Yes/No)")
        return
    # 10: insta_visible (was -1 when asked)
    if user[10] == -1:
        visible = 1 if text.lower() in ("yes","y") else 0
        cursor.execute("UPDATE users SET insta_visible=? WHERE user_id=?", (visible, user_id))
        conn.commit()
        update_star(user_id)
        await update.message.reply_text(f"Profile completed! {get_star_text(get_user(user_id)[11])}\nYou need at least 2 stars to find matches.")
        return

    # If all done
    await update.message.reply_text("Your profile is already completed. Use /profile to view it or /findmatch to search.")

# Photo handler: forward image to admin for manual verification
async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    ensure_user_row(user_id)
    user = get_user(user_id)
    if not user:
        await update.message.reply_text("Please register first using /start.")
        return
    if not update.message.photo:
        await update.message.reply_text("Please send a photo (selfie or college ID).")
        return
    file_id = update.message.photo[-1].file_id
    caption = f"Photo from user {user_id} ({user[1] or 'NoName'}). Use /verify {user_id} to approve or /unverify {user_id} to reject."
    # Forward to admin chat
    await context.bot.send_photo(chat_id=ADMIN_ID, photo=file_id, caption=caption)
    # mark selfie uploaded
    cursor.execute("UPDATE users SET selfie_uploaded=1 WHERE user_id=?", (user_id,))
    conn.commit()
    await update.message.reply_text("Your photo has been sent to admin for verification. ✅")

# ----------------- Matching -----------------
# NOTE: likes stored in-memory (resets on restart). For production store in DB.
likes = {}  # {liker_id: set(target_ids)}

async def find_match(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)
    if not user or user[11] < 2:
        await update.message.reply_text("You need at least 2 stars to start finding matches.")
        return
    if user[11] == 2:
        cursor.execute("SELECT user_id, name, gender, year, state, likes, dislikes, looking_for, bio, star FROM users WHERE user_id != ? AND star=2", (user_id,))
    else:  # star 3 can see star 2 or 3
        cursor.execute("SELECT user_id, name, gender, year, state, likes, dislikes, looking_for, bio, star FROM users WHERE user_id != ? AND star>=2", (user_id,))
    matches = cursor.fetchall()
    if not matches:
        await update.message.reply_text("No matches available currently.")
        return
    # show first match
    match = matches[0]
    mid = match[0]
    keyboard = [
        [InlineKeyboardButton("❤️ Like", callback_data=f"like_{mid}"),
         InlineKeyboardButton("❌ Skip", callback_data=f"skip_{mid}")]
    ]
    text = (
        f"👤 Name: {match[1]}\nGender: {match[2]}\nYear: {match[3]}\nState: {match[4]}\n"
        f"Likes: {match[5]}\nDislikes: {match[6]}\nLooking for: {match[7]}\nBio: {match[8]}\n"
        f"Verification: {get_star_text(match[9])}"
    )
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id
    action, target_id = data.split("_")
    target_id = int(target_id)
    if action == "like":
        likes.setdefault(user_id, set()).add(target_id)
        # check if mutual
        if user_id in likes.get(target_id, set()):
            await query.edit_message_text("🎉 It's a match! You both liked each other.")
            # optionally send both users each other's Telegram username? We cannot share private info — let users chat manually.
            await context.bot.send_message(chat_id=target_id, text=f"You matched with user {user_id} — open profile with /profile.")
        else:
            await query.edit_message_text("You liked this user ✅")
    elif action == "skip":
        await query.edit_message_text("Skipped ❌")

# ----------------- Admin Commands (restricted) -----------------
def is_admin(user_id):
    return user_id == ADMIN_ID

async def check_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("Unauthorized - admin only.")
        return
    if not context.args:
        await update.message.reply_text("Usage: /check <user_id>")
        return
    target_id = int(context.args[0])
    user = get_user(target_id)
    if not user:
        await update.message.reply_text("User not found.")
        return
    await update.message.reply_text(f"User ID: {target_id}\nInstagram (private): {user[9]}\nSelfie uploaded: {bool(user[12])}\nStar: {get_star_text(user[11])}")

async def verify_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("Unauthorized - admin only.")
        return
    if not context.args:
        await update.message.reply_text("Usage: /verify <user_id>")
        return
    target_id = int(context.args[0])
    cursor.execute("UPDATE users SET selfie_verified=1 WHERE user_id=?", (target_id,))
    conn.commit()
    update_star(target_id)
    await update.message.reply_text(f"User {target_id} is now fully verified ⭐⭐⭐")

async def unverify_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("Unauthorized - admin only.")
        return
    if not context.args:
        await update.message.reply_text("Usage: /unverify <user_id>")
        return
    target_id = int(context.args[0])
    cursor.execute("UPDATE users SET selfie_verified=0 WHERE user_id=?", (target_id,))
    conn.commit()
    update_star(target_id)
    await update.message.reply_text(f"User {target_id} verification removed.")

async def list_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("Unauthorized - admin only.")
        return
    cursor.execute("SELECT user_id, name, star FROM users")
    rows = cursor.fetchall()
    if not rows:
        await update.message.reply_text("No users yet.")
        return
    text = "\n".join([f"{r[0]} - {r[1] or '-'} - {get_star_text(r[2])}" for r in rows])
    await update.message.reply_text(text)

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "/start - create or update profile\n"
        "/profile - view your profile\n"
        "/findmatch - find matches (requires at least 2 stars)\n"
        "To upload selfie/ID: simply send a PHOTO to the bot\n\n"
        "Admin commands: /check, /verify, /unverify, /list (admin only)"
    )
    await update.message.reply_text(text)

# ----------------- Main -----------------
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("profile", profile_cmd))
    app.add_handler(CommandHandler("findmatch", find_match))
    app.add_handler(CommandHandler("check", check_user))
    app.add_handler(CommandHandler("verify", verify_user))
    app.add_handler(CommandHandler("unverify", unverify_user))
    app.add_handler(CommandHandler("list", list_users))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(MessageHandler(filters.PHOTO, photo_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    app.add_handler(CallbackQueryHandler(button_handler))
    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
