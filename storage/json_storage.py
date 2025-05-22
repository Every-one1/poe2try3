import json
import os
import re
from datetime import datetime

DATA_DIR = "data/patch_notes/"

if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

def slugify(text):
    """Converts text to a slug for filenames."""
    if not text: # Handle cases where text might be None or empty
        return ""
    text = str(text).lower() # Ensure text is string
    text = re.sub(r'\s+', '-', text)  # Replace spaces with hyphens
    text = re.sub(r'[^\w\-]', '', text)  # Remove non-alphanumeric characters (except hyphens)
    text = re.sub(r'-+', '-', text)  # Replace multiple hyphens with single hyphen
    text = text.strip('-') # Remove leading/trailing hyphens
    return text

def save_processed_patch_note(processed_data, progress_callback=None):
    """
    Saves processed patch note data to a JSON file.
    Optionally uses a progress_callback for logging instead of print.
    """
    
    def _log(message):
        if progress_callback:
            progress_callback(message)
        else:
            print(message) # Fallback to print if no callback

    if not processed_data or not processed_data.get("title") or not processed_data.get("date"):
        _log("Error: Processed data is missing title or date for filename generation.")
        return None # Indicates an issue before even trying to save (e.g. bad data)

    date_str = processed_data["date"]
    date_prefix = ""

    # Try to extract YYYY-MM-DD from various potential date string formats
    if isinstance(date_str, str):
        if 'T' in date_str: # Handles ISO format like "2023-12-05T10:00:00"
            date_prefix = date_str.split('T')[0]
        else:
            # Attempt to parse common date formats
            possible_formats = ['%Y-%m-%d', '%b %d, %Y', '%B %d, %Y', '%d/%m/%Y', '%m/%d/%Y']
            parsed_successfully = False
            for fmt in possible_formats:
                try:
                    dt_obj = datetime.strptime(date_str, fmt)
                    date_prefix = dt_obj.strftime('%Y-%m-%d')
                    parsed_successfully = True
                    break
                except ValueError:
                    continue
            
            if not parsed_successfully:
                # Fallback to regex if direct parsing fails
                match = re.match(r"(\d{4}-\d{2}-\d{2})", date_str)
                if match:
                    date_prefix = match.group(1)
                else:
                    _log(f"Warning: Could not determine YYYY-MM-DD from date '{date_str}'. Using slugified original.")
                    date_prefix = slugify(date_str) if date_str else "unknown-date"
    else: 
        _log(f"Warning: Date field is not a string ('{date_str}'). Using 'unknown-date'.")
        date_prefix = "unknown-date"

    title_slug = slugify(processed_data["title"])
    if not title_slug: 
        title_slug = "untitled-patch" # Default if title becomes empty
        
    filename = f"{date_prefix}_{title_slug}.json"
    filepath = os.path.join(DATA_DIR, filename)

    # Delta Detection
    if os.path.exists(filepath):
        _log(f"Patch note '{filename}' already exists. Skipping save.")
        return None # None indicates already exists, not an error in saving itself
    
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(processed_data, f, indent=4)
        _log(f"Saved new patch note: {filename}")
        return filepath 
    except IOError as e:
        _log(f"Error saving patch note to {filepath}: {e}")
        return False # False indicates a save failure

def load_latest_patch_note(progress_callback=None):
    """
    Loads the most recent patch note from DATA_DIR.
    Optionally uses a progress_callback for logging.
    """
    def _log(message):
        if progress_callback:
            progress_callback(message)
        else:
            print(message)

    try:
        files = [f for f in os.listdir(DATA_DIR) if f.endswith('.json') and re.match(r"\d{4}-\d{2}-\d{2}_", f)]
        if not files:
            _log("No patch notes found in the data directory.")
            return None
        
        files.sort(reverse=True)
        latest_filename = files[0]
        
        _log(f"Identified latest patch note file: {latest_filename}")
        return load_patch_note_by_filename(latest_filename, progress_callback=progress_callback)
    except Exception as e:
        _log(f"Error scanning for latest patch note: {e}")
        return None

