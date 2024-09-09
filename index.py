import os
import requests
from bs4 import BeautifulSoup
from flask import Flask, request
from telegram import Bot, Update
from telegram.ext import CommandHandler, MessageHandler, Filters, Dispatcher, CallbackQueryHandler
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

# Welcome message when the user joins
def welcome(update: Update, context) -> None:
    user_id = update.message.from_user.id
    if user_in_channel(user_id):
        user_membership_status[user_id] = True
        update.message.reply_text("You are verified as a channel member. Send a movie name to search for it.")
    else:
        user_membership_status[user_id] = False
        update.message.reply_text(f"Please join our channel to use this bot: {CHANNEL_INVITE_LINK}")

# Function to check if a user is in the channel
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

# Function to scrape the movie search results
def search_movies(query):
    search_url = f"https://www.filmyfly.wales/site-1.html?to-search={query}"
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
        }
        logging.info(f"Sending request to URL: {search_url}")
        response = requests.get(search_url, headers=headers, timeout=10)
        logging.info(f"Received response with status code: {response.status_code}")

        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')

            movies = []
            for item in soup.find_all('div', class_='A2'):
                # Extracting the title
                title_tag = item.find('a', href=True).find_next('b').find('span')
                title = title_tag.get_text(strip=True) if title_tag else "No Title"
                
                # Extracting the image URL
                image_tag = item.find('img')
                image_url = image_tag['src'] if image_tag else None

                # Extracting download link
                download_tag = item.find('a', class_='dl')
                download_link = download_tag['href'] if download_tag else None
                download_text = download_tag.get_text(strip=True) if download_tag else "Download"

                movies.append({
                    'title': title,
                    'image': image_url,
                    'download_link': download_link,
                    'download_text': download_text
                })
            logging.info(f"Found {len(movies)} movies.")
            return movies
        else:
            logging.error("Failed to retrieve the search results.")
            return []
    except Exception as e:
        logging.error(f"Error during movie search: {e}")
        return []

# Function to handle the movie search
def find_movie(update: Update, context) -> None:
    query = update.message.text.strip()
    user_id = update.message.from_user.id
    search_results_message = update.message.reply_text("Searching for movies... Please wait.")
    
    movies_list = search_movies(query)
    
    if movies_list:
        # Save search results in cache
        search_results_cache[user_id] = movies_list

        # Create response message with the list of movies and download links
        message = "Select a movie:\n\n"
        for idx, movie in enumerate(movies_list):
            message += f"{idx+1}. {movie['title']}\n"
            message += f"Download link: {movie['download_link']}\n\n"
        
        search_results_message.edit_text(message)
    else:
        search_results_message.edit_text('Sorry 🙏, No Result Found!\nCheck If You Have Misspelled The Movie Name.')

# Function to handle button clicks
def button_click(update: Update, context) -> None:
    query = update.callback_query
    query.answer()

    user_id = query.from_user.id
    selected_movie_idx = int(query.data)
    
    if user_id in search_results_cache:
        selected_movie = search_results_cache[user_id][selected_movie_idx]

        # Send the selected movie details (title and download link)
        title = selected_movie['title']
        download_link = selected_movie.get('download_link', "#")

        # Send title and download link as plain text
        query.message.reply_text(f"{title}\n\nDownload link: {download_link}")
    else:
        query.message.reply_text("No data found. Please search again.")

# Setup the dispatcher and handlers
def setup_dispatcher():
    dispatcher = Dispatcher(bot, None, use_context=True)
    dispatcher.add_handler(CommandHandler('start', welcome))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, find_movie))
    dispatcher.add_handler(CallbackQueryHandler(button_click))
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
    webhook_url = f'https://your-deployment-url.com/{TOKEN}'
    s = bot.setWebhook(webhook_url)
    if s:
        return "Webhook setup ok"
    else:
        return "Webhook setup failed"

if __name__ == '__main__':
    app.run(debug=True)
