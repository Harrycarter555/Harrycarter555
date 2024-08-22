import os
import requests
from flask import Flask, request
from telegram import Bot, Update
from telegram.ext import CommandHandler, MessageHandler, Filters, Dispatcher
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Telegram bot token
TOKEN = os.getenv("TELEGRAM_TOKEN")
bot = Bot(TOKEN)

# Function to send start message
def start(update: Update, context) -> None:
    update.message.reply_text(
        "Hello! Send me a shortened URL. Open that URL in your browser first, "
        "then send me the final link you reached."
    )

# Function to process URL
def process_url(update: Update, context) -> None:
    url = update.message.text

    if "http" in url:
        # Assuming user sent final URL
        update.message.reply_text(f'Received final URL: {url}')
    else:
        # Assuming user needs instructions
        update.message.reply_text(
            'It seems like you sent an incomplete URL. Please open the shortened link in your browser first, '
            'and then send me the full URL that appears in your browser’s address bar.'
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
