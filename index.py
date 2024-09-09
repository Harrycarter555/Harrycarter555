import os
import requests
from flask import Flask, request
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, Filters, CallbackQueryHandler
from dotenv import load_dotenv
import logging
from threading import Thread
from movies_scraper import search_movies

load_dotenv()

# Setup logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = "-1002170013697"  # Replace with your actual private channel ID
CHANNEL_INVITE_LINK = "https://t.me/+dUXsdWu9dlk4ZTk9"  # Replace with your actual invitation link
bot = Bot(TOKEN)

# Dummy storage for demonstration (replace with actual persistent storage solution)
user_membership_status = {}
search_results_cache = {}

def welcome(update: Update, context) -> None:
    user_id = update.message.from_user.id
    if user_in_channel(user_id):
        user_membership_status[user_id] = True
        update.message.reply_text("You are verified as a channel member. Send a movie name to search for it.")
    else:
        user_membership_status[user_id] = False
        update.message.reply_text(f"Please join our channel to use this bot: {CHANNEL_INVITE_LINK}")

def user_in_channel(user_id):
    url = f"https://api.telegram.org/bot{TOKEN}/getChatMember?chat_id={CHANNEL_ID}&user_id={user_id}"
    try:
        response = requests.get(url).json()
        if response.get('ok') and 'result' in response:
            status = response['result']['status']
            return status in ['member', 'administrator', 'creator']
        else:
            return False
    except Exception as e:
        logging.error(f"Exception while checking user channel status: {e}")
        return False

def find_movie(update: Update, context) -> None:
    query = update.message.text.strip()
    user_id = update.message.from_user.id
    search_results = update.message.reply_text("Searching for movies... Please wait.")

    def search_and_reply():
        try:
            movies_list = search_movies(query)
            if movies_list:
                search_results_cache[user_id] = movies_list
                keyboard = [[InlineKeyboardButton(movie['title'], callback_data=str(idx))] for idx, movie in enumerate(movies_list)]
                reply_markup = InlineKeyboardMarkup(keyboard)
                search_results.edit_text('Select a movie:', reply_markup=reply_markup)
            else:
                search_results.edit_text('Sorry 🙏, No Result Found! Check If You Have Misspelled The Movie Name.')
        except Exception as e:
            logging.error(f"Error during movie search: {e}")
            search_results.edit_text('An error occurred while searching for movies.')

    # Start the search in a new thread to prevent blocking
    Thread(target=search_and_reply).start()

def button_click(update: Update, context) -> None:
    query = update.callback_query
    query.answer()

    user_id = query.from_user.id
    selected_movie_idx = int(query.data)
    selected_movie = search_results_cache[user_id][selected_movie_idx]

    title = selected_movie['title']
    image_url = selected_movie.get('image', None)
    download_links = selected_movie.get('download_links', [])

    keyboard = []
    for link in download_links:
        keyboard.append([InlineKeyboardButton(link['text'], url=link['url'])])

    reply_markup = InlineKeyboardMarkup(keyboard)

    if image_url:
        query.message.reply_photo(photo=image_url, caption=f"{title}", reply_markup=reply_markup)
    else:
        query.message.reply_text(f"{title}\n\nDownload Links:", reply_markup=reply_markup)

def setup_dispatcher():
    dispatcher = Dispatcher(bot, None, use_context=True)
    dispatcher.add_handler(CommandHandler('start', welcome))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, find_movie))
    dispatcher.add_handler(CallbackQueryHandler(button_click))
    return dispatcher

app = Flask(__name__)

@app.route('/')
def index():
    return 'Hello World!'

@app.route(f'/{TOKEN}', methods=['POST'])
def respond():
    update = Update.de_json(request.get_json(force=True), bot)
    try:
        setup_dispatcher().process_update(update)
    except Exception as e:
        logging.error(f"Exception while processing update: {e}")
    return 'ok'

@app.route('/setwebhook', methods=['GET', 'POST'])
def set_webhook():
    webhook_url = f'https://harrycarter555.vercel.app/{TOKEN}'  # Update with your deployment URL
    try:
        s = bot.setWebhook(webhook_url)
        if s:
            return "Webhook setup ok"
        else:
            return "Webhook setup failed"
    except Exception as e:
        logging.error(f"Exception while setting webhook: {e}")
        return "Webhook setup failed"

if __name__ == '__main__':
    app.run(debug=True)
