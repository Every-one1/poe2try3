# poe2db_scraper.py
import requests
from bs4 import BeautifulSoup
import time
import json
import os
from datetime import datetime, timedelta

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}
CACHE_DIR = "scraper_cache"
CACHE_EXPIRY_HOURS = 24 # How long to keep cache entries (in hours)

if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)

def parse_html_table_to_text(table_soup):
    # ... (function remains the same as previous version) ...
    if not table_soup:
        return "Table not found"
    text_output = []
    thead = table_soup.find('thead')
    header_source = thead if thead else table_soup 
    headers = [th.get_text(separator=" ", strip=True) for th in header_source.find_all('th', recursive=False if thead else True)]
    if headers:
        text_output.append(" | ".join(headers))
        separator_line = " | ".join(["-" * len(h) for h in headers])
        text_output.append(separator_line)
    table_body = table_soup.find('tbody')
    rows_to_parse = table_body.find_all('tr') if table_body else table_soup.find_all('tr')
    start_index = 0
    if not table_body and headers and rows_to_parse:
        first_row_cols_text = [td.get_text(separator=" ", strip=True) for td in rows_to_parse[0].find_all(['td', 'th'])]
        if " | ".join(first_row_cols_text) == " | ".join(headers):
           start_index = 1
    for row in rows_to_parse[start_index:]:
        cols = [td.get_text(separator=" ", strip=True) for td in row.find_all(['td', 'th'])]
        if any(c.strip() for c in cols): 
            text_output.append(" | ".join(cols))
    return "\n".join(text_output)


