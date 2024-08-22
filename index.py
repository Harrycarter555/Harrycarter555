import os
import requests
from flask import Flask, request
from telegram import Bot, Update
from telegram.ext import CommandHandler, MessageHandler, Filters, Dispatcher
from dotenv import load_dotenv
from urllib.parse import urlparse

# Load environment variables
load_dotenv()

# Telegram bot token
TOKEN = os.getenv("TELEGRAM_TOKEN")
bot = Bot(TOKEN)

# Bypass function to resolve the final URL
def bypass_link(url):
    try:
        # Make a HEAD request to follow redirects
        response = requests.head(url, allow_redirects=True)
        final_url = response.url
        return final_url
    except Exception as e:
        return f"Error bypassing the link: {str(e)}"

# Function to send start message
def start(update: Update, context) -> None:
    update.message.reply_text(
        "Hello! Send me a shortened URL, and I will bypass it to give you the final destination link."
    )

# Function to process URL
def process_url(update: Update, context) -> None:
    url = update.message.text

    if "http" in url:
        final_url = bypass_link(url)
        update.message.reply_text(f'Bypassed link: {final_url}')
    else:
        update.message.reply_text(
            'It seems like the input is not a valid URL. Please send a proper shortened URL.'
        )

# Function to set up dispatcher
def setup_dispatcher():
    dispatcher = Dispatcher(bot, None, use_context=True)
    dispatcher.add_handler(CommandHandler('start', start))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, process_url))
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
    webhook_url = f'https://harrycarter555.vercel.app/{TOKEN}'
    s = bot.setWebhook(webhook_url)
    if s:
        return "Webhook setup ok"
    else:
        return "Webhook setup failed"

if __name__ == '__main__':
    app.run(debug=True)
