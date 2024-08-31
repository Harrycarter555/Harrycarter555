import os
import requests
from bs4 import BeautifulSoup
from flask import Flask, request
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, MessageHandler, Filters, CallbackQueryHandler, Dispatcher
from dotenv import load_dotenv
import logging

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
    logging.debug(f"User ID: {user_id}")
    if user_in_channel(user_id):
        user_membership_status[user_id] = True
        logging.debug(f"User {user_id} joined the channel and is now verified.")
        update.message.reply_text("You are verified as a channel member. Send a movie name to search for it.")
    else:
        user_membership_status[user_id] = False
        logging.debug(f"User {user_id} did not join the channel.")
        update.message.reply_text(f"Please join our channel to use this bot: {CHANNEL_INVITE_LINK}")

def user_in_channel(user_id):
    url = f"https://api.telegram.org/bot{TOKEN}/getChatMember?chat_id={CHANNEL_ID}&user_id={user_id}"
    logging.debug(f"Checking membership status for user {user_id} with URL: {url}")
    try:
        response = requests.get(url).json()
        logging.debug(f"Response from Telegram API: {response}")
        if response.get('ok') and 'result' in response:
            status = response['result']['status']
            logging.debug(f"User {user_id} status in channel: {status}")
            return status in ['member', 'administrator', 'creator']
        else:
            logging.error("Invalid response structure or 'ok' field is False.")
            return False
    except Exception as e:
        logging.error(f"Exception while checking user channel status: {e}")
        return False

def search_movies(query):
    search_url = f"https://www.filmyfly.wales/site-1.html?to-search={query}"
    logging.debug(f"Searching for movies with URL: {search_url}")

    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
        }
        response = requests.get(search_url, headers=headers)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')

            movies = []
            for item in soup.find_all('div', class_='A2'):
                # Extracting the title
                title_tag = item.find('a', href=True).find_next('b').find('span')
                title = title_tag.get_text(strip=True) if title_tag else "No Title"
                
                # Extracting the movie URL
                movie_url_tag = item.find('a', href=True)
                movie_url = "https://www.filmyfly.wales" + movie_url_tag['href'] if movie_url_tag else "#"

                # Extracting the image URL
                image_tag = item.find('img')
                image_url = image_tag['src'] if image_tag else ""

                movies.append({
                    'title': title,
                    'url': movie_url,
                    'image': image_url
                })
            logging.debug(f"Movies found: {movies}")
            return movies
        else:
            logging.error(f"Failed to retrieve search results. Status Code: {response.status_code}")
            return []
    except Exception as e:
        logging.error(f"Error during movie search: {e}")
        return []

def find_movie(update: Update, context) -> None:
    query = update.message.text.strip()
    user_id = update.message.from_user.id
    search_results = update.message.reply_text("Searching for movies... Please wait.")
    movies_list = search_movies(query)
    logging.debug(f"Movies List: {movies_list}")
    
    if movies_list:
        # Save search results in cache
        search_results_cache[user_id] = movies_list

        # Show the first result
        show_movie_result(update, movies_list[0], 0)
        search_results.delete()  # Remove the initial "Searching..." message
    else:
        search_results.edit_text('Sorry 🙏, No Result Found!\nCheck If You Have Misspelled The Movie Name.')

def show_movie_result(update: Update, movie, index):
    title = movie.get("title", "No Title")
    movie_url = movie.get("url", "#")
    image_url = movie.get("image", "")

    keyboard = [
        [InlineKeyboardButton("Watch Now", url=movie_url)],
        [InlineKeyboardButton("Trailer", url=movie_url + "/#modaltrailer")],
        [InlineKeyboardButton("Next", callback_data=f"next_{index + 1}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if image_url:
        update.message.reply_photo(photo=image_url, caption=title, reply_markup=reply_markup)
    else:
        update.message.reply_text(title, reply_markup=reply_markup)

def button(update: Update, context) -> None:
    query = update.callback_query
    query.answer()

    user_id = query.from_user.id
    callback_data = query.data

    if callback_data.startswith("next_"):
        index = int(callback_data.split("_")[1])
        movies_list = search_results_cache.get(user_id, [])

        if index < len(movies_list):
            movie = movies_list[index]
            query.message.delete()  # Delete the previous message
            show_movie_result(query, movie, index)
        else:
            query.message.reply_text("No more results.")

def setup_dispatcher():
    dispatcher = Dispatcher(bot, None, use_context=True)
    dispatcher.add_handler(CommandHandler('start', welcome))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, find_movie))
    dispatcher.add_handler(CallbackQueryHandler(button))
    return dispatcher

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
    webhook_url = f'https://harrycarter555.vercel.app/{TOKEN}'  # Update with your deployment URL
    s = bot.setWebhook(webhook_url)
    if s:
        return "Webhook setup ok"
    else:
        return "Webhook setup failed"

if __name__ == '__main__':
    app.run(debug=True)
