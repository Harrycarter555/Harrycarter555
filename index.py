import os
import requests
import json
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

# File to save the learned bypass patterns
PATTERN_FILE = "bypass_patterns.json"

# Function to load the saved patterns from the file
def load_bypass_patterns():
    if os.path.exists(PATTERN_FILE):
        with open(PATTERN_FILE, 'r') as file:
            return json.load(file)
    return {}

# Function to save the patterns to the file
def save_bypass_patterns(patterns):
    with open(PATTERN_FILE, 'w') as file:
        json.dump(patterns, file)

# Load patterns initially
bypass_patterns = load_bypass_patterns()

# Function to trace steps from the initial link provided by the user
def trace_and_learn_steps(url):
    try:
        session = requests.Session()
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}

        # Step 1: Get initial page
        response = session.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')

        # Example for extracting any needed tokens or hidden inputs
        # token = soup.find('input', {'name': 'token'})['value']

        # (Optional) Simulate clicking through the bypass process
        # response = session.post('next-step-url', data={'token': token}, headers=headers)

        # Final URL after bypass
        final_url = response.url

        # Save the traced steps to the bypass patterns
        bypass_patterns[url] = {
            'final_url': final_url,
            'headers': headers,
            # Additional data can be saved if needed (e.g., tokens, POST data)
        }

        # Save the updated patterns to the file
        save_bypass_patterns(bypass_patterns)

        return final_url  # Return the final URL to the user
    except Exception as e:
        return f"Error tracing the link: {str(e)}"

# Function to bypass a link based on learned steps
def auto_bypass_link(url):
    try:
        for pattern in bypass_patterns:
            if pattern in url:
                # Return the saved final URL directly
                return bypass_patterns[pattern]['final_url']
        return "No learned pattern found for this URL. Please teach me the initial link first."
    except Exception as e:
        return f"Error bypassing the link: {str(e)}"

# Function to send start message
def start(update: Update, context) -> None:
    update.message.reply_text(
        "Hello! Please send me a shortened URL to learn how to bypass it. After learning, I will automatically bypass similar links."
    )

# Function to process URL
def process_url(update: Update, context) -> None:
    url = update.message.text

    if "http" in url:
        if any(pattern in url for pattern in bypass_patterns):
            # Automatically bypass if pattern is learned
            final_url = auto_bypass_link(url)
        else:
            # Learn the steps if pattern is not yet learned
            final_url = trace_and_learn_steps(url)
            update.message.reply_text(f'I have learned how to bypass this URL!')

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
