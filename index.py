import os
import requests
from bs4 import BeautifulSoup
from flask import Flask, request
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from dotenv import load_dotenv
import logging
import asyncio

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
    if user_in_channel(user_id):
        user_membership_status[user_id] = True
        update.message.reply_text("Welcome! You are verified as a channel member. Send a movie name to search for it.")
    else:
        user_membership_status[user_id] = False
        update.message.reply_text(f"Please join our channel to use this bot: {CHANNEL_INVITE_LINK}")

def find_movie(update: Update, context) -> None:
    if update.message.text.startswith('/'):
        return
    
    query = update.message.text.strip()
    user_id = update.message.from_user.id

    search_results = update.message.reply_text("Searching for movies... Please wait.")
    movies_list = search_movies(query)

    if movies_list:
        search_results_cache[user_id] = movies_list
        keyboard = [[InlineKeyboardButton(movie['title'], callback_data=str(idx))] for idx, movie in enumerate(movies_list)]
        reply_markup = InlineKeyboardMarkup(keyboard)
        search_results.edit_text('Select a movie:', reply_markup=reply_markup)
    else:
        search_results.edit_text('Sorry 🙏, No Result Found! Check If You Have Misspelled The Movie Name.')

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
    search_url = f"https://www.filmyfly.wales/site-1.html?to-search={query}"
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'}
        response = requests.get(search_url, headers=headers)
        response.raise_for_status()
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
            movies.append({'title': title, 'url': movie_url, 'image': image_url, 'download_links': download_links})
        return movies
    except requests.RequestException as e:
        logger.error(f"Failed to retrieve search results: {e}")
        return []
    except Exception as e:
        logger.error(f"Error during movie search: {e}")
        return []

def get_download_links(movie_url: str):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'}
        response = requests.get(movie_url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        download_links = set()
        for class_name in ['dl', 'dll', 'dlll']:
            for div in soup.find_all('div', class_=class_name):
                link = div.find_previous('a', href=True)
                download_links.add((link['href'], div.get_text(strip=True)) if link else ('#', div.get_text(strip=True)))
        for a_tag in soup.find_all('a', href=True, class_='dl'):
            download_links.add((a_tag['href'], a_tag.get_text(strip=True)))
        for a_tag in soup.find_all('a', href=True):
            if '▼' in a_tag.get_text() or 'center' in a_tag.get('align', ''):
                download_links.add((a_tag['href'], a_tag.get_text(strip=True)))
        filtered_links = [{'url': url, 'text': text} for url, text in download_links if url.startswith('http') and 'cank.xyz' not in url]
        return filtered_links
    except requests.RequestException as e:
        logger.error(f"Failed to retrieve download links: {e}")
        return []
    except Exception as e:
        logger.error(f"Error while fetching download links: {e}")
        return []

def button_click(update: Update, context) -> None:
    query = update.callback_query
    query.answer()
    user_id = query.from_user.id
    selected_movie_idx = int(query.data)
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

def setup_dispatcher() -> Application:
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler('start', welcome))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, find_movie))
    application.add_handler(CallbackQueryHandler(button_click))
    return application

app = Flask(__name__)

@app.route('/')
def index():
    return 'Hello World!'

@app.route(f'/{TOKEN}', methods=['POST'])
def respond():
    update = Update.de_json(request.get_json(force=True), bot)
    asyncio.run(setup_dispatcher().process_update(update))
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
    app.run(debug=True, port=int(os.getenv("PORT", 5000)))