def get_scraped_data(url, name):
    """Gets scraped data for a skill or item, with caching."""
    sanitized_name = "".join(c if c.isalnum() else "_" for c in name)
    cache_file = os.path.join(CACHE_DIR, f"{sanitized_name}.json")
    
    # Check cache
    if os.path.exists(cache_file):
        try:
            file_mod_time = datetime.fromtimestamp(os.path.getmtime(cache_file))
            if datetime.now() - file_mod_time < timedelta(hours=CACHE_EXPIRY_HOURS):
                with open(cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error reading cache file {cache_file}: {e}")

    # For unique items, try different URL formats
    if "unique" in url.lower() or "item" in url.lower():
        # Try the standard format first
        try:
            response = requests.get(url, headers=HEADERS, timeout=15)
            if response.status_code == 200:
                data = _scrape_page_logic(response.content, name)
                if data and data.get("name", "N/A") != "N/A":
                    _save_to_cache(cache_file, data)
                    return data
        except Exception as e:
            print(f"Error with standard URL format: {e}")

        # Try alternative URL formats for unique items
        alternative_urls = [
            url.replace("_", "-"),  # Replace underscores with hyphens
            url.replace("_", ""),   # Remove underscores
            url + "-unique",        # Add -unique suffix
            url.replace("item", "unique-item")  # Replace item with unique-item
        ]

        for alt_url in alternative_urls:
            try:
                response = requests.get(alt_url, headers=HEADERS, timeout=15)
                if response.status_code == 200:
                    data = _scrape_page_logic(response.content, name)
                    if data and data.get("name", "N/A") != "N/A":
                        _save_to_cache(cache_file, data)
                        return data
            except Exception as e:
                print(f"Error with alternative URL {alt_url}: {e}")
                continue

        print(f"Could not find valid data for unique item: {name}")
        return None

    # For skills, use the original logic
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching {url}: {e}")
        return None

    data = _scrape_page_logic(response.content, name)
    if data:
        _save_to_cache(cache_file, data)
    return data

def _save_to_cache(cache_file, data):
    """Helper function to save data to cache."""
    try:
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Error writing to cache file {cache_file}: {e}")

def _scrape_page_logic(url): # Renamed from scrape_skill_page to be more generic
    """Internal logic to scrape a skill or item page from poe2db.tw."""
    # This function contains the BeautifulSoup parsing logic from the previous scrape_skill_page
    # It should return a dictionary of the scraped data or None if the request fails.
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching page {url}: {e}")
        return None # Indicate failure

    soup = BeautifulSoup(response.content, 'html.parser')
    
    data = { # Generic name
        "name": "N/A", "primary_tag": "N/A", "secondary_tags": [], "stats_properties": [],
        "requirements": "N/A", "description": "N/A", 
        # Skill-specific (might be empty for items)
        "spear_effects": [], "quality_effects_heading": "N/A", "quality_mods": [], 
        "lightning_bolts_stats": [], 
        # Item-specific (might be empty for skills)
        "item_implicits": [], "item_explicits": [],
        # Common potentially
        "level_scaling_table_text": "N/A", "attribute_table_text": "N/A",
        "source_url": url # Good to keep track of where data came from
    }

    # Try to find the main "card" element for the skill or item
    # This might need to be adjusted if item pages have a different main container class
    main_card = soup.find('div', class_='newItemPopup gemPopup item-popup--poe2') # For gems
    if not main_card:
        # A more generic selector for item cards IF DIFFERENT.
        # For now, let's assume item pages might use a similar top-level popup structure
        # or we'll need a different function/logic path for items.
        # Let's try to get name from meta as a fallback if no main card identified for now
        meta_title = soup.find('meta', property='og:title')
        if meta_title and meta_title.get('content'):
            data["name"] = meta_title.get('content').replace(" - PoE2DB", "").strip()
        # print(f"Warning: Could not find standard main card for {url}. Data extraction might be limited.")
        # We could try to find other sections even without a main card, e.g., tables.
    
    if main_card: # Proceed with detailed parsing if main_card is found
        name_div = main_card.find('div', class_='itemName')
        if name_div and name_div.find('span', class_='lc'):
            data["name"] = name_div.find('span', class_='lc').get_text(strip=True)
        
        type_line_div = main_card.find('div', class_='typeLine') # Often contains "Attack", "Spell" or item type
        if type_line_div and type_line_div.find('span', class_='lc'):
            primary_tag_anchor = type_line_div.find('span', class_='lc').find('a')
            data["primary_tag"] = primary_tag_anchor.get_text(strip=True) if primary_tag_anchor else type_line_div.find('span', class_='lc').get_text(strip=True)

        first_stats_block = main_card.find('div', class_='Stats') # First block of stats/properties
        if first_stats_block:
            property_divs = first_stats_block.find_all('div', class_='property', recursive=False)
            if property_divs:
                prop_iter = iter(property_divs)
                first_prop_div = next(prop_iter, None)
                if first_prop_div and first_prop_div.find_all('a', class_='GemTags'): # Check if first property is tags
                    data["secondary_tags"] = [a.get_text(strip=True) for a in first_prop_div.find_all('a', class_='GemTags')]
                    for prop_div in prop_iter: # Continue with the rest
                        data["stats_properties"].append(prop_div.get_text(strip=True))
                elif first_prop_div: # If first was not tags, process it as a normal property
                    data["stats_properties"].append(first_prop_div.get_text(strip=True))
                    for prop_div in prop_iter: # And the rest
                        data["stats_properties"].append(prop_div.get_text(strip=True))

            requirements_divs = first_stats_block.find_all('div', class_='requirements')
            if requirements_divs:
                data["requirements"] = " | ".join([req.get_text(strip=True) for req in requirements_divs])

            desc_div = first_stats_block.find('div', class_='secDescrText')
            if desc_div: data["description"] = desc_div.get_text(separator="\n", strip=True)
            
            # Item implicits (often appear before explicits)
            # The class might be "implicitMod" or similar - needs inspection for item pages
            data["item_implicits"] = [mod.get_text(separator=" ", strip=True) for mod in first_stats_block.find_all('div', class_='implicitMod')]


        # This part is skill-specific, look for "Spear" and "Lightning Bolts" sections
        # For items, these won't be found, which is fine.
        # Need to find ALL "Stats" blocks within the main_card for items too.
        all_stats_blocks_in_card = main_card.find_all('div', class_='Stats')

        for stats_block in all_stats_blocks_in_card:
            # Try to get explicit mods if it's an item. This selector needs verification for items.
            for mod_div in stats_block.find_all('div', class_='explicitMod'):
                if mod_div not in data.get("spear_effects", []) and \
                   mod_div not in data.get("lightning_bolts_stats", []): # Avoid duplication if already parsed
                    data["item_explicits"].append(mod_div.get_text(separator=" ", strip=True))

            # Skill-specific sections (Spear)
            spear_header = main_card.find(lambda tag: tag.name == 'div' and tag.has_attr('class') and \
                                       'hybridHeader' in tag.get('class') and tag.find('span', class_='ItemType', string='Spear'))
            if spear_header and spear_header.find_next_sibling('div', class_='Stats') == stats_block:
                data["spear_effects"] = [mod.get_text(separator=" ", strip=True) for mod in stats_block.find_all('div', class_='explicitMod')]
                quality_heading_div = stats_block.find('div', class_='text-type0')
                if quality_heading_div and "Additional Effects From Quality" in quality_heading_div.get_text():
                    data["quality_effects_heading"] = quality_heading_div.get_text(strip=True).replace("<br>", "").strip()
                    current_el = quality_heading_div
                    while True:
                        current_el = current_el.find_next_sibling()
                        if not current_el : break 
                        if current_el.name == 'div' and current_el.has_attr('class') and 'qualityMod' in current_el.get('class'):
                            data["quality_mods"].append(current_el.get_text(separator=" ", strip=True))
                        elif current_el.name == 'div' and current_el.has_attr('class') and \
                             ('hybridHeader' in current_el.get('class') or \
                              'separator' in current_el.get('class') or \
                              'text-type0' in current_el.get('class')):
                            break
            
            # Skill-specific sections (Lightning Bolts)
            bolts_header = main_card.find(lambda tag: tag.name == 'div' and tag.has_attr('class') and \
                                       'hybridHeader' in tag.get('class') and tag.find('span', class_='ItemType', string='Lightning Bolts'))
            if bolts_header and bolts_header.find_next_sibling('div', class_='Stats') == stats_block:
                for prop_bolt in stats_block.find_all(['div'], class_=['hybridProperty', 'explicitMod']):
                    data["lightning_bolts_stats"].append(prop_bolt.get_text(separator=" ", strip=True))

    # Tables are usually outside the main_card for skills
    level_effect_header = soup.find('h5', class_='card-header', string=lambda t: t and "Level Effect" in t)
    if level_effect_header:
        level_card_div = level_effect_header.find_parent('div', class_=lambda c: c and 'card' in c.split())
        if level_card_div:
            level_table_soup = level_card_div.find('table')
            if level_table_soup: data["level_scaling_table_text"] = parse_html_table_to_text(level_table_soup)

    attribute_header = soup.find('h5', class_='card-header', string=lambda t: t and "Attribute" in t)
    if attribute_header:
        attribute_card_div = attribute_header.find_parent('div', class_=lambda c: c and 'card' in c.split())
        if attribute_card_div:
            attribute_table_soup = attribute_card_div.find('table')
            if attribute_table_soup: data["attribute_table_text"] = parse_html_table_to_text(attribute_table_soup)
    
    return data


if __name__ == "__main__":
    # Test with a skill
    skill_name_for_url = "Lightning_Spear" 
    test_skill_url = f"https://poe2db.tw/us/{skill_name_for_url}"
    print(f"--- Testing Scraper with Skill: {skill_name_for_url} ---")
    scraped_skill_info = get_scraped_data(test_skill_url, skill_name_for_url) # Use caching wrapper
    if scraped_skill_info:
        for key, value in scraped_skill_info.items():
            if isinstance(value, list) and value: print(f"\n{key.replace('_', ' ').title()}:\n  " + "\n  ".join(f"- {item}" for item in value))
            elif isinstance(value, str) and value != "N/A" and value.strip(): print(f"\n{key.replace('_', ' ').title()}:\n{value if 'table' in key else f'  {value}'}")

    # Test with a unique item (you'll need to find a unique item name and its slug for poe2db.tw)
    # Example (placeholder - find a real unique item URL from poe2db.tw):
    # item_name_for_url = "Sacred_Flame" # Assuming this is the slug for "Sacred Flame" unique sceptre
    # test_item_url = f"https://poe2db.tw/us/{item_name_for_url}" 
    # print(f"\n\n--- Testing Scraper with Item: {item_name_for_url} ---")
    # scraped_item_info = get_scraped_data(test_item_url, item_name_for_url)
    # if scraped_item_info:
    #     for key, value in scraped_item_info.items():
    #         if isinstance(value, list) and value: print(f"\n{key.replace('_', ' ').title()}:\n  " + "\n  ".join(f"- {item}" for item in value))
    #         elif isinstance(value, str) and value != "N/A" and value.strip(): print(f"\n{key.replace('_', ' ').title()}:\n{value if 'table' in key else f'  {value}'}")