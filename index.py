import os
import requests
from flask import Flask, request
from telegram import Bot, Update
from telegram.ext import CommandHandler, MessageHandler, Filters, Dispatcher
from dotenv import load_dotenv
from bs4 import BeautifulSoup

# Load environment variables
load_dotenv()

# Telegram bot token
TOKEN = os.getenv("TELEGRAM_TOKEN")
bot = Bot(TOKEN)

# In-memory storage for user patterns
user_patterns = {}

# Function to guide the user
def start(update: Update, context) -> None:
    update.message.reply_text(
        "Hello! To help me bypass shortened URLs, follow these steps:\n\n"
        "1. Open the shortened URL in your browser.\n"
        "2. Trace the steps or actions needed to reach the final destination.\n"
        "3. Send me the URL along with a brief description of the steps or actions you took.\n\n"
        "Example:\n"
        "1. Open URL: http://short.url\n"
        "2. Click 'Continue' button if required.\n"
        "3. Send me the final URL.\n\n"
        "After you provide the steps, I will be able to handle similar URLs in the future."
    )

# Function to save bypass steps
def save_bypass_steps(update: Update, context) -> None:
    url = update.message.text
    user_id = update.message.chat_id
    
    if user_id not in user_patterns:
        user_patterns[user_id] = {}

    # Save URL and corresponding bypass steps (You need to adjust this based on actual steps)
    user_patterns[user_id][url] = "manual steps provided by the user"

    update.message.reply_text(
        "Thanks! I have noted down the steps for the URL. You can now provide me with similar shortened URLs, "
        "and I will automatically bypass them for you."
    )

# Function to automatically bypass learned steps
def bypass_learned_steps(update: Update, context) -> None:
    url = update.message.text
    user_id = update.message.chat_id

    if user_id in user_patterns:
        # Simulate bypass based on saved steps (You need to implement actual logic based on saved steps)
        # Example: Here we just provide the original URL
        final_url = url

        update.message.reply_text(f'Final bypassed link: {final_url}')
    else:
        update.message.reply_text(
            "I don't have any bypass steps saved for you. Please use the /start command to teach me how to bypass URLs."
        )

# Function to set up dispatcher
def setup_dispatcher():
    dispatcher = Dispatcher(bot, None, use_context=True)
    dispatcher.add_handler(CommandHandler('start', start))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, save_bypass_steps))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, bypass_learned_steps))
    return dispatcher

# Flask app setup
app = Flask(__name__)

@app.route('/')
def index():
    return 'Hello World!'

@app.route(f'/{TOKEN}', methods=['POST'])
def respond():
    update = Update.de_json(request.get_json(force=True), bot)
    setup_dispatcher().process_update(update)
    return 'ok'

@app.route('/setwebhook', methods=['GET', 'POST'])
def set_webhook():
    webhook_url = f'https://yourapp.vercel.app/{TOKEN}'
    s = bot.setWebhook(webhook_url)
    if s:
        return "Webhook setup ok"
    else:
        return "Webhook setup failed"

if __name__ == '__main__':
    app.run(debug=True)
