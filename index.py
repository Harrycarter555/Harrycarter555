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

# In-memory storage for learning steps for different patterns
step_patterns = {}

# Function to trace and save steps for a given URL
def trace_and_save_steps(url, user_id):
    try:
        session = requests.Session()
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = session.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Save the URL and its subsequent steps
        if user_id not in step_patterns:
            step_patterns[user_id] = []

        # Example of saving a step; adjust based on actual shortener steps
        step_patterns[user_id].append(url)
        
        # Further steps can be traced and added here if needed
        
        return "Steps saved successfully!"
    except Exception as e:
        return f"Error tracing the link: {str(e)}"

# Function to handle initial URL input for learning steps
def teach_steps(update: Update, context) -> None:
    url = update.message.text
    user_id = update.message.chat_id
    result = trace_and_save_steps(url, user_id)
    update.message.reply_text(result)

# Function to automatically bypass using learned steps
def bypass_learned_steps(update: Update, context) -> None:
    url = update.message.text
    user_id = update.message.chat_id

    if user_id in step_patterns and len(step_patterns[user_id]) > 0:
        session = requests.Session()
        headers = {'User-Agent': 'Mozilla/5.0'}
        final_url = url

        # Follow each learned step
        for step in step_patterns[user_id]:
            response = session.get(final_url, headers=headers)
            final_url = response.url

        update.message.reply_text(f'Final bypassed link: {final_url}')
    else:
        update.message.reply_text("Please teach me the steps first using /teach command.")

# Function to set up dispatcher
def setup_dispatcher():
    dispatcher = Dispatcher(bot, None, use_context=True)
    dispatcher.add_handler(CommandHandler('teach', teach_steps))
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
