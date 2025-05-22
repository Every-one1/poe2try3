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
CACHE_EXPIRY_HOURS = 24

if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)

def _log_message(message, progress_callback=None):
    if progress_callback:
        progress_callback(message)
    else:
        print(message)

def parse_html_table_to_text(table_soup):
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


def get_scraped_data(url, item_name_or_skill_name, progress_callback=None):
    """Gets scraped data for a skill or item, with caching."""
    sanitized_name = "".join(c if c.isalnum() else "_" for c in item_name_or_skill_name)
    cache_file = os.path.join(CACHE_DIR, f"{sanitized_name}.json")
    
    if os.path.exists(cache_file):
        try:
            file_mod_time = datetime.fromtimestamp(os.path.getmtime(cache_file))
            if datetime.now() - file_mod_time < timedelta(hours=CACHE_EXPIRY_HOURS):
                with open(cache_file, 'r', encoding='utf-8') as f:
                    _log_message(f"Cache hit for {item_name_or_skill_name}", progress_callback)
                    return json.load(f)
        except Exception as e:
            _log_message(f"Error reading cache file {cache_file}: {e}", progress_callback)

    _log_message(f"Cache miss or expired for {item_name_or_skill_name}. Scraping {url}...", progress_callback)

    # The original _scrape_page_logic was renamed to _scrape_page_logic_from_content
    # and now get_scraped_data handles the requests.get part.
    
    # Try standard URL first
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        if response.status_code == 200:
            # Pass item_name_or_skill_name to _scrape_page_logic_from_content
            data = _scrape_page_logic_from_content(response.content, item_name_or_skill_name, url, progress_callback)
            if data and data.get("name", "N/A") != "N/A":
                _save_to_cache(cache_file, data, progress_callback)
                return data
    except requests.exceptions.RequestException as e:
        _log_message(f"Error fetching standard URL {url}: {e}", progress_callback)

    # For unique items, try alternative URL formats if the initial attempt failed
    # This check needs to be more robust, e.g., by checking if "item" or "unique" is in the name or URL.
    # For simplicity, we'll assume if the first try fails and 'item' or 'unique' is in the name, try alts.
    is_likely_item = "item" in item_name_or_skill_name.lower() or "unique" in item_name_or_skill_name.lower() or \
                     "item" in url.lower() or "unique" in url.lower()

    if is_likely_item:
        _log_message(f"Standard URL failed for likely item '{item_name_or_skill_name}'. Trying alternatives...", progress_callback)
        alternative_urls = [
            url.replace("_", "-"),
            url.replace("_", ""),
            url + "-unique",
        ]
        # Ensure the original URL isn't re-added if it matches an alt
        alternative_urls = [alt for alt in alternative_urls if alt != url]


        for alt_url in alternative_urls:
            _log_message(f"Trying alternative URL: {alt_url}", progress_callback)
            try:
                response = requests.get(alt_url, headers=HEADERS, timeout=15)
                if response.status_code == 200:
                    data = _scrape_page_logic_from_content(response.content, item_name_or_skill_name, alt_url, progress_callback)
                    if data and data.get("name", "N/A") != "N/A":
                        _log_message(f"Success with alternative URL: {alt_url}", progress_callback)
                        _save_to_cache(cache_file, data, progress_callback)
                        return data
            except requests.exceptions.RequestException as e:
                _log_message(f"Error with alternative URL {alt_url}: {e}", progress_callback)
                continue
        _log_message(f"All alternative URLs failed for item: {item_name_or_skill_name}", progress_callback)
    
    _log_message(f"Could not find valid data for: {item_name_or_skill_name} from {url} (and alternatives if tried).", progress_callback)
    return None


def _save_to_cache(cache_file, data, progress_callback=None):
    try:
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        _log_message(f"Saved to cache: {cache_file}", progress_callback)
    except Exception as e:
        _log_message(f"Error writing to cache file {cache_file}: {e}", progress_callback)

