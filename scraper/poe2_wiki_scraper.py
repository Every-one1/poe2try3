import requests
from bs4 import BeautifulSoup
import time
import json
import os
from datetime import datetime, timedelta
import re # Make sure this import is present

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}
CACHE_DIR = "scraper_cache/wiki" # Ensure this is specific to wiki
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

    base_url = "https://www.poewiki.net/wiki/"
    page_slug = element_name.replace(' ', '_')
    url = f"{base_url}{page_slug}"

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
        "mechanics": "", 
        "lore": "", 
        "version_history": [], 
        "source_url": url
    }

    content_div = soup.find('div', class_='mw-parser-output')
    if content_div:
        first_p = content_div.find('p', recursive=False)
        if first_p:
            data["description"] = first_p.get_text(strip=True)

        mechanics_header = content_div.find(lambda tag: tag.name in ['h2', 'h3'] and 
                                         tag.find('span', class_='mw-headline', string=re.compile(r'Mechanics', re.I)))
        if mechanics_header:
            elements = []
            current = mechanics_header.find_next_sibling()
            while current and current.name not in ['h2', 'h3']:
                if current.name == 'p' or current.name == 'ul':
                    elements.append(current.get_text(separator='\n', strip=True))
                current = current.find_next_sibling()
            data["mechanics"] = "\n".join(elements)

        lore_header = content_div.find(lambda tag: tag.name in ['h2', 'h3'] and 
                                   tag.find('span', class_='mw-headline', string=re.compile(r'Lore|Background', re.I)))
        if lore_header:
            elements = []
            current = lore_header.find_next_sibling()
            while current and current.name not in ['h2', 'h3']:
                if current.name == 'p' or current.name == 'ul':
                    elements.append(current.get_text(separator='\n', strip=True))
                current = current.find_next_sibling()
            data["lore"] = "\n".join(elements)
            
        version_header = content_div.find(lambda tag: tag.name in ['h2', 'h3'] and 
                                        tag.find('span', class_='mw-headline', string=re.compile(r'Version history', re.I)))
        if version_header:
            elements = []
            current = version_header.find_next_sibling()
            while current and current.name not in ['h2', 'h3']:
                if current.name == 'ul': 
                    for li_item in current.find_all('li', recursive=False):
                        elements.append(li_item.get_text(separator='\n', strip=True))
                elif current.name == 'p': 
                     elements.append(current.get_text(separator='\n', strip=True))
                current = current.find_next_sibling()
            data["version_history"] = elements

    try:
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Error writing to wiki cache file {cache_file}: {e}")

    return data

if __name__ == "__main__":
    test_skill = "Lightning Bolt" 
    print(f"\nTesting wiki scraper for skill: {test_skill}")
    skill_data = get_wiki_data(test_skill, "skill")
    if skill_data:
        print(json.dumps(skill_data, indent=2))
    else:
        print(f"No data found for {test_skill}")

    test_item = "The Whispering Ice" 
    print(f"\nTesting wiki scraper for item: {test_item}")
    item_data = get_wiki_data(test_item, "item")
    if item_data:
        print(json.dumps(item_data, indent=2))
    else:
        print(f"No data found for {test_item}")
