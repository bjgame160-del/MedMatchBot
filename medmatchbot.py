import os
import sqlite3
import json
import random
import time
import logging
from flask import Flask, request
import telebot
from telebot import types

logging.basicConfig(level=logging.INFO)

# --- Configuration ---

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    logging.error("BOT_TOKEN environment variable is not set. Exiting.")
    raise SystemExit("BOT_TOKEN not set")

ADMIN_ID = int(os.getenv("ADMIN_ID", "6371731528"))
bot = telebot.TeleBot(BOT_TOKEN, parse_mode=None)

# Channel details
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME", "@medicosssssssss")  # for get_chat_member
CHANNEL_LINK = os.getenv("CHANNEL_LINK", "https://t.me/medicosssssssss")  # for clickable link in messages

# Optional webhook URL (if you deploy with webhooks)
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # e.g. https://your-app.onrender.com/

# --- Database ---

DB_PATH = "users.db"

ALLOWED_FIELDS = {
    'name', 'gender', 'state', 'year', 'likes', 'dislikes',
    'instagram', 'show_insta', 'photo_id', 'stars', 'liked_users'
}


def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        name TEXT,
        gender TEXT,
        state TEXT,
        year TEXT,
        likes TEXT,
        dislikes TEXT,
        instagram TEXT,
        show_insta INTEGER DEFAULT 0,
        photo_id TEXT,
        stars INTEGER DEFAULT 0,
        liked_users TEXT DEFAULT '[]'
    )''')
    conn.commit()
    conn.close()


init_db()

# --- Helper DB functions ---

def create_user_if_not_exists(user_id, first_name=None):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users (user_id, name) VALUES (?, ?)", (user_id, first_name or ""))
    conn.commit()
    conn.close()


def save_user_data(user_id, field, value):
    if field not in ALLOWED_FIELDS:
        raise ValueError(f"Field '{field}' is not allowed to be saved.")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    if field in ('show_insta', 'stars'):
        try:
            value = int(value)
        except Exception:
            value = 0

    if field == 'liked_users':
        if isinstance(value, (list, set)):
            value = json.dumps(list(value))
        elif isinstance(value, str):
            pass

    c.execute(f"UPDATE users SET {field} = ? WHERE user_id = ?", (value, user_id))
    conn.commit()
    conn.close()


def get_user(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row


# --- Utilities ---

SESSIONS = {}  # ephemeral runtime data (chat_partner, temporary fields)


def is_user_in_channel(user_id):
    try:
        member = bot.get_chat_member(CHANNEL_USERNAME, user_id)
        logging.info(f"get_chat_member returned: {member.status}")
        return member.status in ['member', 'administrator', 'creator']
    except Exception as e:
        logging.warning(f"Error checking channel membership for {user_id}: {e}")
        return False


def get_liked_set_from_row(user_row):
    if not user_row:
        return set()
    s = user_row[11] or '[]'
    try:
        lst = json.loads(s)
        return set(str(x) for x in lst)
    except Exception:
        return set()


def save_liked_set(user_id, liked_set):
    if not isinstance(liked_set, (set, list)):
        raise ValueError("liked_set must be set or list")
    s = json.dumps(list(liked_set))
    save_user_data(user_id, 'liked_users', s)


def profile_text_from_row(row):
    if not row:
        return "No profile."
    name = row[1] or "-"
    gender = row[2] or "-"
    state = row[3] or "-"
    year = row[4] or "-"
    likes = row[5] or "-"
    dislikes = row[6] or "-"
    try:
        stars = int(row[10])
    except Exception:
        stars = 0
    star_text = "⭐" * stars if stars > 0 else "⚪ Unverified"

    text = (
        f"👤 Name: {name}\n"
        f"⚧ Gender: {gender}\n"
        f"🎓 Year: {year}\n"
        f"📍 State: {state}\n"
        f"❤️ Likes: {likes}\n"
        f"💔 Dislikes: {dislikes}\n"
        f"🔒 Verification: {star_text}\n"
    )
    return text


def is_eligible(seeker_row, candidate_row):
    if not seeker_row or not candidate_row:
        return False
    seeker_id = seeker_row[0]
    cand_id = candidate_row[0]
    if seeker_id == cand_id:
        return False

    s_gender = (seeker_row[2] or '').strip().lower()
    c_gender = (candidate_row[2] or '').strip().lower()
    if s_gender and c_gender and s_gender == c_gender:
        return False

    try:
        seeker_stars = int(seeker_row[10] or 0)
    except Exception:
        seeker_stars = 0
    try:
        cand_stars = int(candidate_row[10] or 0)
    except Exception:
        cand_stars = 0

    if seeker_stars == 1:
        return False
    if seeker_stars == 2 and cand_stars != 2:
        return False
    if seeker_stars == 3 and cand_stars < 2:
        return False
    if cand_stars < 2:
        return False
    return True


def find_candidate_for(user_id):
    seeker = get_user(user_id)
    if not seeker:
        return None
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id != ?", (user_id,))
    rows = c.fetchall()
    conn.close()
    random.shuffle(rows)
    seeker_likes = get_liked_set_from_row(seeker)
    for row in rows:
        if not is_eligible(seeker, row):
            continue
        if str(row[0]) in seeker_likes:
            continue
        return row
    return None


# --- Handlers: Registration ---

@bot.message_handler(commands=['start'])
def start(message):
    chat_id = message.chat.id
    create_user_if_not_exists(chat_id, message.from_user.first_name)

    if not is_user_in_channel(chat_id):
        join_text = (
            "🚨 To use this bot, you must first join our official channel!<br><br>"
            f"👉 <a href='{CHANNEL_LINK}'>Join Here</a><br><br>"
            "After joining, press /start again."
        )
        bot.send_message(chat_id, join_text, parse_mode="HTML", disable_web_page_preview=True)
        return

    bot.send_message(chat_id, "✅ You are verified! Let's continue your registration...")
    bot.send_message(chat_id, "👋 Welcome to MedMatch! Let's create your profile.")
    bot.send_message(chat_id, "What's your name?")
    bot.register_next_step_handler(message, get_name)


def get_name(message):
    user_id = message.chat.id
    create_user_if_not_exists(user_id, message.from_user.first_name)
    save_user_data(user_id, 'name', message.text)
    bot.send_message(user_id, "What's your gender? (Male/Female/Other)")
    bot.register_next_step_handler(message, get_gender)


def get_gender(message):
    user_id = message.chat.id
    save_user_data(user_id, 'gender', message.text)
    bot.send_message(user_id, "In which state is your medical college?")
    bot.register_next_step_handler(message, get_state)


def get_state(message):
    user_id = message.chat.id
    save_user_data(user_id, 'state', message.text)
    bot.send_message(user_id, "Which year are you in? (e.g., 1st year, 2nd year, Internship)")
    bot.register_next_step_handler(message, get_year)


def get_year(message):
    user_id = message.chat.id
    save_user_data(user_id, 'year', message.text)
    bot.send_message(user_id, "Which subjects do you like most?")
    bot.register_next_step_handler(message, get_likes)


def get_likes(message):
    user_id = message.chat.id
    save_user_data(user_id, 'likes', message.text)
    bot.send_message(user_id, "Which subjects do you dislike?")
    bot.register_next_step_handler(message, get_dislikes)


def get_dislikes(message):
    user_id = message.chat.id
    save_user_data(user_id, 'dislikes', message.text)
    save_user_data(user_id, 'stars', 1)

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Enter Instagram Username 📸", "Upload Selfie/College ID 🪪")
    markup.add("Find Match 💞", "View Profile ⭐")

    bot.send_message(user_id, "✅ Basic profile completed! You earned ⭐ (1 Star)", reply_markup=markup)
    bot.send_message(ADMIN_ID, f"🆕 New user registered: {message.from_user.first_name} ({user_id})")


# --- Instagram & Verification ---

@bot.message_handler(func=lambda m: m.text == "Enter Instagram Username 📸")
def ask_insta(message):
    bot.send_message(message.chat.id, "Send your Instagram username (without @):")
    bot.register_next_step_handler(message, save_insta)


def save_insta(message):
    user_id = message.chat.id
    insta = message.text.strip().replace("@", "")
    save_user_data(user_id, 'instagram', insta)

    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("👁 Show Insta to matches", callback_data="show_insta"),
        types.InlineKeyboardButton("🙈 Hide Insta", callback_data="hide_insta")
    )
    bot.send_message(user_id, "Would you like to show your Insta to matches?", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data in ["show_insta", "hide_insta"])
def set_insta_visibility(call):
    user_id = call.from_user.id
    show = 1 if call.data == "show_insta" else 0
    save_user_data(user_id, 'show_insta', show)
    save_user_data(user_id, 'stars', 2)
    bot.answer_callback_query(call.id, "Saved!")
    bot.send_message(user_id, "✅ Instagram saved. You earned ⭐⭐ (2 Stars) and can now find matches.")
    user = get_user(user_id)
    try:
        bot.send_message(ADMIN_ID, f"📸 Insta added: {user[1]} (@{user[7]})")
    except Exception:
        pass


@bot.message_handler(func=lambda m: m.text == "Upload Selfie/College ID 🪪")
def ask_photo(message):
    bot.send_message(message.chat.id, "Please upload your selfie or college ID photo 📸")
    bot.register_next_step_handler(message, save_photo)


def save_photo(message):
    user_id = message.chat.id
    if not message.photo:
        bot.send_message(user_id, "Please send a valid photo.")
        return
    file_id = message.photo[-1].file_id
    save_user_data(user_id, 'photo_id', file_id)
    save_user_data(user_id, 'stars', 3)
    bot.send_message(user_id, "✅ Photo uploaded! You are now ⭐⭐⭐ Fully Verified!")
    bot.send_message(ADMIN_ID, f"🪪 New verification photo from {message.from_user.first_name}")
    try:
        bot.send_photo(ADMIN_ID, file_id)
    except Exception:
        pass


# --- Matching: /findmatch ---

@bot.message_handler(commands=['findmatch'])
def findmatch_cmd(message):
    user_id = message.chat.id
    user_row = get_user(user_id)
    if not user_row:
        bot.send_message(user_id, "You have no profile yet. Use /start to create your profile.")
        return

    stars = int(user_row[10] or 0)
    if stars < 2:
        bot.send_message(user_id, "⚠️ You need at least 2 Stars to find matches. Complete verification to continue.")
        return

    candidate = find_candidate_for(user_id)
    if not candidate:
        bot.send_message(user_id, "No matches found right now. Try again later.")
        return

    candidate_text = profile_text_from_row(candidate)
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(
        types.InlineKeyboardButton("❤️ Like", callback_data=f"like_{candidate[0]}"),
        types.InlineKeyboardButton("❌ Skip", callback_data=f"skip_{candidate[0]}")
    )
    if candidate[7] and int(candidate[8] or 0) == 1:
        candidate_text += f"\n📱 Instagram: @{candidate[7]}"
    bot.send_message(user_id, candidate_text, reply_markup=keyboard)


@bot.callback_query_handler(func=lambda call: call.data and (call.data.startswith("like_") or call.data.startswith("skip_")))
def handle_like_skip(call):
    data = call.data
    user_id = call.from_user.id
    action, target_str = data.split("_", 1)
    try:
        target_id = int(target_str)
    except Exception:
        bot.answer_callback_query(call.id, "Invalid target")
        return

    seeker_row = get_user(user_id)
    target_row = get_user(target_id)
    if not seeker_row or not target_row:
        bot.answer_callback_query(call.id, "User data missing.")
        return

    if action == "skip":
        bot.answer_callback_query(call.id, "Skipped ❌")
        return

    seeker_liked = get_liked_set_from_row(seeker_row)
    seeker_liked.add(str(target_id))
    save_liked_set(user_id, seeker_liked)
    bot.answer_callback_query(call.id, "You liked this profile ✅")

    target_liked = get_liked_set_from_row(target_row)
    if str(user_id) in target_liked:
        bot.send_message(user_id, f"🎉 It's a match with {target_row[1]}! 🎉")
        bot.send_message(target_id, f"🎉 It's a match with {seeker_row[1]}! 🎉")

        s_insta = seeker_row[7] if int(seeker_row[8] or 0) == 1 else None
        t_insta = target_row[7] if int(target_row[8] or 0) == 1 else None

        msg_user = "You can start chatting now."
        if t_insta:
            msg_user += f"\n📱 Their Instagram: @{t_insta}"
        bot.send_message(user_id, msg_user)

        msg_target = "You can start chatting now."
        if s_insta:
            msg_target += f"\n📱 Their Instagram: @{s_insta}"
        bot.send_message(target_id, msg_target)

        bot.send_message(ADMIN_ID, f"🎊 New Match! {seeker_row[1]} ({user_id}) ⟷ {target_row[1]} ({target_id})")


# --- View profile ---

@bot.message_handler(commands=['viewprofile'])
def view_profile_cmd(message):
    user_id = message.chat.id
    user_row = get_user(user_id)
    if not user_row:
        bot.send_message(user_id, "❌ No profile found. Use /start to create one.")
        return
    text = profile_text_from_row(user_row)
    if user_row[7] and int(user_row[8] or 0) == 1:
        text += f"\n📱 Instagram: @{user_row[7]}"
    if user_row[9]:
        try:
            bot.send_photo(user_id, user_row[9], caption=text)
        except Exception:
            bot.send_message(user_id, text)
    else:
        bot.send_message(user_id, text)


# --- Admin block/unblock ---

@bot.message_handler(commands=['block'])
def block_user(message):
    if message.chat.id != ADMIN_ID:
        bot.send_message(message.chat.id, "❌ You are not an admin.")
        return
    args = message.text.split()
    if len(args) != 2:
        bot.send_message(message.chat.id, "Usage: /block <user_id>")
        return
    try:
        target_id = int(args[1])
    except ValueError:
        bot.send_message(message.chat.id, "User ID must be a number.")
        return
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE users SET stars = 0 WHERE user_id = ?", (target_id,))
    conn.commit()
    conn.close()
    bot.send_message(message.chat.id, f"✅ User {target_id} has been blocked.")


@bot.message_handler(commands=['unblock'])
def unblock_user(message):
    if message.chat.id != ADMIN_ID:
        bot.send_message(message.chat.id, "❌ You are not an admin.")
        return
    args = message.text.split()
    if len(args) != 2:
        bot.send_message(message.chat.id, "Usage: /unblock <user_id>")
        return
    try:
        target_id = int(args[1])
    except ValueError:
        bot.send_message(message.chat.id, "User ID must be a number.")
        return
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE users SET stars = 1 WHERE user_id = ?", (target_id,))
    conn.commit()
    conn.close()
    bot.send_message(message.chat.id, f"✅ User {target_id} has been unblocked.")


# --- Help ---

@bot.message_handler(commands=['help'])
def help_cmd(message):
    bot.send_message(
        message.chat.id,
        "💬 MedMatchBot Help\n\n"
        "Use these commands:\n"
        "• /start — Create or edit your profile\n"
        "• /findmatch — Find people who match your criteria\n"
        "• /viewprofile — View your own profile\n"
        "• /help — Show this help message\n\n"
        "✨ Higher star users have access to better matches!"
    )


# --- Simple Flask webhook endpoints (if using webhooks) ---

app = Flask(__name__)

@app.route('/')
def home():
    return "MedMatchBot is running 💘"

@app.route('/setwebhook', methods=['GET'])
def set_webhook():
    if not WEBHOOK_URL:
        return "WEBHOOK_URL not configured", 400
    bot.remove_webhook()
    time.sleep(1)
    bot.set_webhook(url=WEBHOOK_URL.rstrip('/') + '/' + BOT_TOKEN)
    return "Webhook set successfully!"

if __name__ == "__main__":
    if WEBHOOK_URL:
        logging.info('Starting Flask app for webhook...')
        app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
    else:
        logging.info('Starting bot in polling mode...')
        bot.infinity_polling()
