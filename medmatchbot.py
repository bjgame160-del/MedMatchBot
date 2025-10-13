import os
import sqlite3
import telebot
from telebot import types
from flask import Flask
import random

# ───────────────────────────────
#  Configuration
# ───────────────────────────────
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "6371731528"))   # your admin ID
bot = telebot.TeleBot(BOT_TOKEN)
CHANNEL_USERNAME = "@medicosssssssss"  
CHANNEL_LINK = "https://t.me/medicosssssssss"

def is_user_in_channel(user_id):
    try:
        member = bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ['member', 'administrator', 'creator']
    except Exception as e:
        print("Error checking channel membership:", e)
        return False
if not is_user_in_channel(chat_id):
    join_text = (
        "🚨 To use this bot, you must first join our official channel!\n\n"
        f"👉 [Join Here]({CHANNEL_LINK})\n\n"
        "After joining, press /start again."
) 
bot.send_message(chat_id, join_text, parse_mode="Markdown", disable_web_page_preview=True)
return
server = Flask(__name__)

# ───────────────────────────────
#  Database Setup
# ───────────────────────────────
DB_PATH = "users.db"

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
        liked_users TEXT DEFAULT ''
    )''')
    conn.commit()
    conn.close()

def save_user_data(user_id, field, value):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(f"UPDATE users SET {field}=? WHERE user_id=?", (value, user_id))
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row

# Initialize DB
init_db()

# ───────────────────────────────
#  Registration Flow
# ───────────────────────────────
@bot.message_handler(commands=['start'])
@bot.message_handler(commands=['start'])
def start(message):
    chat_id = message.chat.id

    # 🔹 Check if user is in channel
    if not is_user_in_channel(chat_id):
        join_text = (
            "🚨 To use this bot, you must first join our official channel!\n\n"
            f"👉 [Join Here]({CHANNEL_USERNAME})\n\n"
            "After joining, press /start again."
        )
        bot.send_message(chat_id, join_text, parse_mode="Markdown", disable_web_page_preview=True)
        return

    # If joined, continue registration
    users[chat_id] = {"stars": 0}
    bot.send_message(chat_id, "👋 Welcome to *MedMatch!* Let's create your profile.", parse_mode="Markdown")
    bot.send_message(chat_id, "What's your *name*?")
    bot.register_next_step_handler(message, get_name)

def get_name(message):
    user_id = message.chat.id
    save_user_data(user_id, "name", message.text)
    bot.send_message(user_id, "What's your *gender?* (Male/Female/Other)")
    bot.register_next_step_handler(message, get_gender)

def get_gender(message):
    user_id = message.chat.id
    save_user_data(user_id, "gender", message.text)
    bot.send_message(user_id, "In which *state* is your medical college?")
    bot.register_next_step_handler(message, get_state)

def get_state(message):
    user_id = message.chat.id
    save_user_data(user_id, "state", message.text)
    bot.send_message(user_id, "Which *year* are you in? (e.g., 1st year, 2nd year, Internship)")
    bot.register_next_step_handler(message, get_year)

def get_year(message):
    user_id = message.chat.id
    save_user_data(user_id, "year", message.text)
    bot.send_message(user_id, "Which subjects do you *like most*?")
    bot.register_next_step_handler(message, get_likes)

def get_likes(message):
    user_id = message.chat.id
    save_user_data(user_id, "likes", message.text)
    bot.send_message(user_id, "Which subjects do you *dislike*?")
    bot.register_next_step_handler(message, get_dislikes)

def get_dislikes(message):
    user_id = message.chat.id
    save_user_data(user_id, "dislikes", message.text)
    save_user_data(user_id, "stars", 1)
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Enter Instagram Username 📸", "Upload Selfie/College ID 🪪")
    markup.add("Find Match 💞", "View Profile ⭐")
    bot.send_message(message.chat.id, "✅ Basic profile completed! You earned ⭐ (1 Star)", reply_markup=markup)
    bot.send_message(ADMIN_ID, f"🆕 New user registered: {message.from_user.first_name} ({user_id})")

# ───────────────────────────────
#  Instagram & Verification
# ───────────────────────────────
@bot.message_handler(func=lambda m: m.text == "Enter Instagram Username 📸")
def ask_insta(message):
    bot.send_message(message.chat.id, "Send your Instagram username (without @):")
    bot.register_next_step_handler(message, save_insta)

def save_insta(message):
    user_id = message.chat.id
    insta = message.text.strip().replace("@", "")
    save_user_data(user_id, "instagram", insta)

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("👁 Show Insta to matches", callback_data="show_insta"),
               types.InlineKeyboardButton("🙈 Hide Insta", callback_data="hide_insta"))
    bot.send_message(user_id, "Would you like to show your Insta to matches?", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data in ["show_insta", "hide_insta"])
def set_insta_visibility(call):
    user_id = call.message.chat.id
    show = 1 if call.data == "show_insta" else 0
    save_user_data(user_id, "show_insta", show)
    save_user_data(user_id, "stars", 2)
    bot.answer_callback_query(call.id, "Saved!")
    bot.send_message(user_id, "✅ Instagram saved. You earned ⭐⭐ (2 Stars) and can now find matches.")
    user = get_user(user_id)
    bot.send_message(ADMIN_ID, f"📸 Insta added: {user[1]} (@{user[7]})")

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
    save_user_data(user_id, "photo_id", file_id)
    save_user_data(user_id, "stars", 3)
    bot.send_message(user_id, "✅ Photo uploaded! You are now ⭐⭐⭐ *Fully Verified!*", parse_mode="Markdown")
    bot.send_message(ADMIN_ID, f"🪪 New verification photo from {message.from_user.first_name}")
    bot.send_photo(ADMIN_ID, file_id)
    # ───────────────────────────────
#  Part 2 — Matching Logic
# ───────────────────────────────

import json
import time

# helper: convert liked_users TEXT to set and back
def get_liked_set(user_row):
    s = user_row[11] if user_row and user_row[11] else ""
    try:
        liked = set(json.loads(s)) if s.strip() else set()
    except Exception:
        liked = set()
    return liked

def save_liked_set(user_id, liked_set):
    s = json.dumps(list(liked_set))
    save_user_data(user_id, "liked_users", s)

# helper: build profile text from DB row
def profile_text_from_row(row):
    # row indices based on CREATE TABLE order:
    # 0 user_id,1 name,2 gender,3 state,4 year,5 likes,6 dislikes,7 instagram,8 show_insta,9 photo_id,10 stars,11 liked_users
    name = row[1] or "-"
    gender = row[2] or "-"
    state = row[3] or "-"
    year = row[4] or "-"
    likes = row[5] or "-"
    dislikes = row[6] or "-"
    stars = row[10] or 0
    star_text = "⭐" * int(stars) if stars > 0 else "⚪ Unverified"
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

# helper: check eligibility between seeker and candidate
def is_eligible(seeker_row, candidate_row):
    # basic checks: opposite gender only
    if not seeker_row or not candidate_row:
        return False
    seeker_id, seeker_gender, seeker_stars = seeker_row[0], seeker_row[2], seeker_row[10]
    cand_id, cand_gender, cand_stars = candidate_row[0], candidate_row[2], candidate_row[10]
    # must be different users
    if seeker_id == cand_id:
        return False
    # opposite gender policy
    if seeker_gender and cand_gender and seeker_gender.lower() == cand_gender.lower():
        return False
    # star rules
    if seeker_stars == 1:
        return False
    if seeker_stars == 2 and cand_stars != 2:
        return False
    if seeker_stars == 3 and cand_stars < 2:
        return False
    # candidate must have at least 2 stars to be discoverable
    if cand_stars < 2:
        return False
    return True

# find next candidate user for seeker (random order)
def find_candidate_for(user_id):
    seeker = get_user(user_id)
    if not seeker:
        return None
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # get all users except seeker
    c.execute("SELECT * FROM users WHERE user_id != ?", (user_id,))
    rows = c.fetchall()
    conn.close()
    # shuffle rows for randomness
    random.shuffle(rows)
    # filter by eligibility and not previously liked/seen
    seeker_likes = get_liked_set(seeker)
    for row in rows:
        if not is_eligible(seeker, row):
            continue
        # skip if seeker already liked or skipped this candidate before
        # we only store likes; skipping won't be persistent in this version to keep it simple
        if str(row[0]) in seeker_likes:
            continue
        return row
    return None

# /findmatch command handler
@bot.message_handler(commands=['findmatch'])
def findmatch_cmd(message):
    user_id = message.chat.id
    user_row = get_user(user_id)
    if not user_row:
        bot.send_message(user_id, "You have no profile yet. Use /start to create your profile.")
        return
    stars = user_row[10] or 0
    if stars < 2:
        bot.send_message(user_id, "⚠️ You need at least 2 Stars to find matches. Complete verification to continue.")
        return
    candidate = find_candidate_for(user_id)
    if not candidate:
        bot.send_message(user_id, "No matches found right now. Try again later.")
        return
    # send profile card with inline buttons
    candidate_text = profile_text_from_row(candidate)
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(
        types.InlineKeyboardButton("❤️ Like", callback_data=f"like_{candidate[0]}"),
        types.InlineKeyboardButton("❌ Skip", callback_data=f"skip_{candidate[0]}")
    )
    # if candidate has their insta visible and seeker is allowed to see it, append
    if candidate[7] and candidate[8] == 1:
        candidate_text += f"\n📱 Instagram: @{candidate[7]}"
    bot.send_message(user_id, candidate_text, reply_markup=keyboard)

# callback handler for like/skip
@bot.callback_query_handler(func=lambda call: call.data and (call.data.startswith("like_") or call.data.startswith("skip_")))
def handle_like_skip(call):
    data = call.data
    user_id = call.from_user.id
    action, target_str = data.split("_", 1)
    target_id = int(target_str)
    # ensure both users exist
    seeker_row = get_user(user_id)
    target_row = get_user(target_id)
    if not seeker_row or not target_row:
        bot.answer_callback_query(call.id, "User data missing.")
        return
    if action == "skip":
        bot.answer_callback_query(call.id, "Skipped ❌")
        # just acknowledge, no persistent skip tracking for now
        return
    # action == like
    # load seeker liked set, add target
    seeker_liked = get_liked_set(seeker_row)
    seeker_liked.add(str(target_id))
    save_liked_set(user_id, seeker_liked)
    bot.answer_callback_query(call.id, "You liked this profile ✅")
    # check mutual: has target liked seeker?
    target_liked = get_liked_set(target_row)
    if str(user_id) in target_liked:
        # it's a match!
        # notify both users
        bot.send_message(user_id, f"🎉 It's a match with {target_row[1]}! 🎉")
        bot.send_message(target_id, f"🎉 It's a match with {seeker_row[1]}! 🎉")
        # share Insta handles if both allowed
        s_insta = seeker_row[7] if seeker_row[8] == 1 else None
        t_insta = target_row[7] if target_row[8] == 1 else None
        # send contact info or prompts
        match_msg_user = "You can start chatting now."
        if t_insta:
            match_msg_user += f"\n📱 Their Instagram: @{t_insta}"
        bot.send_message(user_id, match_msg_user)
        match_msg_target = "You can start chatting now."
        if s_insta:
            match_msg_target += f"\n📱 Their Instagram: @{s_insta}"
        bot.send_message(target_id, match_msg_target)
        # notify admin about match
        bot.send_message(ADMIN_ID, f"🎊 New Match! {seeker_row[1]} ({user_id}) ⟷ {target_row[1]} ({target_id})")
    else:
        # not mutual yet; stored like persists
        pass
        # ───────────────────────────────
#  Part 3 — View Profile + Flask Server
# ───────────────────────────────

from flask import Flask, request

# /viewprofile command
@bot.message_handler(commands=['viewprofile'])
def view_profile_cmd(message):
    user_id = message.chat.id
    user_row = get_user(user_id)
    if not user_row:
        bot.send_message(user_id, "❌ No profile found. Use /start to create one.")
        return
    text = profile_text_from_row(user_row)
    if user_row[7] and user_row[8] == 1:
        text += f"\n📱 Instagram: @{user_row[7]}"
    if user_row[9]:
        bot.send_photo(user_id, user_row[9], caption=text)
    else:
        bot.send_message(user_id, text)
# ───────────────────────────────
#  Admin block / unblock commands
# ───────────────────────────────

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

    # Mark user as blocked: stars = 0 and maybe a field blocked?
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE users SET stars = 0 WHERE user_id = ?", (target_id,))
    # Optionally, you could add a 'blocked' column and set blocked=1
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

    # Unblock: restore stars perhaps to 1 or require re-verification
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE users SET stars = 1 WHERE user_id = ?", (target_id,))
    conn.commit()
    conn.close()
    bot.send_message(message.chat.id, f"✅ User {target_id} has been unblocked.")        

# /help command
@bot.message_handler(commands=['help'])
def help_cmd(message):
    bot.send_message(
        message.chat.id,
        "💬 *MedMatchBot Help*\n\n"
        "Use these commands:\n"
        "• /start — Create or edit your profile\n"
        "• /findmatch — Find people who match your criteria\n"
        "• /viewprofile — View your own profile\n"
        "• /help — Show this help message\n\n"
        "✨ Higher star users have access to better matches!",
        parse_mode="Markdown"
    )
@bot.callback_query_handler(func=lambda call: call.data.startswith("accept_") or call.data.startswith("decline_"))
def handle_match_response(call):
    action, requester_id = call.data.split("_")
    requester_id = int(requester_id)
    responder_id = call.message.chat.id

    if action == "accept":
        bot.send_message(requester_id, "🎉 Your match accepted! You can now chat here. Type /endchat to stop.")
        bot.send_message(responder_id, "💬 You accepted the match! Start chatting now. Type /endchat to stop.")
        users[requester_id]["chat_partner"] = responder_id
        users[responder_id]["chat_partner"] = requester_id
    else:
        bot.send_message(requester_id, "❌ Your match request was declined.")
        bot.send_message(responder_id, "✅ You declined the match.")
@bot.message_handler(func=lambda m: True)
def forward_messages(message):
    chat_partner = users.get(message.chat.id, {}).get("chat_partner")
    if chat_partner:
        bot.send_message(chat_partner, f"{users[message.chat.id]['name']}: {message.text}")

@bot.message_handler(func=lambda m: m.text == "Find Match 💞")
def find_match(message):
    user = users.get(message.chat.id)
    if not user:
        bot.send_message(message.chat.id, "⚠️ You need to complete your profile first. Type /start.")
        return

    user_star = user.get("stars", 0)
    user_gender = user.get("gender", "").lower()

    if user_star < 2:
        bot.send_message(message.chat.id, "⭐ You need at least 2 stars to find a match.")
        return

    # Find compatible users
    for uid, data in users.items():
        if uid == message.chat.id:
            continue

        if data.get("gender", "").lower() == user_gender:
            continue  # skip same gender

        # 2-star users can match only with 2-star
        if user_star == 2 and data.get("stars", 0) != 2:
            continue

        # 3-star users can match with 2 or 3
        if user_star == 3 and data.get("stars", 0) not in [2, 3]:
            continue

        # Match found
        bot.send_message(message.chat.id, f"💞 You’ve got a potential match: *{data.get('name')}*! Sending request...", parse_mode="Markdown")
        bot.send_message(uid, f"💌 You’ve got a match request from *{user.get('name')}*! Accept?", parse_mode="Markdown")

        # Inline buttons for Accept/Decline
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ Accept", callback_data=f"accept_{message.chat.id}"),
                   types.InlineKeyboardButton("❌ Decline", callback_data=f"decline_{message.chat.id}"))
        bot.send_message(uid, "Would you like to accept this chat?", reply_markup=markup)
        return

    bot.send_message(message.chat.id, "😔 No suitable matches found right now. Try again later!")
    
# ───────────────────────────────
#  Flask App (for Render deployment)
# ───────────────────────────────

app = Flask(__name__)

@app.route('/')
def home():
    return "MedMatchBot is running 💘"

@app.route('/' + BOT_TOKEN, methods=['POST'])
def getMessage():
    json_str = request.get_data().decode('UTF-8')
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return "OK", 200

@app.route('/setwebhook', methods=['GET', 'POST'])
def set_webhook():
    bot.remove_webhook()
    time.sleep(1)
    bot.set_webhook(url='https://medmatchbot.onrender.com/' + BOT_TOKEN)
    return "Webhook set successfully!"

if __name__ == "__main__":
    # For Render: use host 0.0.0.0, port from environment
    port = int(os.environ.get("PORT", 5000))
    print("Bot running on port", port)
    app.run(host="0.0.0.0", port=port)
