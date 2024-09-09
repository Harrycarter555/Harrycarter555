import requests
from bs4 import BeautifulSoup
import logging

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
            download_links = set()  # Use a set to avoid duplicates

            # Handle <a> tags with classes 'dl', 'dll', 'dlll'
            for class_name in ['dl', 'dll', 'dlll']:
                for div in soup.find_all('div', class_=class_name):
                    link = div.find_previous('a', href=True)
                    if link:
                        download_links.add((link['href'], div.get_text(strip=True)))
                    else:
                        download_links.add(('#', div.get_text(strip=True)))

            # Handle <a> tags with the download button format
            for a_tag in soup.find_all('a', href=True, class_='dl'):
                download_links.add((a_tag['href'], a_tag.get_text(strip=True)))
            
            # Handle cases with ▼ and center alignments
            for a_tag in soup.find_all('a', href=True):
                if '▼' in a_tag.get_text() or 'center' in a_tag.get('align', ''):
                    download_links.add((a_tag['href'], a_tag.get_text(strip=True)))

            # Filter out invalid URLs (e.g., URLs without host, specific invalid URLs)
            filtered_links = [
                {'url': url, 'text': text}
                for url, text in download_links
                if url.startswith('http') and 'cank.xyz' not in url  # Exclude specific invalid URLs
            ]
            return filtered_links
        else:
            logging.error(f"Failed to retrieve download links. Status Code: {response.status_code}")
            return []
    except Exception as e:
        logging.error(f"Error while fetching download links: {e}")
        return []
