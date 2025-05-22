import requests
from bs4 import BeautifulSoup
import time
import json
import os
from datetime import datetime, timedelta

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}
CACHE_DIR = "scraper_cache/community"
CACHE_EXPIRY_HOURS = 24

if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)

def get_reddit_posts(search_term, subreddit="pathofexile2", limit=5):
    """Gets relevant Reddit posts about a specific skill or item."""
    sanitized_term = "".join(c if c.isalnum() else "_" for c in search_term)
    cache_file = os.path.join(CACHE_DIR, f"reddit_{sanitized_term}.json")
    
    # Check cache
    if os.path.exists(cache_file):
        try:
            file_mod_time = datetime.fromtimestamp(os.path.getmtime(cache_file))
            if datetime.now() - file_mod_time < timedelta(hours=CACHE_EXPIRY_HOURS):
                with open(cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error reading Reddit cache file {cache_file}: {e}")

    url = f"https://www.reddit.com/r/{subreddit}/search.json"
    params = {
        'q': search_term,
        'restrict_sr': 'on',
        'sort': 'relevance',
        't': 'all',
        'limit': limit
    }
    
    try:
        response = requests.get(url, headers=HEADERS, params=params, timeout=15)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching Reddit posts: {e}")
        return None

    data = {
        "search_term": search_term,
        "subreddit": subreddit,
        "posts": [],
        "source_url": url
    }

    try:
        json_data = response.json()
        for post in json_data.get('data', {}).get('children', []):
            post_data = post.get('data', {})
            data["posts"].append({
                "title": post_data.get('title', ''),
                "url": f"https://reddit.com{post_data.get('permalink', '')}",
                "score": post_data.get('score', 0),
                "num_comments": post_data.get('num_comments', 0),
                "created_utc": post_data.get('created_utc', 0),
                "selftext": post_data.get('selftext', '')
            })
    except Exception as e:
        print(f"Error parsing Reddit response: {e}")
        return None

    # Cache the results
    try:
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Error writing to Reddit cache file {cache_file}: {e}")

    return data

def get_forum_posts(search_term, limit=5):
    """Gets relevant forum posts from the official PoE forums."""
    sanitized_term = "".join(c if c.isalnum() else "_" for c in search_term)
    cache_file = os.path.join(CACHE_DIR, f"forum_{sanitized_term}.json")
    
    # Check cache
    if os.path.exists(cache_file):
        try:
            file_mod_time = datetime.fromtimestamp(os.path.getmtime(cache_file))
            if datetime.now() - file_mod_time < timedelta(hours=CACHE_EXPIRY_HOURS):
                with open(cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error reading forum cache file {cache_file}: {e}")

    url = "https://www.pathofexile.com/forum/search"
    params = {
        'q': search_term,
        'forum': 'poe2',
        'sort': 'relevance',
        'limit': limit
    }
    
    try:
        response = requests.get(url, headers=HEADERS, params=params, timeout=15)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching forum posts: {e}")
        return None

    soup = BeautifulSoup(response.content, 'html.parser')
    
    data = {
        "search_term": search_term,
        "posts": [],
        "source_url": url
    }

    # Extract forum posts
    post_divs = soup.find_all('div', class_='forumPost')
    for post_div in post_divs[:limit]:
        title_div = post_div.find('div', class_='title')
        content_div = post_div.find('div', class_='content')
        
        if title_div and content_div:
            data["posts"].append({
                "title": title_div.get_text(strip=True),
                "url": title_div.find('a')['href'] if title_div.find('a') else '',
                "content": content_div.get_text(strip=True),
                "author": post_div.find('div', class_='author').get_text(strip=True) if post_div.find('div', class_='author') else 'Unknown'
            })

    # Cache the results
    try:
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Error writing to forum cache file {cache_file}: {e}")

    return data

def get_build_guides(skill_name=None, class_name=None, limit=5):
    """Gets build guides from popular PoE2 community sites."""
    cache_key = f"guides_{skill_name or 'all'}_{class_name or 'all'}"
    cache_file = os.path.join(CACHE_DIR, f"{cache_key}.json")
    
    # Check cache
    if os.path.exists(cache_file):
        try:
            file_mod_time = datetime.fromtimestamp(os.path.getmtime(cache_file))
            if datetime.now() - file_mod_time < timedelta(hours=CACHE_EXPIRY_HOURS):
                with open(cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error reading guides cache file {cache_file}: {e}")

    # List of community sites to scrape
    sites = [
        {
            "name": "poe2db",
            "url": "https://poe2db.tw/us/builds",
            "params": {
                "skill": skill_name,
                "class": class_name
            }
        },
        {
            "name": "poe-vault",
            "url": "https://www.poe-vault.com/poe2/builds",
            "params": {
                "skill": skill_name,
                "class": class_name
            }
        }
    ]
    
    data = {
        "skill": skill_name,
        "class": class_name,
        "guides": [],
        "sources": []
    }

    for site in sites:
        try:
            response = requests.get(site["url"], headers=HEADERS, params=site["params"], timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Site-specific parsing logic
            if site["name"] == "poe2db":
                guide_divs = soup.find_all('div', class_='build-card')
                for guide_div in guide_divs[:limit]:
                    title_div = guide_div.find('div', class_='build-title')
                    if title_div:
                        data["guides"].append({
                            "title": title_div.get_text(strip=True),
                            "url": title_div.find('a')['href'] if title_div.find('a') else '',
                            "author": guide_div.find('div', class_='author').get_text(strip=True) if guide_div.find('div', class_='author') else 'Unknown',
                            "source": site["name"]
                        })
            
            elif site["name"] == "poe-vault":
                guide_divs = soup.find_all('div', class_='build-guide')
                for guide_div in guide_divs[:limit]:
                    title_div = guide_div.find('h2')
                    if title_div:
                        data["guides"].append({
                            "title": title_div.get_text(strip=True),
                            "url": title_div.find('a')['href'] if title_div.find('a') else '',
                            "author": guide_div.find('div', class_='author').get_text(strip=True) if guide_div.find('div', class_='author') else 'Unknown',
                            "source": site["name"]
                        })
            
            data["sources"].append(site["name"])
            
        except Exception as e:
            print(f"Error fetching guides from {site['name']}: {e}")
            continue

    # Cache the results
    try:
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Error writing to guides cache file {cache_file}: {e}")

    return data

if __name__ == "__main__":
    # Test the scrapers
    test_skill = "Lightning Bolt"
    test_class = "Sorcerer"
    
    print(f"\nTesting Reddit scraper for: {test_skill}")
    reddit_data = get_reddit_posts(test_skill)
    print(json.dumps(reddit_data, indent=2))
    
    print(f"\nTesting forum scraper for: {test_skill}")
    forum_data = get_forum_posts(test_skill)
    print(json.dumps(forum_data, indent=2))
    
    print(f"\nTesting build guides scraper for: {test_skill} {test_class}")
    guides_data = get_build_guides(test_skill, test_class)
    print(json.dumps(guides_data, indent=2)) 