def _scrape_page_logic_from_content(html_content, name_for_logging, source_url_for_data, progress_callback=None):
    """Internal logic to scrape a skill or item page from its HTML content."""
    soup = BeautifulSoup(html_content, 'html.parser')
    data = {
        "name": "N/A", "primary_tag": "N/A", "secondary_tags": [], "stats_properties": [],
        "requirements": "N/A", "description": "N/A",
        "spear_effects": [], "quality_effects_heading": "N/A", "quality_mods": [], 
        "lightning_bolts_stats": [], 
        "item_implicits": [], "item_explicits": [],
        "level_scaling_table_text": "N/A", "attribute_table_text": "N/A",
        "source_url": source_url_for_data 
    }

    main_card = soup.find('div', class_='newItemPopup gemPopup item-popup--poe2') # Gem specific
    if not main_card:
        # Try a more generic item popup structure if gem one fails
        main_card = soup.find('div', class_='newItemPopup itemPopup item-popup--poe2') # Item specific
    
    if not main_card:
        # Fallback: Try to find any element that looks like a main content block.
        # This is highly heuristic.
        main_card = soup.find('div', id='itemPopup') # Common ID from some web frameworks
        if not main_card:
            main_card = soup.find('div', class_='item-details') # Another common class
    
    if not main_card: # If still no main_card, try to get name from meta and log warning
        meta_title = soup.find('meta', property='og:title')
        if meta_title and meta_title.get('content'):
            data["name"] = meta_title.get('content').replace(" - PoE2DB", "").strip()
        _log_message(f"Warning: Could not find standard main card for {name_for_logging} at {source_url_for_data}. Data extraction might be limited. Found name: {data['name']}", progress_callback)
        # Attempt to parse tables even if main card is not found
    else: # Main card found, proceed with detailed parsing
        name_div = main_card.find('div', class_='itemName')
        if name_div and name_div.find('span', class_='lc'):
            data["name"] = name_div.find('span', class_='lc').get_text(strip=True)
        elif not data["name"] or data["name"] == "N/A": # If name still not set
             meta_title = soup.find('meta', property='og:title')
             if meta_title and meta_title.get('content'):
                data["name"] = meta_title.get('content').replace(" - PoE2DB", "").strip()
        
        type_line_div = main_card.find('div', class_='typeLine')
        if type_line_div:
            type_span = type_line_div.find('span', class_='lc')
            if type_span:
                primary_tag_anchor = type_span.find('a')
                data["primary_tag"] = primary_tag_anchor.get_text(strip=True) if primary_tag_anchor else type_span.get_text(strip=True)

        # Consolidate finding all 'Stats' blocks, whether it's the first or subsequent ones.
        all_stats_blocks = main_card.find_all('div', class_='Stats')
        
        is_first_stats_block = True
        for stats_block in all_stats_blocks:
            if is_first_stats_block:
                property_divs = stats_block.find_all('div', class_='property', recursive=False)
                if property_divs:
                    prop_iter = iter(property_divs)
                    first_prop_div = next(prop_iter, None)
                    if first_prop_div and first_prop_div.find_all('a', class_='GemTags'):
                        data["secondary_tags"] = [a.get_text(strip=True) for a in first_prop_div.find_all('a', class_='GemTags')]
                        for prop_div in prop_iter: data["stats_properties"].append(prop_div.get_text(strip=True))
                    elif first_prop_div:
                        data["stats_properties"].append(first_prop_div.get_text(strip=True))
                        for prop_div in prop_iter: data["stats_properties"].append(prop_div.get_text(strip=True))

                requirements_divs = stats_block.find_all('div', class_='requirements')
                if requirements_divs:
                    data["requirements"] = " | ".join([req.get_text(strip=True) for req in requirements_divs])

                desc_div = stats_block.find('div', class_='secDescrText')
                if desc_div: data["description"] = desc_div.get_text(separator="\n", strip=True)
                
                data["item_implicits"].extend([mod.get_text(separator=" ", strip=True) for mod in stats_block.find_all('div', class_='implicitMod')])
                is_first_stats_block = False

            # Item Explicits (can be in any stats block)
            data["item_explicits"].extend([mod.get_text(separator=" ", strip=True) for mod in stats_block.find_all('div', class_='explicitMod') 
                                            if mod.get_text(strip=True) not in data["spear_effects"] and \
                                               mod.get_text(strip=True) not in data["lightning_bolts_stats"]])


            # Skill-specific sections (Spear)
            spear_header = stats_block.find_previous_sibling(lambda tag: tag.name == 'div' and tag.has_attr('class') and \
                                       'hybridHeader' in tag.get('class') and tag.find('span', class_='ItemType', string='Spear'))
            if spear_header: # Check if current stats_block is directly after spear_header
                 # This condition might be too strict if there are other elements in between
                if spear_header.find_next_sibling('div', class_='Stats') == stats_block:
                    data["spear_effects"].extend([mod.get_text(separator=" ", strip=True) for mod in stats_block.find_all('div', class_='explicitMod')])
                    quality_heading_div = stats_block.find('div', class_='text-type0', string=lambda t: t and "Additional Effects From Quality" in t)
                    if quality_heading_div:
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
            
            bolts_header = stats_block.find_previous_sibling(lambda tag: tag.name == 'div' and tag.has_attr('class') and \
                                       'hybridHeader' in tag.get('class') and tag.find('span', class_='ItemType', string='Lightning Bolts'))
            if bolts_header:
                if bolts_header.find_next_sibling('div', class_='Stats') == stats_block:
                    data["lightning_bolts_stats"].extend([prop_bolt.get_text(separator=" ", strip=True) for prop_bolt in stats_block.find_all(['div'], class_=['hybridProperty', 'explicitMod'])])

    # Tables parsing (remains outside main_card assumption)
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
    
    # Fallback name if still N/A
    if data.get("name", "N/A") == "N/A":
        data["name"] = name_for_logging # Use the name passed to the function as a last resort
        _log_message(f"Used passed name '{name_for_logging}' as fallback for {source_url_for_data}", progress_callback)

    return data


