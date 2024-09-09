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

# Flask app setup
app = Flask(__name__)

# Function to check if user is in the channel
def user_in_channel(user_id) -> bool:
    url = f"https://api.telegram.org/bot{TOKEN}/getChatMember?chat_id={CHANNEL_ID}&user_id={user_id}"
    try:
        response = requests.get(url).json()
        if response.get('ok') and 'result' in response:
            status = response['result']['status']
            logger.info(f"User {user_id} status in channel: {status}")
            return status in ['member', 'administrator', 'creator']
        logger.warning(f"Unexpected response format: {response}")
        return False
    except Exception as e:
        logger.error(f"Exception while checking user channel status: {e}")
        return False

# Welcome handler function
def welcome(update: Update, context) -> None:
    user_id = update.message.from_user.id
    logger.info(f"Welcome message for user {user_id}")
    if user_in_channel(user_id):
        update.message.reply_text("You are verified as a channel member. Send a movie name to search for it.")
    else:
        update.message.reply_text(f"Please join our channel to use this bot: {CHANNEL_INVITE_LINK}")

# Movie search function
def search_movies(query: str):
    search_url = f"https://www.filmyfly.wales/site-1.html?to-search={query}"
    logger.info(f"Searching URL: {search_url}")
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
        }
        response = requests.get(search_url, headers=headers)  # Removed timeout
        if response.status_code == 200:
            logger.info("Successfully retrieved search results")
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
            logger.info(f"Found {len(movies)} movies")
            return movies
        else:
            logger.error(f"Failed to retrieve search results. Status Code: {response.status_code}")
            return []
    except requests.exceptions.RequestException as e:
        logger.error(f"Error during movie search: {e}")
        return []

# Function to get download links from the movie page
def get_download_links(movie_url: str):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
        }
        response = requests.get(movie_url, headers=headers)  # Removed timeout
        if response.status_code == 200:
            logger.info(f"Successfully retrieved download links for {movie_url}")
            soup = BeautifulSoup(response.content, 'html.parser')
            download_links = set()

            for class_name in ['dl', 'dll', 'dlll']:
                for div in soup.find_all('div', class_=class_name):
                    link = div.find_previous('a', href=True)
                    if link:
                        download_links.add((link['href'], div.get_text(strip=True)))
                    else:
                        download_links.add(('#', div.get_text(strip=True)))

            for a_tag in soup.find_all('a', href=True, class_='dl'):
                download_links.add((a_tag['href'], a_tag.get_text(strip=True)))

            for a_tag in soup.find_all('a', href=True):
                if '▼' in a_tag.get_text() or 'center' in a_tag.get('align', ''):
                    download_links.add((a_tag['href'], a_tag.get_text(strip=True)))

            filtered_links = [
                {'url': url, 'text': text}
                for url, text in download_links
                if url.startswith('http') and 'cank.xyz' not in url
            ]
            logger.info(f"Found {len(filtered_links)} download links")
            return filtered_links
        else:
            logger.error(f"Failed to retrieve download links. Status Code: {response.status_code}")
            return []
    except requests.exceptions.RequestException as e:
        logger.error(f"Error while fetching download links: {e}")
        return []

# Function to search for movies
def find_movie(update: Update, context) -> None:
    query = update.message.text.strip()
    user_id = update.message.from_user.id
    logger.info(f"User {user_id} searched for: {query}")
    
    # Avoid multiple "Searching for movies..." messages
    search_results_message = update.message.reply_text("Searching for movies... Please wait.")
    
    movies_list = search_movies(query)
    
    if movies_list:
        keyboard = [[InlineKeyboardButton(movie['title'], callback_data=str(idx))] for idx, movie in enumerate(movies_list)]
        reply_markup = InlineKeyboardMarkup(keyboard)
        search_results_message.edit_text('Select a movie:', reply_markup=reply_markup)
    else:
        search_results_message.edit_text('Sorry 🙏, No Result Found! Check If You Have Misspelled The Movie Name.')

# Button click handler
def button_click(update: Update, context) -> None:
    query = update.callback_query
    query.answer()
    
    selected_movie_idx = int(query.data)
    selected_movie = search_movies(query.data)[selected_movie_idx]

    title = selected_movie['title']
    image_url = selected_movie.get('image', None)
    download_links = selected_movie.get('download_links', [])

    keyboard = [[InlineKeyboardButton(link['text'], url=link['url'])] for link in download_links]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if image_url:
        query.message.reply_photo(photo=image_url, caption=f"{title}", reply_markup=reply_markup)
    else:
        query.message.reply_text(f"{title}\n\nDownload Links:", reply_markup=reply_markup)

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
