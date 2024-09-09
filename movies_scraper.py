import aiohttp
import asyncio
from bs4 import BeautifulSoup
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

async def search_movies(query):
    """
    Search movies based on the provided query from the target website.
    
    Args:
        query (str): The movie name to search.
    
    Returns:
        list: A list of dictionaries containing movie details like title, URL, image URL, and download links.
    """
    search_url = f"https://www.filmyfly.wales/site-1.html?to-search={query.replace(' ', '+')}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
    }
    movies = []

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(search_url, headers=headers, timeout=10) as response:
                logging.debug(f"Request sent to: {search_url}, Status code: {response.status}")
                
                if response.status == 200:
                    content = await response.text()
                    soup = BeautifulSoup(content, 'html.parser')
                    
                    # Log the first 500 characters of the page content for debugging
                    logging.debug(f"Received content (first 500 chars): {content[:500]}")
                    
                    # Parsing movie entries
                    for item in soup.find_all('div', class_='A2'):
                        logging.debug(f"Movie div found: {item}")
                        title_tag = item.find('a', href=True).find_next('b').find('span')
                        title = title_tag.get_text(strip=True) if title_tag else "No Title"
                        movie_url_tag = item.find('a', href=True)
                        movie_url = "https://www.filmyfly.wales" + movie_url_tag['href'] if movie_url_tag else "#"
                        image_tag = item.find('img')
                        image_url = image_tag['src'] if image_tag else None
                        download_links = await get_download_links(session, movie_url)
                        movies.append({
                            'title': title,
                            'url': movie_url,
                            'image': image_url,
                            'download_links': download_links
                        })
                    
                    logging.debug(f"Parsed movies: {movies}")
                    return movies
                else:
                    logging.error(f"Failed to retrieve search results. Status Code: {response.status}")
                    return []
        except asyncio.TimeoutError:
            logging.error("Request timed out.")
            return []
        except Exception as e:
            logging.error(f"An exception occurred: {e}")
            return []

async def get_download_links(session, movie_url):
    """
    Retrieve download links from a specific movie page.
    
    Args:
        session (aiohttp.ClientSession): The active session for making HTTP requests.
        movie_url (str): The URL of the movie page.
    
    Returns:
        list: A list of dictionaries containing download link text and URLs.
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
        }
        async with session.get(movie_url, headers=headers) as response:
            logging.debug(f"Request sent to: {movie_url}, Status code: {response.status}")
            
            if response.status == 200:
                soup = BeautifulSoup(await response.text(), 'html.parser')
                download_links = set()

                # Extract download links from specific divs and tags
                for class_name in ['dl', 'dll', 'dlll']:
                    for div in soup.find_all('div', class_=class_name):
                        link = div.find_previous('a', href=True)
                        if link:
                            download_links.add((link['href'], div.get_text(strip=True)))
                        else:
                            download_links.add(('#', div.get_text(strip=True)))

                # Adding more download link patterns
                for a_tag in soup.find_all('a', href=True, class_='dl'):
                    download_links.add((a_tag['href'], a_tag.get_text(strip=True)))

                for a_tag in soup.find_all('a', href=True):
                    if '▼' in a_tag.get_text() or 'center' in a_tag.get('align', ''):
                        download_links.add((a_tag['href'], a_tag.get_text(strip=True)))

                # Filter links (remove non-http links or specific blacklisted URLs)
                filtered_links = [
                    {'url': url, 'text': text}
                    for url, text in download_links
                    if url.startswith('http') and 'cank.xyz' not in url
                ]
                logging.debug(f"Filtered download links: {filtered_links}")
                return filtered_links
            else:
                logging.error(f"Failed to retrieve download links. Status Code: {response.status}")
                return []
    except Exception as e:
        logging.error(f"Error while fetching download links: {e}")
        return []

# Example of how to run the asynchronous search
if __name__ == "__main__":
    query = "example movie"
    loop = asyncio.get_event_loop()
    movies = loop.run_until_complete(search_movies(query))
    
    if movies:
        for movie in movies:
            print(f"Title: {movie['title']}, URL: {movie['url']}, Image: {movie['image']}, Download Links: {movie['download_links']}")
    else:
        print("An error occurred while searching for movies.")
