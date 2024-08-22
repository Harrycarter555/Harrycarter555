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

# Function to bypass a common URL shortener (Example: adf.ly or similar services)
def bypass_shortened_link(url):
    try:
        session = requests.Session()
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}

        # Step 1: Get initial page
        response = session.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')

        # Example for extracting hidden input values or tokens
        # token = soup.find('input', {'name': 'token'})['value']

        # Simulate the wait time or bypass actions here
        # e.g., response = session.post('final-step-url', data={'token': token}, headers=headers)

        # Step 2: Follow redirects until final destination
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
        final_url = bypass_shortened_link(url)
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