def load_patch_note_by_filename(filename, progress_callback=None):
    """
    Loads a specific patch note JSON file from DATA_DIR.
    Optionally uses a progress_callback for logging.
    """
    def _log(message):
        if progress_callback:
            progress_callback(message)
        else:
            print(message)

    if not filename.endswith(".json"):
        filename += ".json"

    filepath = os.path.join(DATA_DIR, filename)
    if not os.path.exists(filepath):
        _log(f"Error: File '{filename}' not found in {DATA_DIR}.")
        return None
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        _log(f"Successfully loaded patch note: {filename}")
        return data
    except json.JSONDecodeError as e:
        _log(f"Error decoding JSON from {filepath}: {e}")
        return None
    except Exception as e:
        _log(f"Error loading patch note from {filepath}: {e}")
        return None

if __name__ == "__main__":
    print("--- Testing JSON Storage ---")

    # Ensure DATA_DIR is clean for a predictable test, or manage existing files
    # For this test, we'll proceed assuming it might have prior test files.

    sample_data_1 = {
        "url": "https://www.pathofexile.com/forum/view-thread/sample1",
        "title": "Major Update Alpha",
        "date": "2023-01-15T10:00:00", # ISO format
        "thread_id": "sample1_thread",
        "cleaned_text": "This is the first major update with many changes. Buffs to skills.",
        "summary": "First major update. Skill buffs.",
        "keywords": ["buff", "update", "major"],
        "sections": [{"title": "General Changes", "content": "Lots of things changed."}],
        "raw_html_preserved": "<html><body><h1>Alpha</h1><p>Content</p></body></html>"
    }

    sample_data_2 = {
        "url": "https://www.pathofexile.com/forum/view-thread/sample2",
        "title": "Minor Hotfix Beta",
        "date": "2023-01-16", # Different date format (YYYY-MM-DD)
        "thread_id": "sample2_thread",
        "cleaned_text": "This is a minor hotfix. Nerfs to some items.",
        "summary": "Minor hotfix. Item nerfs.",
        "keywords": ["nerf", "hotfix", "minor"],
        "sections": [{"title": "Bug Fixes", "content": "Fixed some bugs."}],
        "raw_html_preserved": "<html><body><h1>Beta</h1><p>Fixes</p></body></html>"
    }
    
    # Save first patch note
    print("\nAttempting to save patch note 1...")
    filepath1_actual = save_processed_patch_note(sample_data_1) # Filename includes slug
    if filepath1_actual:
        print(f"Filepath for patch 1: {filepath1_actual}")

    # Attempt to save it again (should skip)
    print("\nAttempting to save patch note 1 again (should skip)...")
    save_processed_patch_note(sample_data_1)

    # Save second patch note
    print("\nAttempting to save patch note 2...")
    filepath2_actual = save_processed_patch_note(sample_data_2)
    if filepath2_actual:
        print(f"Filepath for patch 2: {filepath2_actual}")

    # Load the latest patch note
    print("\nLoading latest patch note...")
    latest_note = load_latest_patch_note()
    if latest_note:
        print(f"Loaded latest patch: '{latest_note.get('title')}' (Date: {latest_note.get('date')})")
    else:
        print("No latest patch note found or error loading.")

    # Load a specific patch note by filename
    # We need to construct the expected filename based on our slugify logic
    expected_filename1 = "2023-01-15_major-update-alpha.json"
    print(f"\nLoading patch note by filename: {expected_filename1}...")
    specific_note = load_patch_note_by_filename(expected_filename1)
    if specific_note:
        print(f"Loaded specific patch: {specific_note.get('title')}")
    else:
        print(f"Could not load {expected_filename1}.")

    # Test with problematic date to ensure slugify and filename generation handles it
    problem_date_data = {
        "url": "url_problem_date", "title": "Test Date Issue", "date": "Some Weird Date Format!!", 
        "thread_id": "date_issue", "cleaned_text": "text", "summary": "sum", "keywords": [], "sections": []
    }
    print("\nAttempting to save patch note with problematic date...")
    save_processed_patch_note(problem_date_data) # Expected: ...some-weird-date-format_test-date-issue.json

    # Test with problematic title
    problem_title_data = {
        "url": "url_problem_title", "title": "!@#$%^&*()_+", "date": "2023-03-03", 
        "thread_id": "title_issue", "cleaned_text": "text", "summary": "sum", "keywords": [], "sections": []
    }
    print("\nAttempting to save patch note with problematic title (should become 'untitled-patch' or similar if slug is empty)...")
    # Slugify will make this empty, so it should become "untitled-patch"
    save_processed_patch_note(problem_title_data) # Expected: 2023-03-03_untitled-patch.json

    print("\n--- End of Storage Tests ---")
