import requests
from bs4 import BeautifulSoup
import time
import json
import os
from datetime import datetime, timedelta

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}
CACHE_DIR = "scraper_cache/wiki"
CACHE_EXPIRY_HOURS = 24

if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)

def get_wiki_data(element_name, element_type="skill"):
    """Gets data from the PoE2 wiki for a given skill or item."""
    sanitized_name = "".join(c if c.isalnum() else "_" for c in element_name)
    cache_file = os.path.join(CACHE_DIR, f"{sanitized_name}_wiki.json")

    # Check cache
    if os.path.exists(cache_file):
        try:
            file_mod_time = datetime.fromtimestamp(os.path.getmtime(cache_file))
            if datetime.now() - file_mod_time < timedelta(hours=CACHE_EXPIRY_HOURS):
                with open(cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error reading wiki cache file {cache_file}: {e}")

    # Construct wiki URL based on element type
    base_url = "https://www.poewiki.net/wiki/"
    if element_type == "skill":
        url = f"{base_url}{element_name.replace(' ', '_')}"
    else:  # item
        url = f"{base_url}{element_name.replace(' ', '_')}"

    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching wiki page {url}: {e}")
        return None

    soup = BeautifulSoup(response.content, 'html.parser')
    
    data = {
        "name": element_name,
        "type": element_type,
        "description": "",
        "mechanics": [],
        "synergies": [],
        "patch_notes": [],
        "source_url": url
    }

    # Extract main content
    content_div = soup.find('div', class_='mw-parser-output')
    if content_div:
        # Get description
        first_p = content_div.find('p')
        if first_p:
            data["description"] = first_p.get_text(strip=True)

        # Get mechanics
        mechanics_header = content_div.find(lambda tag: tag.name in ['h2', 'h3'] and 
                                         tag.find('span', class_='mw-headline') and 
                                         'Mechanics' in tag.find('span', class_='mw-headline').get_text())
        if mechanics_header:
            current = mechanics_header.find_next_sibling()
            while current and current.name not in ['h2', 'h3']:
                if current.name == 'p':
                    data["mechanics"].append(current.get_text(strip=True))
                current = current.find_next_sibling()

        # Get synergies
        synergies_header = content_div.find(lambda tag: tag.name in ['h2', 'h3'] and 
                                          tag.find('span', class_='mw-headline') and 
                                          'Synergies' in tag.find('span', class_='mw-headline').get_text())
        if synergies_header:
            current = synergies_header.find_next_sibling()
            while current and current.name not in ['h2', 'h3']:
                if current.name == 'p':
                    data["synergies"].append(current.get_text(strip=True))
                current = current.find_next_sibling()

        # Get patch notes
        patch_notes_header = content_div.find(lambda tag: tag.name in ['h2', 'h3'] and 
                                            tag.find('span', class_='mw-headline') and 
                                            'Version History' in tag.find('span', class_='mw-headline').get_text())
        if patch_notes_header:
            current = patch_notes_header.find_next_sibling()
            while current and current.name not in ['h2', 'h3']:
                if current.name == 'ul':
                    for li in current.find_all('li'):
                        data["patch_notes"].append(li.get_text(strip=True))
                current = current.find_next_sibling()

    # Cache the results
    try:
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Error writing to wiki cache file {cache_file}: {e}")

    return data

def get_patch_notes():
    """Retrieves all patch notes from the PoE2 forum."""
    cache_file = "scraper_cache/patch_notes.json"
    cache_dir = os.path.dirname(cache_file)
    
    # Create cache directory if it doesn't exist
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)
    
    # Check cache first
    if os.path.exists(cache_file):
        cache_age = time.time() - os.path.getmtime(cache_file)
        if cache_age < 24 * 60 * 60:  # 24 hours
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error reading cache: {e}")
    
    try:
        # Create a session to maintain cookies
        session = requests.Session()
        session.headers.update(HEADERS)
        
        # First visit the forum page to get necessary cookies
        forum_url = "https://www.pathofexile.com/forum/view-forum/2212"
        print(f"Accessing forum page: {forum_url}")
        response = session.get(forum_url)
        response.raise_for_status()
        
        # Now get the patch notes
        patch_notes_url = "https://www.pathofexile.com/forum/view-thread/3781189"
        print(f"Fetching patch notes from: {patch_notes_url}")
        response = session.get(patch_notes_url)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find all patch note threads
        patch_notes = []
        thread_list = soup.find_all('div', class_='thread')
        
        for thread in thread_list:
            try:
                title_elem = thread.find('a', class_='thread_title')
                if not title_elem:
                    continue
                    
                title = title_elem.text.strip()
                if not any(keyword in title.lower() for keyword in ['patch', 'hotfix', 'update']):
                    continue
                
                url = title_elem['href']
                if not url.startswith('http'):
                    url = f"https://www.pathofexile.com{url}"
                
                thread_id = url.split('/')[-1]
                
                # Get the thread content
                thread_response = session.get(url)
                thread_response.raise_for_status()
                thread_soup = BeautifulSoup(thread_response.text, 'html.parser')
                
                # Find the main content
                content_div = thread_soup.find('div', class_='content')
                if content_div:
                    # Extract all text content, preserving structure
                    content = []
                    for element in content_div.stripped_strings:
                        if element.strip():
                            content.append(element.strip())
                    
                    # Get the date
                    date_elem = thread_soup.find('span', class_='post_date')
                    date = date_elem.text.strip() if date_elem else ""
                    
                    patch_notes.append({
                        "title": title,
                        "url": url,
                        "thread_id": thread_id,
                        "date": date,
                        "content": content
                    })
                
                # Be nice to the server
                time.sleep(1)
                
            except Exception as e:
                print(f"Error processing thread: {e}")
                continue
        
        # Sort by date (most recent first)
        patch_notes.sort(key=lambda x: x.get('date', ''), reverse=True)
        
        result = {
            "latest_patch": patch_notes[0] if patch_notes else None,
            "all_patches": patch_notes,
            "source_url": forum_url
        }
        
        # Save to cache
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2)
        except Exception as e:
            print(f"Error saving to cache: {e}")
        
        return result
        
    except Exception as e:
        print(f"Error fetching patch notes: {e}")
        return None

def get_latest_patch_notes():
    """Gets only the latest PoE2 patch notes."""
    all_notes = get_patch_notes()
    if all_notes and all_notes.get("latest_patch"):
        return all_notes["latest_patch"]
    return None

if __name__ == "__main__":
    # Test the scrapers
    test_skill = "Lightning Bolt"
    test_item = "The Whispering Ice"
    
    print(f"\nTesting wiki scraper for skill: {test_skill}")
    skill_data = get_wiki_data(test_skill, "skill")
    print(json.dumps(skill_data, indent=2))
    
    print(f"\nTesting wiki scraper for item: {test_item}")
    item_data = get_wiki_data(test_item, "item")
    print(json.dumps(item_data, indent=2))
    
    print("\nTesting patch notes scraper")
    patch_notes = get_patch_notes()
    print(json.dumps(patch_notes, indent=2)) 