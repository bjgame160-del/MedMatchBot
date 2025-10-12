import os
import telebot
from telebot import types
from flask import Flask

# Load environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")

bot = telebot.TeleBot(BOT_TOKEN)
server = Flask(__name__)

users = {}
user_photos = {}

# Start command
@bot.message_handler(commands=['start'])
def start(message):
    chat_id = message.chat.id
    users[chat_id] = {"stars": 0}
    bot.send_message(chat_id, "👋 Welcome to *MedicoMatch!* Let's create your profile.", parse_mode="Markdown")
    bot.send_message(chat_id, "What's your *name*?")
    bot.register_next_step_handler(message, get_name)

def get_name(message):
    users[message.chat.id]["name"] = message.text
    bot.send_message(message.chat.id, "What's your *gender?* (Male/Female/Other)")
    bot.register_next_step_handler(message, get_gender)

def get_gender(message):
    users[message.chat.id]["gender"] = message.text
    bot.send_message(message.chat.id, "In which *state* is your medical college?")
    bot.register_next_step_handler(message, get_state)

def get_state(message):
    users[message.chat.id]["state"] = message.text
    bot.send_message(message.chat.id, "Which *year* are you in? (e.g., 1st year, 2nd year, Internship, etc.)")
    bot.register_next_step_handler(message, get_year)

def get_year(message):
    users[message.chat.id]["year"] = message.text
    bot.send_message(message.chat.id, "Which subjects do you *like most*?")
    bot.register_next_step_handler(message, get_likes)

def get_likes(message):
    users[message.chat.id]["likes"] = message.text
    bot.send_message(message.chat.id, "Which subjects do you *dislike*?")
    bot.register_next_step_handler(message, get_dislikes)

def get_dislikes(message):
    users[message.chat.id]["dislikes"] = message.text
    users[message.chat.id]["stars"] = 1
    # Notify admin about new registration (basic profile)
    admin_msg = (
        f"📩 New registration started:\n"
        f"👤 Name: {users[message.chat.id].get('name')}\n"
        f"⚧ Gender: {users[message.chat.id].get('gender')}\n"
        f"📍 State: {users[message.chat.id].get('state')}\n"
        f"🎓 Year: {users[message.chat.id].get('year')}\n"
        f"❤️ Likes: {users[message.chat.id].get('likes')}\n"
        f"💔 Dislikes: {users[message.chat.id].get('dislikes')}\n"
    )
    bot.send_message(int(ADMIN_ID), admin_msg)
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Enter Instagram Username 📸", "Upload Selfie/College ID 🪪", "View Profile ⭐")
    bot.send_message(message.chat.id, "✅ Basic profile completed! You earned ⭐ (1 Star)", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "Enter Instagram Username 📸")
def get_insta(message):
    bot.send_message(message.chat.id, "Send your Instagram username (without @):")
    bot.register_next_step_handler(message, save_insta)

def save_insta(message):
    insta = message.text.strip().replace("@", "")
    users[message.chat.id]["instagram"] = insta
    users[message.chat.id]["stars"] = 2

    # Notify user
    bot.send_message(message.chat.id, f"✅ Insta handle saved.\nYou earned ⭐⭐ (2 Stars)\nYou can now find matches.")

    # Send full registration info to admin
    info = (
        f"📩 New registration completed:\n"
        f"👤 Name: {users[message.chat.id].get('name')}\n"
        f"⚧ Gender: {users[message.chat.id].get('gender')}\n"
        f"📍 State: {users[message.chat.id].get('state')}\n"
        f"🎓 Year: {users[message.chat.id].get('year')}\n"
        f"❤️ Likes: {users[message.chat.id].get('likes')}\n"
        f"💔 Dislikes: {users[message.chat.id].get('dislikes')}\n"
        f"📸 Instagram: @{insta}"
    )
    bot.send_message(int(ADMIN_ID), info)

@bot.message_handler(func=lambda m: m.text == "Upload Selfie/College ID 🪪")
def ask_photo(message):
    bot.send_message(message.chat.id, "Please upload your selfie or college ID photo 📸")
    bot.register_next_step_handler(message, save_photo)

def save_photo(message):
    if message.photo:
        file_id = message.photo[-1].file_id
        users[message.chat.id]["photo_id"] = file_id
        users[message.chat.id]["stars"] = 3

        # Notify user
        bot.send_message(
            message.chat.id,
            "✅ Photo uploaded successfully!\nYou are now ⭐⭐⭐ *Fully Verified!*",
            parse_mode="Markdown"
        )

        # Notify admin with full user info + photo
        admin_msg = (
            f"📷 New verification photo received:\n"
            f"👤 Name: {users[message.chat.id].get('name')}\n"
            f"⚧ Gender: {users[message.chat.id].get('gender')}\n"
            f"📍 State: {users[message.chat.id].get('state')}\n"
            f"🎓 Year: {users[message.chat.id].get('year')}\n"
            f"⭐ Verification: 3 Stars"
        )
        bot.send_message(int(ADMIN_ID), admin_msg)
        bot.send_photo(int(ADMIN_ID), file_id)

    else:
        bot.send_message(message.chat.id, "❌ Please send a valid photo.")

@bot.message_handler(func=lambda m: m.text == "View Profile ⭐")
def view_profile(message):
    user = users.get(message.chat.id)
    if not user:
        bot.send_message(message.chat.id, "No profile found. Type /start to begin.")
        return
    info = (
        f"👤 *Name:* {user.get('name')}\n"
        f"⚧ *Gender:* {user.get('gender')}\n"
        f"📍 *State:* {user.get('state')}\n"
        f"🎓 *Year:* {user.get('year')}\n"
        f"❤️ *Likes:* {user.get('likes')}\n"
        f"💔 *Dislikes:* {user.get('dislikes')}\n"
        f"⭐ *Verification:* {user.get('stars')} Stars\n"
    )
    bot.send_message(message.chat.id, info, parse_mode="Markdown")

# Flask server for Render keep-alive
@server.route('/')
def home():
    return "Bot is running!"

from flask import Flask, request

app = Flask(__name__)

@app.route(f"/{BOT_TOKEN}", methods=['POST'])
def getMessage():
    bot.process_new_updates([telebot.types.Update.de_json(request.stream.read().decode("utf-8"))])
    return "!", 200

@app.route("/")
def webhook():
    bot.remove_webhook()
    bot.set_webhook(url='https://medmatchbot.onrender.com/' + BOT_TOKEN)
    return "Bot is running!", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
