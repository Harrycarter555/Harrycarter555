import os
from flask import Flask, request
from telegram import Bot, Update
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, Filters, CallbackQueryHandler
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TELEGRAM_TOKEN")
bot = Bot(TOKEN)

# Flask app setup
app = Flask(__name__)

# Import functions from movies_scraper.py
from movies_scraper import user_in_channel, welcome, find_movie, button_click

# Dispatcher setup
def setup_dispatcher():
    dispatcher = Dispatcher(bot, None, use_context=True)
    dispatcher.add_handler(CommandHandler('start', welcome))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, find_movie))
    dispatcher.add_handler(CallbackQueryHandler(button_click))
    return dispatcher

@app.route('/')
def index():
    return 'Bot is running!'

@app.route(f'/{TOKEN}', methods=['POST'])
def respond():
    try:
        update = Update.de_json(request.get_json(force=True), bot)
        setup_dispatcher().process_update(update)
        logger.info("Update processed successfully")
        return 'ok', 200
    except Exception as e:
        logger.error(f"Error processing update: {e}")
        return 'Error', 500  # Changed to 500 Internal Server Error for better diagnostic

@app.route('/setwebhook', methods=['GET', 'POST'])
def set_webhook():
    webhook_url = f'https://harrycarter555.vercel.app/{TOKEN}'  # Ensure this URL is correct
    try:
        s = bot.setWebhook(webhook_url)
        if s:
            logger.info("Webhook setup successfully")
            return "Webhook setup ok"
        else:
            logger.error("Webhook setup failed")
            return "Webhook setup failed"
    except Exception as e:
        logger.error(f"Error setting up webhook: {e}")
        return "Webhook setup failed"

if __name__ == '__main__':
    app.run(debug=True)
