import requests
from bs4 import BeautifulSoup

url_list = {}

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Referer': 'https://mkvcinemas.cat/',
}

def search_movies(query):
    movies_list = []
    try:
        search_url = f"https://mkvcinemas.cat/?s={query.replace(' ', '+')}"
        response = requests.get(search_url, headers=headers)
        website = BeautifulSoup(response.text, "html.parser")
        
        print(f"[DEBUG] Fetching URL: {search_url}")
        print(f"[DEBUG] Response Status Code: {response.status_code}")
        print(f"[DEBUG] Response Text: {response.text[:1000]}")  # Print first 1000 characters for inspection
        
        movies = website.find_all("a", {'class': 'ml-mask jt'})
        print(f"[DEBUG] Found Movies: {len(movies)}")
        
        for index, movie in enumerate(movies):
            movie_details = {}
            title_span = movie.find("span", {'class': 'mli-info'})
            if title_span:
                movie_details["id"] = f"link{index}"
                movie_details["title"] = title_span.text
                url_list[movie_details["id"]] = movie['href']
                movies_list.append(movie_details)
            else:
                print(f"[DEBUG] No title span found for movie {index}")
    except Exception as e:
        print(f"[ERROR] Exception in search_movies: {e}")
    return movies_list

def get_movie(movie_id):
    movie_details = {}
    try:
        movie_url = url_list[movie_id]
        movie_page_link = BeautifulSoup(requests.get(movie_url, headers=headers).text, "html.parser")
        
        print(f"[DEBUG] Fetching Movie Page URL: {movie_url}")
        print(f"[DEBUG] Response Text: {requests.get(movie_url, headers=headers).text[:1000]}")  # Print first 1000 characters for inspection
        
        if movie_page_link:
            title_div = movie_page_link.find("div", {'class': 'mvic-desc'})
            if title_div:
                title = title_div.h3.text
                movie_details["title"] = title
            
            final_links = {}
            
            # Fetching specific links with class 'gdlink'
            links = movie_page_link.find_all("a", {'class': 'gdlink'})
            print(f"[DEBUG] Found gdlink Links: {len(links)}")
            for i in links:
                final_links[f"{i.text}"] = i['href']
            
            # Fetching additional links with class 'button'
            button_links = movie_page_link.find_all("a", {'class': 'button'})
            print(f"[DEBUG] Found button Links: {len(button_links)}")
            for i in button_links:
                if "href" in i.attrs and "title" in i.attrs:
                    final_links[f"{i.text} [{i['title']}]"] = i['href']
            
            # Re-add the "Stream Online" link
            stream_section = movie_page_link.find(text="Stream Online Links:")
            if stream_section:
                stream_links = stream_section.find_next("a")
                if stream_links:
                    final_links["🔴 Stream Online"] = stream_links['href']
            
            movie_details["links"] = final_links
        else:
            print(f"[DEBUG] No movie page link found for {movie_id}")
    except Exception as e:
        print(f"[ERROR] Exception in get_movie: {e}")
    return movie_details
