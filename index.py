import os
import requests
from bs4 import BeautifulSoup
from flask import Flask, request
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, MessageHandler, Filters, CallbackQueryHandler, Dispatcher
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = "-1002214699257"  # Replace with your actual private channel ID
CHANNEL_INVITE_LINK = "https://t.me/+zUnqs8mlbX5kNTE1"  # Replace with your actual invitation link
bot = Bot(TOKEN)

# Dummy storage for demonstration (replace with actual persistent storage solution)
user_membership_status = {}
search_results_cache = {}

def welcome(update: Update, context) -> None:
    user_id = update.message.from_user.id
    
    # Clear the cache when the user starts a new session
    if user_id in search_results_cache:
        del search_results_cache[user_id]
    
    if user_in_channel(user_id):
        user_membership_status[user_id] = True
        update.message.reply_text("You are verified as a channel member. Send a movie name to search for it.")
    else:
        user_membership_status[user_id] = False
        update.message.reply_text(f"Please join our channel to use this bot: {CHANNEL_INVITE_LINK}")

def user_in_channel(user_id) -> bool:
    url = f"https://api.telegram.org/bot{TOKEN}/getChatMember?chat_id={CHANNEL_ID}&user_id={user_id}"
    try:
        response = requests.get(url).json()
        if response.get('ok') and 'result' in response:
            status = response['result']['status']
            return status in ['member', 'administrator', 'creator']
        return False
    except Exception as e:
        logger.error(f"Exception while checking user channel status: {e}")
        return False

def search_movies(query: str):
    # Replace spaces with '+' for multi-word searches
    if ' ' in query:
        query = '+'.join(query.split())
    
    search_url = f"https://filmyfly.wales/site-1.html?to-search={query}"
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
        }
        response = requests.get(search_url, headers=headers)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            movies = []
            for item in soup.find_all('div', class_='A2'):
                title_tag = item.find('a', href=True).find_next('b').find('span')
                title = title_tag.get_text(strip=True) if title_tag else "No Title"
                movie_url_tag = item.find('a', href=True)
                movie_url = "https://www.filmyfly.wales" + movie_url_tag['href'] if movie_url_tag else "#"
                image_tag = item.find('img')
                image_url = image_tag['src'] if image_tag else None
                download_links = get_download_links(movie_url)
                movies.append({
                    'title': title,
                    'url': movie_url,
                    'image': image_url,
                    'download_links': download_links
                })
            return movies
        else:
            logger.error(f"Failed to retrieve search results. Status Code: {response.status_code}")
            return []
    except Exception as e:
        logger.error(f"Error during movie search: {e}")
        return []

def get_download_links(movie_url: str):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
        }
        response = requests.get(movie_url, headers=headers)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            download_links = set()  # Use a set to avoid duplicates

            # Handle <a> tags with classes 'dl', 'dll', 'dlll'
            for class_name in ['dl', 'dll', 'dlll']:
                for div in soup.find_all('div', class_=class_name):
                    link = div.find_previous('a', href=True)
                    if link and link['href'].startswith("http"):
                        download_links.add(link['href'])

            return list(download_links)
        else:
            logger.error(f"Failed to retrieve movie page. Status Code: {response.status_code}")
            return []
    except Exception as e:
        logger.error(f"Error during fetching download links: {e}")
        return []

def handle_message(update: Update, context) -> None:
    user_id = update.message.from_user.id
    if user_id not in user_membership_status or not user_membership_status[user_id]:
        update.message.reply_text(f"Please join our channel to use this bot: {CHANNEL_INVITE_LINK}")
        return

    query = update.message.text.strip()
    
    # Prevent repeated "Searching for movies" messages
    if user_id in search_results_cache and search_results_cache[user_id].get('query') == query:
        update.message.reply_text("You already searched for this movie. Please wait while fetching results.")
        return
    
    # Notify user that the search is in progress
    update.message.reply_text("Searching for movies... Please wait.")
    
    # Search for movies and cache the results
    search_results = search_movies(query)
    search_results_cache[user_id] = {
        'query': query,
        'results': search_results
    }

    if not search_results:
        update.message.reply_text("Sorry, no movies found.")
    else:
        for movie in search_results:
            buttons = [[InlineKeyboardButton("Download", url=movie['url'])]]
            reply_markup = InlineKeyboardMarkup(buttons)
            update.message.reply_photo(
                photo=movie['image'] if movie['image'] else None,
                caption=f"Title: {movie['title']}\nDownload links available.",
                reply_markup=reply_markup
            )

def main():
    app = Flask(__name__)

    @app.route(f"/{TOKEN}", methods=["POST"])
    def respond():
        update = Update.de_json(request.get_json(), bot)
        dispatcher.process_update(update)
        return "ok"

    @app.route("/")
    def index():
        return "Bot is running!"

    updater = Dispatcher(bot, None, workers=0)
    
    # Command and message handlers
    updater.add_handler(CommandHandler("start", welcome))
    updater.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

    return app

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
