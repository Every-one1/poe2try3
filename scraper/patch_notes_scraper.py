import requests
from bs4 import BeautifulSoup
import time
import json
import os
from datetime import datetime, timedelta # Added timedelta

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

CACHE_DIR = "scraper_cache/patch_notes" # Modified CACHE_DIR
FORUM_URL = "https://www.pathofexile.com/forum/view-forum/2212" # Primary source for patch notes
CACHE_FILENAME = "all_patch_notes.json" # Cache filename

if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)

def get_patch_notes():
    """Retrieves all patch notes from the PoE2 forum."""
    cache_file = os.path.join(CACHE_DIR, CACHE_FILENAME)
    
    # Check cache first
    if os.path.exists(cache_file):
        try:
            file_mod_time = datetime.fromtimestamp(os.path.getmtime(cache_file))
            if datetime.now() - file_mod_time < timedelta(hours=24): # 24 hours
                with open(cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error reading cache file {cache_file}: {e}")
    
    try:
        # Create a session to maintain cookies
        session = requests.Session()
        session.headers.update(HEADERS)
        
        # First visit the forum page to get necessary cookies and find threads
        print(f"Accessing forum page: {FORUM_URL}")
        response = session.get(FORUM_URL, timeout=20) # Increased timeout
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        patch_notes = []
        # Find all thread items. Structure may vary, adjust selector as needed.
        thread_elements = soup.select('div.thread-list div.thread') 

        if not thread_elements:
            print("No thread elements found with 'div.thread-list div.thread'. Trying alternative 'div.thread'.")
            thread_elements = soup.find_all('div', class_='thread') # Alternative selector

        if not thread_elements:
            print("No thread elements found. Check forum page structure and CSS selectors.")
            return None


        print(f"Found {len(thread_elements)} potential threads on the forum page.")
        
        for thread_element in thread_elements:
            try:
                title_elem = thread_element.find('a', class_='thread_title')
                if not title_elem:
                    # Try another common structure if the first fails
                    title_elem = thread_element.select_one('div.title a') # Common alternative
                    if not title_elem: # More specific to GGG forums, sometimes it's within a div.thread-title
                        title_elem = thread_element.select_one('div.thread-title a')
                        if not title_elem:
                             print("Skipping element, title element not found with known selectors.")
                             continue
                
                title = title_elem.text.strip()
                # Filter for actual patch notes
                if not any(keyword in title.lower() for keyword in ['patch', 'hotfix', 'update', 'notes']):
                    # print(f"Skipping thread (title does not match keywords): {title}")
                    continue
                
                url = title_elem['href']
                if not url.startswith('http'):
                    url = f"https://www.pathofexile.com{url}"
                
                # Extract thread_id (often the last part of the URL)
                thread_id_match = re.search(r'/thread/(\d+)', url)
                thread_id = thread_id_match.group(1) if thread_id_match else url.split('/')[-1]


                print(f"Processing matching thread: {title} ({url})")
                
                # Get the thread content
                thread_response = session.get(url, timeout=20) 
                thread_response.raise_for_status()
                thread_soup = BeautifulSoup(thread_response.text, 'html.parser')
                
                # Find the main content div (usually the first post's content)
                content_div = thread_soup.find('div', class_='content') 
                if not content_div: 
                    content_div = thread_soup.select_one('div.forum-post-content div.content') # GGG specific
                    if not content_div: 
                         content_div = thread_soup.select_one('div.post_content') # General fallback
                         if not content_div:
                            print(f"Warning: Main content div not found for thread: {title}")
                            raw_html_content = ""
                            text_content = []
                         else: # Found with post_content
                            raw_html_content = str(content_div)
                            text_content = [s.strip() for s in content_div.stripped_strings if s.strip()]
                    else: # Found with forum-post-content div.content
                        raw_html_content = str(content_div)
                        text_content = [s.strip() for s in content_div.stripped_strings if s.strip()]
                else: # Found with div.content
                    raw_html_content = str(content_div)
                    text_content = [s.strip() for s in content_div.stripped_strings if s.strip()]

                
                # Get the date
                date_elem = thread_soup.find('span', class_='post_date')
                if not date_elem: 
                    date_elem = thread_soup.select_one('div.post-time') or thread_soup.select_one('time')
                
                date_str = date_elem.text.strip() if date_elem else "Unknown Date"
                
                # Basic date parsing attempt (can be made more robust)
                parsed_date = None
                if date_elem and date_elem.has_attr('data-time'): # Example for some forums
                    try:
                        parsed_date = datetime.fromtimestamp(int(date_elem['data-time']))
                        date_str = parsed_date.strftime('%b %d, %Y, %I:%M:%S %p')
                    except ValueError: pass # Keep original string if parse fails
                elif "on " in date_str.lower(): # GGG format "on Jan 1, 2024, 1:00:00 AM"
                     try:
                        parsed_date = datetime.strptime(date_str.split("on ")[1], '%b %d, %Y, %I:%M:%S %p')
                        date_str = parsed_date.strftime('%b %d, %Y, %I:%M:%S %p') # Standardize
                     except ValueError: pass # Keep original string
                # Add more parsing rules if other formats are common

                patch_notes.append({
                    "title": title,
                    "url": url,
                    "thread_id": thread_id,
                    "date": date_str, 
                    "parsed_date_sort_key": parsed_date or datetime.min, # For reliable sorting
                    "raw_html_content": raw_html_content,
                    "text_content": text_content
                })
                
                print(f"Successfully processed: {title}")
                time.sleep(1.5) # Increased sleep time slightly
                
            except requests.exceptions.HTTPError as http_err:
                print(f"HTTP error processing thread {url}: {http_err}")
            except requests.exceptions.Timeout:
                print(f"Timeout processing thread {url}")
            except Exception as e:
                print(f"Error processing thread {url}: {e}")
                continue
        
        # Sort by parsed_date_sort_key
        patch_notes.sort(key=lambda x: x.get('parsed_date_sort_key', datetime.min), reverse=True)
        
        # Remove the temporary sort key before caching/returning
        for note in patch_notes:
            note.pop('parsed_date_sort_key', None)

        result = {
            "latest_patch": patch_notes[0] if patch_notes else None,
            "all_patches": patch_notes,
            "source_url": FORUM_URL 
        }
        
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2)
            print(f"Patch notes saved to cache: {cache_file}")
        except Exception as e:
            print(f"Error saving to cache: {e}")
        
        return result
        
    except requests.exceptions.RequestException as e:
        print(f"Error fetching main forum page {FORUM_URL}: {e}")
        return None
    except Exception as e: 
        print(f"An unexpected error occurred in get_patch_notes: {e}")
        return None

def get_latest_patch_notes():
    """Gets only the latest PoE2 patch notes."""
    all_notes = get_patch_notes()
    if all_notes and all_notes.get("latest_patch"):
        return all_notes["latest_patch"]
    return None

if __name__ == "__main__":
    import re # Added re for thread_id extraction in main test
    print("Fetching latest patch notes...")
    notes = get_patch_notes()
    if notes and notes.get("latest_patch"):
        latest = notes["latest_patch"]
        print(f"Latest Patch: {latest.get('title')}")
        print(f"Date: {latest.get('date')}")
        print(f"URL: {latest.get('url')}")
        print(f"Raw HTML content snippet: {latest.get('raw_html_content', '')[:200]}...")
        print(f"Text content snippet: {str(latest.get('text_content', []))[:200]}...")
    else:
        print("Could not fetch latest patch notes.")
