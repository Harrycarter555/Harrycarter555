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

        # Find all movie elements
        movies = website.find_all("a", {'class': 'film-poster-ahref'})
        print(f"[DEBUG] Found Movies: {len(movies)}")

        for index, movie in enumerate(movies):
            movie_details = {}
            title = movie['title']
            poster_img = movie.find("i", {'class': 'fa fa-play'}).parent.find("img")  # Adjust this line based on actual HTML

            if poster_img and poster_img.has_attr('src'):
                image_url = poster_img['src']
            else:
                image_url = "default_image_url"  # Replace with a default image if no image is found

            movie_details["id"] = f"link{index}"
            movie_details["title"] = title
            movie_details["image"] = image_url  # Use the extracted image URL

            url_list[movie_details["id"]] = movie['href']
            movies_list.append(movie_details)
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
            title_div = movie_page_link.find("div", {'class': 'mvic-desc'})  # Adjust based on actual HTML
            if title_div:
                title = title_div.h3.text
                movie_details["title"] = title

            final_links = {}

            # Adjust the parsing for links accordingly.
            links = movie_page_link.find_all("a", {'class': 'some-link-class'})  # Adjust based on actual HTML
            print(f"[DEBUG] Found Links: {len(links)}")
            for i in links:
                final_links[f"{i.text}"] = i['href']

            # Adjust additional link parsing based on actual HTML structure.
            button_links = movie_page_link.find_all("a", {'class': 'button'})  # Example
            print(f"[DEBUG] Found Button Links: {len(button_links)}")
            for i in button_links:
                if "href" in i.attrs and "title" in i.attrs:
                    final_links[f"{i.text} [{i['title']}]"] = i['href']

            movie_details["links"] = final_links
        else:
            print(f"[DEBUG] No movie page link found for {movie_id}")
    except Exception as e:
        print(f"[ERROR] Exception in get_movie: {e}")
    return movie_details
