import requests
from bs4 import BeautifulSoup

def get_movie_links_website1(query):
    search_url = f"https://https://luxmovies.info/search?q={query}"
    response = requests.get(search_url)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Assuming the download links are in <a> tags with class 'download-link'
    links = []
    for a_tag in soup.find_all('a', class_='download-link'):
        link = a_tag['href']
        links.append(link)
    
    return links
