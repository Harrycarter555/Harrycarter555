import os
import requests
from bs4 import BeautifulSoup
from flask import Flask, request
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, MessageHandler, Filters, CallbackQueryHandler, Dispatcher
from dotenv import load_dotenv
import logging
import threading

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
user_search_status = {}
search_results_cache = {}

# Check if user is a member of the channel
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

# /start command response
def welcome(update: Update, context) -> None:
    user_id = update.message.from_user.id
    if user_in_channel(user_id):
        user_search_status[user_id] = None  # Clear any previous search status
        update.message.reply_text("You are verified as a channel member. Send a movie name to search for it.")
    else:
        update.message.reply_text(f"Please join our channel to use this bot: {CHANNEL_INVITE_LINK}")

# Movie search function (runs in the background to avoid blocking main thread)
def search_movies(query: str):
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
                movie_url = "https://filmyfly.wales" + movie_url_tag['href'] if movie_url_tag else "#"
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

# Fetch download links
def get_download_links(movie_url: str):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
        }
        response = requests.get(movie_url, headers=headers)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            download_links = set()  # Use a set to avoid duplicates

            for class_name in ['dl', 'dll', 'dlll']:
                for div in soup.find_all('div', class_=class_name):
                    link = div.find_previous('a', href=True)
                    if link:
                        download_links.add((link['href'], div.get_text(strip=True)))
                    else:
                        download_links.add(('#', div.get_text(strip=True)))

            filtered_links = [
                {'url': url, 'text': text}
                for url, text in download_links
                if url.startswith('http') and 'cank.xyz' not in url
            ]
            return filtered_links
        else:
            logger.error(f"Failed to retrieve download links. Status Code: {response.status_code}")
            return []
    except Exception as e:
        logger.error(f"Error while fetching download links: {e}")
        return []

# Search movie handler
def find_movie(update: Update, context) -> None:
    query = update.message.text.strip()
    user_id = update.message.from_user.id

    # Check if a search is already in progress
    if user_id in user_search_status and user_search_status[user_id] == "searching":
        update.message.reply_text("You already have a search in progress. Please wait or choose another query.")
        return

    # Clear previous search results for the user
    search_results_cache.pop(user_id, None)

    # Update search status
    user_search_status[user_id] = "searching"
    
    # Notify user that search is in progress
    search_results = update.message.reply_text("Searching for movies... Please wait.")
    
    # Perform the movie search in a separate thread
    search_thread = threading.Thread(target=perform_search, args=(update, query, search_results))
    search_thread.start()

def perform_search(update, query, search_results):
    try:
        movies_list = search_movies(query)
        
        if movies_list:
            user_search_status[update.message.from_user.id] = "completed"  # Update search status
            keyboard = [[InlineKeyboardButton(movie['title'], callback_data=str(idx))] for idx, movie in enumerate(movies_list)]
            reply_markup = InlineKeyboardMarkup(keyboard)
            search_results.edit_text('Select a movie:', reply_markup=reply_markup)
        else:
            user_search_status.pop(update.message.from_user.id, None)  # Remove search status if no results
            search_results.edit_text('Sorry 🙏, No Result Found! Check If You Have Misspelled The Movie Name.')
    except Exception as e:
        logger.error(f"Error during search completion: {e}")
        search_results.edit_text('An error occurred while searching. Please try again.')

# Button click handler
def button_click(update: Update, context) -> None:
    query = update.callback_query
    query.answer()
    
    user_id = query.from_user.id
    selected_movie_idx = int(query.data)
    
    if user_id not in search_results_cache:
        query.message.reply_text("No search results found. Please perform a search first.")
        return

    selected_movie = search_results_cache[user_id][selected_movie_idx]

    title = selected_movie['title']
    image_url = selected_movie.get('image', None)
    download_links = selected_movie.get('download_links', [])

    keyboard = [[InlineKeyboardButton(link['text'], url=link['url'])] for link in download_links]

    reply_markup = InlineKeyboardMarkup(keyboard)

    if image_url:
        query.message.reply_photo(photo=image_url, caption=f"{title}", reply_markup=reply_markup)
    else:
        query.message.reply_text(f"{title}\n\nDownload Links:", reply_markup=reply_markup)

# Setup dispatcher
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
    setup_dispatcher().process_update(update)
    return 'ok'

@app.route('/setwebhook', methods=['GET', 'POST'])
def set_webhook():
    webhook_url = f'https://harrycarter555.vercel.app/{TOKEN}'  # Update with your deployment URL
    try:
        response = requests.get(f'https://api.telegram.org/bot{TOKEN}/setWebhook?url={webhook_url}')
        if response.status_code == 200:
            return f"Webhook set to {webhook_url}"
        else:
            return f"Failed to set webhook. Status code: {response.status_code}"
    except Exception as e:
        logger.error(f"Exception while setting webhook: {e}")
        return "Failed to set webhook."

if __name__ == '__main__':
    app.run(port=5000)  # Make sure the port matches your deployment settings

# To handle any updates or commands in a production environment
@app.route('/webhook', methods=['POST'])
def webhook():
    json_update = request.get_json()
    if json_update:
        update = Update.de_json(json_update, bot)
        setup_dispatcher().process_update(update)
    return 'ok'
