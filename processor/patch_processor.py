import re
from bs4 import BeautifulSoup
from datetime import datetime

# Define PoE-related keywords
POE_KEYWORDS = [
    "nerf", "buff", "new skill", "unique item", "gem", "passive tree", 
    "vaal", "aura", "curse", "mine", "trap", "totem", "sentinel", "sanctum", 
    "crucible", "ancestor", "affliction", "archnemesis", "kalguuran", "expedition",
    "ultimatum", "ritual", "heist", "harvest", "delirium", "metamorph", "blight",
    "legion", "synthesis", "betrayal", "delve", "incursion", "bestiary", "abyss",
    "harbinger", "breach", "essence", "prophecy", "perandus", "talisman", "rampage",
    "beyond", "ambush", "domination", "nemesis", "torment", "bloodlines", "onslaught",
    "ascendancy", "atlas", "shaper", "elder", "conqueror", "sirus", "maven", 
    "vaal skill", "support gem", "skill gem", "keystone", "cluster jewel", "flask",
    "map", "boss", "monster", "crafting", "vendor recipe", "divination card",
    "ruthless", "ssf", "hardcore", "standard", "league", "event", "patch", "hotfix",
    "update", "balance", "change", "fix", "improvement", "PvP", "PvE", "trade",
    "Zana", "Kirac", "Einhar", "Alva", "Niko", "Jun", "Cassia", "Tane", "Sister Divinia",
    "Path of Exile", "Wraeclast", "Oriath"
]

def clean_html_content(raw_html_content):
    """Cleans HTML content and extracts text."""
    if not raw_html_content:
        return ""
    soup = BeautifulSoup(raw_html_content, 'html.parser')
    # Assuming raw_html_content is the main content div's HTML
    return soup.get_text(separator='\n', strip=True)

def structure_sections_placeholder(soup_content):
    """Placeholder for section structuring.
    For now, it extracts H1, H2, H3 titles and immediate sibling content.
    """
    sections = []
    if not soup_content:
        return sections

    for header in soup_content.find_all(['h1', 'h2', 'h3', 'h4']): # Added h4
        title = header.get_text(strip=True)
        content_elements = []
        current_element = header.next_sibling
        while current_element and current_element.name not in ['h1', 'h2', 'h3', 'h4']:
            if hasattr(current_element, 'get_text'):
                text = current_element.get_text(separator='\n', strip=True)
                if text:
                    content_elements.append(text)
            current_element = current_element.next_sibling
        
        section_content = "\n".join(content_elements).strip()
        if title and section_content: # Only add if both title and content exist
             sections.append({"title": title, "content": section_content})

    # If no headers were found, but there's content, treat all as one section
    if not sections and soup_content.get_text(strip=True):
        sections.append({
            "title": "General Changes", 
            "content": soup_content.get_text(separator='\n', strip=True)
        })
    return sections

def extractive_summarization(cleaned_text, num_sentences=5): # Changed to 5 as per example
    """Performs simple extractive summarization."""
    if not cleaned_text:
        return ""
    # Basic sentence splitting, can be improved
    sentences = re.split(r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?|\!)\s', cleaned_text)
    # Filter out very short "sentences" that might just be list items or headers
    meaningful_sentences = [s for s in sentences if len(s.split()) > 5] # Min 5 words
    summary = ' '.join(meaningful_sentences[:num_sentences])
    return summary

def extract_keywords(cleaned_text):
    """Extracts predefined keywords from text."""
    if not cleaned_text:
        return []
    
    found_keywords = set()
    text_lower = cleaned_text.lower() # Pre-lower the text for efficiency
    for keyword in POE_KEYWORDS:
        escaped_keyword = r'\b' + re.escape(keyword.lower()) + r'\b' # Ensure keyword is lower for matching
        if re.search(escaped_keyword, text_lower):
            found_keywords.add(keyword.lower()) # Store in lowercase
    return sorted(list(found_keywords))

def process_patch_note(raw_patch_data):
    """Processes a single raw patch note dictionary."""
    raw_html = raw_patch_data.get("raw_html_content", "")
    
    soup = BeautifulSoup(raw_html, 'html.parser')
    # It's assumed raw_html_content IS the main content, so pass soup directly
    # If raw_html_content was the *full* page, one would first find the main content div
    # e.g., main_content_div = soup.find('div', class_='content') or similar
    # For now, the scraper is designed to provide the relevant content div's HTML directly.
    
    cleaned_text = clean_html_content(raw_html) # Uses the raw_html directly as per current design
    
    # Use the soup object for section structuring
    sections = structure_sections_placeholder(soup) # Pass the parsed soup of raw_html

    summary = extractive_summarization(cleaned_text, num_sentences=5)
    keywords = extract_keywords(cleaned_text)
    
    date_str = raw_patch_data.get("date", "")
    standardized_date = date_str 
    if date_str:
        try:
            # Handle "on Mon DD, YYYY, HH:MM:SS AM/PM" format
            if "on " in date_str.lower(): 
                actual_date_str = date_str.split("on ", 1)[1]
                # Python's %a for day name might be locale-dependent, so try to remove it if present
                actual_date_str = re.sub(r'^[A-Za-z]{3,},\s+', '', actual_date_str)
            else:
                actual_date_str = date_str

            # Common format: "Dec 05, 2023, 10:00:00 AM" or "Jan 1, 2024, 12:00:00 PM"
            dt_object = datetime.strptime(actual_date_str, '%b %d, %Y, %I:%M:%S %p')
            standardized_date = dt_object.isoformat()
        except ValueError as e:
            print(f"Warning: Could not parse date '{date_str}' with primary format: {e}. Trying alternatives.")
            # Attempt to parse YYYY-MM-DD from a string if it exists
            match_iso = re.search(r"(\d{4}-\d{2}-\d{2})", date_str)
            if match_iso:
                try:
                    dt_object = datetime.fromisoformat(match_iso.group(1))
                    standardized_date = dt_object.isoformat() # Keep as full ISO if only date is found
                except ValueError:
                     standardized_date = match_iso.group(1) # Store as YYYY-MM-DD if it's just a date
            else: # Fallback if no known format matches
                standardized_date = date_str # Keep original if all parsing fails
                print(f"Kept original date string: {date_str}")


    processed_data = {
        "url": raw_patch_data.get("url"),
        "title": raw_patch_data.get("title"),
        "date": standardized_date,
        "thread_id": raw_patch_data.get("thread_id"),
        "cleaned_text": cleaned_text,
        "summary": summary,
        "keywords": keywords,
        "sections": sections,
        "raw_html_preserved": raw_html # Store the HTML used for processing
    }
    return processed_data