if __name__ == "__main__":
    def _test_logger(message):
        print(f"[TestLogger] {message}")

    skill_name_for_url = "Lightning_Spear" 
    test_skill_url = f"https://poe2db.tw/us/{skill_name_for_url}"
    print(f"--- Testing Scraper with Skill: {skill_name_for_url} ---")
    scraped_skill_info = get_scraped_data(test_skill_url, skill_name_for_url, progress_callback=_test_logger)
    if scraped_skill_info:
        for key, value in scraped_skill_info.items():
            if isinstance(value, list) and value: print(f"\n{key.replace('_', ' ').title()}:\n  " + "\n  ".join(f"- {item}" for item in value))
            elif isinstance(value, str) and value != "N/A" and value.strip(): print(f"\n{key.replace('_', ' ').title()}:\n{value if 'table' in key else f'  {value}'}")
    else:
        print(f"Failed to scrape skill: {skill_name_for_url}")
    
    print("-" * 30)
    
    # Test with a unique item. Example: "Bones_of_Ullr" (Unique Boots)
    # URL: https://poe2db.tw/us/Bones_of_Ullr
    item_name_for_url = "Bones_of_Ullr" 
    test_item_url = f"https://poe2db.tw/us/{item_name_for_url}"
    print(f"\n\n--- Testing Scraper with Item: {item_name_for_url} ---")
    scraped_item_info = get_scraped_data(test_item_url, item_name_for_url, progress_callback=_test_logger)
    if scraped_item_info:
        for key, value in scraped_item_info.items():
            if isinstance(value, list) and value: print(f"\n{key.replace('_', ' ').title()}:\n  " + "\n  ".join(f"- {item}" for item in value))
            elif isinstance(value, str) and value != "N/A" and value.strip(): print(f"\n{key.replace('_', ' ').title()}:\n{value if 'table' in key else f'  {value}'}")
    else:
        print(f"Failed to scrape item: {item_name_for_url}")

    # Test with a non-existent item to check fallback and logging
    # item_name_for_url = "Non_Existent_Item_XYZ" 
    # test_item_url = f"https://poe2db.tw/us/{item_name_for_url}"
    # print(f"\n\n--- Testing Scraper with Non-Existent Item: {item_name_for_url} ---")
    # scraped_item_info = get_scraped_data(test_item_url, item_name_for_url, progress_callback=_test_logger)
    # if scraped_item_info:
    #      print("Scraped non-existent item info (should ideally be minimal or None):")
    #      print(json.dumps(scraped_item_info, indent=2))
    # else:
    #     print(f"Correctly failed to scrape non-existent item: {item_name_for_url}")