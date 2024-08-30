import requests
from bs4 import BeautifulSoup

url_list = {}

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Referer': 'https://1flix.to/',
}

def search_movies(query):
    movies_list = []
    try:
        search_url = f"https://1flix.to/search/{query.replace(' ', '+')}"
        response = requests.get(search_url, headers=headers)
        website = BeautifulSoup(response.text, "html.parser")
        
        print(f"[DEBUG] Fetching URL: {search_url}")
        print(f"[DEBUG] Response Status Code: {response.status_code}")
        print(f"[DEBUG] Response Text: {response.text[:1000]}")  # Print first 1000 characters for inspection
        
        # Find all movie anchor tags
        movies = website.find_all("a", {'class': 'film-poster-ahref flw-item-tip'})
        print(f"[DEBUG] Found Movies: {len(movies)}")
        
        for index, movie in enumerate(movies):
            movie_details = {}
            title = movie.get('title')
            href = movie.get('href')
            img_tag = movie.find("img")  # Assuming image is in <img> tag inside <a>
            img_url = img_tag['src'] if img_tag and 'src' in img_tag.attrs else None
            
            if title and href:
                movie_details["id"] = f"link{index}"
                movie_details["title"] = title
                full_url = f"https://1flix.to{href}" if href.startswith('/') else href
                movie_details["url"] = full_url
                movie_details["image"] = img_url
                url_list[movie_details["id"]] = full_url
                movies_list.append(movie_details)
            else:
                print(f"[DEBUG] No valid title, href, or image found for movie {index}")
    except Exception as e:
        print(f"[ERROR] Exception in search_movies: {e}")
    return movies_list

def get_movie(movie_id):
    movie_details = {}
    try:
        movie_url = url_list.get(movie_id)
        if not movie_url:
            print(f"[ERROR] No URL found for movie ID: {movie_id}")
            return movie_details
        
        response = requests.get(movie_url, headers=headers)
        movie_page_link = BeautifulSoup(response.text, "html.parser")
        
        print(f"[DEBUG] Fetching Movie Page URL: {movie_url}")
        print(f"[DEBUG] Response Text: {response.text[:1000]}")  # Print first 1000 characters for inspection
        
        if movie_page_link:
            # Adjust based on actual HTML structure for the movie title
            title_div = movie_page_link.find("div", {'class': 'mvic-desc'})
            if title_div and title_div.h3:
                movie_details["title"] = title_div.h3.text
            
            final_links = {}
            
            # Adjust the class to match the links section
            links = movie_page_link.find_all("a", {'class': 'some-link-class'})  # Replace with actual class name
            print(f"[DEBUG] Found gdlink Links: {len(links)}")
            for i in links:
                final_links[f"{i.text}"] = i['href']
            
            # Adjust for other link/button sections
            button_links = movie_page_link.find_all("a", {'class': 'button'})  # Example, replace with actual class
            print(f"[DEBUG] Found button Links: {len(button_links)}")
            for i in button_links:
                if "href" in i.attrs and "title" in i.attrs:
                    final_links[f"{i.text} [{i['title']}]"] = i['href']
            
            # Stream online section (adjust as needed)
            stream_section = movie_page_link.find(text="Stream Online Links:")  # Replace if different
            if stream_section:
                stream_links = stream_section.find_next("a")
                if stream_links and stream_links.has_attr('href'):
                    final_links["🔴 Stream Online"] = stream_links['href']
            
            movie_details["links"] = final_links
        else:
            print(f"[DEBUG] No movie page link found for {movie_id}")
    except Exception as e:
        print(f"[ERROR] Exception in get_movie: {e}")
    return movie_details

# Example usage
search_results = search_movies("hello")
print(f"Search Results: {search_results}")

# To get more details of a specific movie from the search results
if search_results:
    movie_id = search_results[0]['id']
    movie_info = get_movie(movie_id)
    print(f"Movie Info: {movie_info}")