if __name__ == "__main__":
    sample_raw_data = {
        "title": "Path of Exile: Affliction Patch Notes - Update 3.23.0",
        "url": "https://www.pathofexile.com/forum/view-thread/3456789",
        "date": "on Dec 05, 2023, 10:00:00 AM",
        "thread_id": "3456789",
        "raw_html_content": """
        <div>
            <h1>Patch Notes - 3.23.0 - Path of Exile: Affliction</h1>
            <p>Welcome to Path of Exile: Affliction! This patch introduces the new Affliction challenge league, several new skill gems and unique items, and many balance changes. We've also included some much-anticipated quality of life improvements.</p>
            <h2>Key Changes</h2>
            <ul>
                <li>The Affliction League: Venture into the Viridian Wildwood.</li>
                <li>New Skills: Tornado Shot, Ice Shot, and Artillery Ballista have been reworked. Added new skill gem: Fire Blast.</li>
                <li>Balance: Significant changes to monster life and damage. Many unique items have been rebalanced. Some say it's a nerf to player power.</li>
            </ul>
            <h3>Specifics</h3>
            <p>The passive tree has seen minor adjustments. Several Vaal skill gems are now stronger.</p>
            <p>This is the end of the notes. We hope you enjoy the Affliction league! Another sentence for summarization. And one more for good measure. Perhaps a fourth one too. And a fifth one to ensure we hit the N sentences for summary.</p>
        </div>
        """,
        "text_content": "Welcome to Path of Exile: Affliction! ... (snipped for brevity)"
    }
    
    print("--- Processing Sample Patch Note ---")
    processed_note = process_patch_note(sample_raw_data)
    
    print("\n--- Processed Data ---")
    for key, value in processed_note.items():
        if key in ["cleaned_text", "raw_html_preserved"]:
            print(f"{key.replace('_', ' ').title()}: {str(value)[:250]}...")
        elif key == "sections":
            print(f"{key.replace('_', ' ').title()}:")
            if value:
                for i, section in enumerate(value):
                    print(f"  Section {i+1}:")
                    print(f"    Title: {section['title']}")
                    print(f"    Content: {section['content'][:150]}...")
            else:
                print("  No sections extracted.")
        else:
            print(f"{key.replace('_', ' ').title()}: {value}")

    print("\n--- Testing with minimal data (for robustness) ---")
    minimal_data = {
        "title": "Hotfix 1.0.1a",
        "url": "url_minimal_hotfix",
        "date": "Jan 1st, 2024", # Non-standard date
        "thread_id": "12345",
        "raw_html_content": "<h4>Small Hotfix</h4><p>Fixed a bug with Fireball. Player power is slightly buffed.</p><p>Another small change.</p>",
    }
    processed_minimal = process_patch_note(minimal_data)
    print(f"Title: {processed_minimal['title']}")
    print(f"Date (Processed): {processed_minimal['date']}") # Check how non-standard date was handled
    print(f"Summary: {processed_minimal['summary']}")
    print(f"Keywords: {processed_minimal['keywords']}")
    print("Sections:")
    if processed_minimal['sections']:
        for i, section in enumerate(processed_minimal['sections']):
            print(f"  Section {i+1}: Title: {section['title']}, Content: {section['content'][:100]}...")
    else:
        print("  No sections extracted.")
    
    print("\n--- Testing with no clear headers ---")
    no_header_data = {
        "title": "Minor Update",
        "url": "url_no_header",
        "date": "2024-02-15", # ISO date only
        "thread_id": "67890",
        "raw_html_content": "<div><p>Just a paragraph of text. No explicit headers. This is a general update about something important, like a gem rebalance. Maybe a nerf to a popular skill.</p></div>",
    }
    processed_no_header = process_patch_note(no_header_data)
    print(f"Title: {processed_no_header['title']}")
    print(f"Date (Processed): {processed_no_header['date']}")
    print(f"Summary: {processed_no_header['summary']}")
    print(f"Keywords: {processed_no_header['keywords']}")
    print("Sections:")
    if processed_no_header['sections']:
        for i, section in enumerate(processed_no_header['sections']):
            print(f"  Section {i+1}: Title: {section['title']}, Content: {section['content'][:100]}...")
    else:
        print("  No sections extracted.")
