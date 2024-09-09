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

def search_movies(query):
    search_url = f"https://www.filmyfly.wales/site-1.html?to-search={query}"
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
            logging.error(f"Failed to retrieve search results. Status Code: {response.status_code}")
            return []
    except Exception as e:
        logging.error(f"Error during movie search: {e}")
        return []

def get_download_links(movie_url):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
        }
        response = requests.get(movie_url, headers=headers)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            download_links = []

            # Handle <a> tags with classes 'dl', 'dll', 'dlll'
            for class_name in ['dl', 'dll', 'dlll']:
                for div in soup.find_all('div', class_=class_name):
                    link = div.find_previous('a', href=True)
                    if link:
                        download_links.append({
                            'url': link['href'],
                            'text': div.get_text(strip=True)
                        })
                    else:
                        download_links.append({
                            'url': '#',  # Placeholder URL for <div> without an <a> tag
                            'text': div.get_text(strip=True)
                        })

            # Handle <a> tags with the download button format
            for a_tag in soup.find_all('a', href=True):
                div_tag = a_tag.find('div')
                if div_tag and div_tag.has_attr('class'):
                    download_links.append({
                        'url': a_tag['href'],
                        'text': div_tag.get_text(strip=True)
                    })
                
                # Handle cases with ▼ and center alignments
                if '▼' in a_tag.get_text() or 'center' in a_tag.get('align', ''):
                    download_links.append({
                        'url': a_tag['href'],
                        'text': a_tag.get_text(strip=True)
                    })

            return download_links
        else:
            logging.error(f"Failed to retrieve download links. Status Code: {response.status_code}")
            return []
    except Exception as e:
        logging.error(f"Error while fetching download links: {e}")
        return []

def find_movie(update: Update, context) -> None:
    query = update.message.text.strip()
    user_id = update.message.from_user.id
    search_results = update.message.reply_text("Searching for movies... Please wait.")
    movies_list = search_movies(query)
    
    if movies_list:
        search_results_cache[user_id] = movies_list
        keyboard = []
        for idx, movie in enumerate(movies_list):
            keyboard.append([InlineKeyboardButton(movie['title'], callback_data=str(idx))])
        reply_markup = InlineKeyboardMarkup(keyboard)
        search_results.edit_text('Select a movie:', reply_markup=reply_markup)
    else:
        search_results.edit_text('Sorry 🙏, No Result Found! Check If You Have Misspelled The Movie Name.')

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
    setup_dispatcher().process_update(update)
    return 'ok'

@app.route('/setwebhook', methods=['GET', 'POST'])
def set_webhook():
    webhook_url = f'https://yourdomain.com/{TOKEN}'  # Update with your deployment URL
    s = bot.setWebhook(webhook_url)
    if s:
        return "Webhook setup ok"
    else:
        return "Webhook setup failed"

if __name__ == '__main__':
    app.run(debug=True)
