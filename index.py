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

# Function to learn the bypass steps from the initial link
def learn_bypass_steps(url):
    global bypass_patterns
    try:
        session = requests.Session()
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}

        # Get initial page
        response = session.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')

        # Save the identified steps/pattern
        bypass_patterns[url] = {
            'headers': headers,
            'soup': str(soup),  # Storing the initial page structure
            'final_url': response.url  # Final redirect URL (if any)
        }

        # Save the updated patterns to the file
        save_bypass_patterns(bypass_patterns)

        return "Steps learned successfully!"
    except Exception as e:
        return f"Error learning the link: {str(e)}"

# Function to bypass a similar link based on learned steps
def bypass_similar_link(url):
    global bypass_patterns
    try:
        # Check if the pattern already exists
        if url in bypass_patterns:
            pattern = bypass_patterns[url]

            session = requests.Session()

            # Apply the learned headers
            response = session.get(url, headers=pattern['headers'])
            soup = BeautifulSoup(response.text, 'html.parser')

            # Compare the current soup with the learned soup pattern
            if str(soup) == pattern['soup']:
                return pattern['final_url']
            else:
                return "Error: The current link does not match the learned pattern."
        else:
            return "Error: No learned pattern found for this URL. Please provide the initial link first."
    except Exception as e:
        return f"Error bypassing the link: {str(e)}"

# Function to send start message
def start(update: Update, context) -> None:
    update.message.reply_text(
        "Hello! Please send the initial link for me to learn the bypass steps."
    )

# Function to process URL and learn or bypass based on context
def process_url(update: Update, context) -> None:
    url = update.message.text

    if "http" in url:
        if url in bypass_patterns:
            result = bypass_similar_link(url)
            update.message.reply_text(f'Result: {result}')
        else:
            result = learn_bypass_steps(url)
            update.message.reply_text(result)
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
