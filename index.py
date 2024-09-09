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
CHANNEL_ID = "-1002170013697"
CHANNEL_INVITE_LINK = "https://t.me/+dUXsdWu9dlk4ZTk9"
bot = Bot(TOKEN)

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

# Function to extract download URL and text from the <a> tag with class 'dl'
def extract_download_url(item):
    download_tag = item.find('a', class_='dl')
    download_link = download_tag['href'] if download_tag else None
    download_text = download_tag.get_text(strip=True) if download_tag else "Download"
    return download_link, download_text

# Function to search for movies on the external website
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
                # Extract the title
                title_tag = item.find('a', href=True).find_next('b').find('span')
                title = title_tag.get_text(strip=True) if title_tag else "No Title"
                
                # Extract the image URL
                image_tag = item.find('img')
                image_url = image_tag['src'] if image_tag else None

                # Extract the download link using extract_download_url
                download_link, download_text = extract_download_url(item)

                movies.append({
                    'title': title,
                    'image': image_url,
                    'download_link': download_link,
                    'download_text': download_text
                })
            return movies
        else:
            return []
    except Exception as e:
        logging.error(f"Error during movie search: {e}")
        return []

# Function to handle movie search results
def find_movie(update: Update, context) -> None:
    query = update.message.text.strip()
    user_id = update.message.from_user.id
    search_results = update.message.reply_text("Searching for movies... Please wait.")
    movies_list = search_movies(query)
    
    if movies_list:
        # Save search results in cache
        search_results_cache[user_id] = movies_list

        # Create Inline Keyboard with movie titles
        keyboard = []
        for idx, movie in enumerate(movies_list):
            keyboard.append([InlineKeyboardButton(movie['title'], callback_data=str(idx))])

        reply_markup = InlineKeyboardMarkup(keyboard)
        search_results.edit_text('Select a movie:', reply_markup=reply_markup)
    else:
        search_results.edit_text('Sorry 🙏, No Result Found!\nCheck If You Have Misspelled The Movie Name.')

# Callback handler for button click events
def button_click(update: Update, context) -> None:
    query = update.callback_query
    query.answer()

    user_id = query.from_user.id
    selected_movie_idx = int(query.data)
    
    # Logging for debugging
    logging.info(f"Selected movie index: {selected_movie_idx}")
    
    if user_id in search_results_cache:
        selected_movie = search_results_cache[user_id][selected_movie_idx]

        # Send the selected movie details (image, title, and download link as inline button)
        title = selected_movie['title']
        image_url = selected_movie.get('image', None)
        download_link = selected_movie.get('download_link', "#")
        download_text = selected_movie.get('download_text', "Download")

        # Create InlineKeyboard with the download link
        keyboard = [[InlineKeyboardButton(download_text, url=download_link)]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Send image and title with inline button for the download link
        if image_url:
            query.message.reply_photo(photo=image_url, caption=f"{title}", reply_markup=reply_markup)
        else:
            query.message.reply_text(f"{title}", reply_markup=reply_markup)
    else:
        query.message.reply_text("No data found. Please search again.")

# Setup dispatcher for handling Telegram commands and messages
def setup_dispatcher():
    dispatcher = Dispatcher(bot, None, use_context=True)
    dispatcher.add_handler(CommandHandler('start', welcome))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, find_movie))
    dispatcher.add_handler(CallbackQueryHandler(button_click))
    return dispatcher

# Flask app for webhook setup
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
