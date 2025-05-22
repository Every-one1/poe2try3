# gemini_analyzer.py
import google.generativeai as genai
import os
from scraper import poe2_wiki_scraper
from scraper import poe2_community_scraper
from scraper import patch_notes_scraper # Added for get_patch_notes
import json

API_KEY = "" # Your key

if not API_KEY or API_KEY == "YOUR_API_KEY_PLACEHOLDER_TEXT":
    raise ValueError("API_KEY is not set correctly in the script.")

genai.configure(api_key=API_KEY)

SAFETY_SETTINGS = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
]
MODEL_NAME = "gemini-1.5-flash"

def _log_message(message, progress_callback=None):
    if progress_callback:
        progress_callback(message)
    else:
        print(message) # Fallback for direct calls or tests

def generate_search_suggestions(build_data, progress_callback=None):
    """Uses Gemini to generate relevant search terms for community research."""
    _log_message("Generating search suggestions with Gemini...", progress_callback)
    try:
        model = genai.GenerativeModel(MODEL_NAME, safety_settings=SAFETY_SETTINGS)
        
        prompt = f"""
        Based on this Path of Exile 2 build data, suggest 3-5 specific search terms or phrases that would be useful for finding relevant community discussions, guides, and feedback.
        Focus on:
        1. The main skill and its mechanics
        2. Key unique items
        3. Build archetype and playstyle
        4. Potential synergies or interactions
        
        Build Data:
        {json.dumps(build_data, indent=2)}
        
        Return the suggestions as a JSON array of strings.
        """
        
        response = model.generate_content(prompt)
        if response.parts:
            try:
                # Attempt to remove markdown and parse JSON
                cleaned_response_text = response.text.replace('```json', '').replace('```', '').strip()
                suggestions = json.loads(cleaned_response_text)
                if isinstance(suggestions, list):
                    _log_message(f"Generated {len(suggestions)} search suggestions.", progress_callback)
                    return suggestions
            except json.JSONDecodeError:
                _log_message(f"Warning: Could not parse Gemini's search suggestions. Raw text: {response.text}", progress_callback)
        return []
    except Exception as e:
        _log_message(f"Error generating search suggestions: {e}", progress_callback)
        return []

def gather_additional_data(build_data, search_queries, progress_callback=None):
    """Gathers additional data from various sources to enhance the analysis."""
    _log_message("Starting to gather additional data...", progress_callback)
    additional_data = {
        "wiki_data": {},
        "community_data": {},
        "patch_notes_data": None
    }
    
    main_skill_name_from_xml = build_data.get("skills_xml", {}).get("main_skill_name", "")
    class_name_from_xml = build_data.get("basics", {}).get("className", "")

    if main_skill_name_from_xml:
        _log_message(f"Fetching wiki data for main skill: {main_skill_name_from_xml}", progress_callback)
        additional_data["wiki_data"]["main_skill"] = poe2_wiki_scraper.get_wiki_data(main_skill_name_from_xml, "skill", progress_callback=progress_callback)
    
    unique_items_from_xml = []
    if build_data.get("items_xml", {}).get("equipped_items"):
        for item in build_data["items_xml"]["equipped_items"]:
            if item.get("rarity") == "UNIQUE" and item.get("name") != "Unknown Item":
                unique_items_from_xml.append(item["name"])

    if unique_items_from_xml:
        _log_message(f"Fetching wiki data for {len(unique_items_from_xml)} unique items...", progress_callback)
        for item_name in unique_items_from_xml:
            _log_message(f"Fetching wiki data for item: {item_name}", progress_callback)
            additional_data["wiki_data"][f"item_{item_name.replace(' ', '_')}"] = poe2_wiki_scraper.get_wiki_data(item_name, "item", progress_callback=progress_callback)

    if search_queries:
        _log_message("Searching community resources using generated queries...", progress_callback)
        all_reddit_posts = []
        all_forum_posts = []
        all_build_guides = []

        # Ensure search_queries is a list of strings, not a dict
        if isinstance(search_queries, dict): # Common mistake if generate_search_suggestions returns a dict
            actual_queries = []
            for q_list in search_queries.values(): # If it's a dict of lists of queries
                if isinstance(q_list, list):
                    actual_queries.extend(q_list)
            search_queries = actual_queries
        
        if not isinstance(search_queries, list):
             _log_message(f"Warning: search_queries is not a list, skipping community search. Type: {type(search_queries)}", progress_callback)
        else:
            for query in search_queries:
                if not isinstance(query, str):
                    _log_message(f"Warning: Query '{query}' is not a string, skipping.", progress_callback)
                    continue
                _log_message(f"Searching Reddit for: {query}", progress_callback)
                reddit_data = poe2_community_scraper.get_reddit_posts(query, progress_callback=progress_callback)
                if reddit_data and reddit_data.get("posts"):
                    all_reddit_posts.extend(reddit_data["posts"])
                
                _log_message(f"Searching official forums for: {query}", progress_callback)
                forum_data = poe2_community_scraper.get_forum_posts(query, progress_callback=progress_callback)
                if forum_data and forum_data.get("posts"):
                    all_forum_posts.extend(forum_data["posts"])
                
                _log_message(f"Searching build guides for: {query} (Class: {class_name_from_xml})", progress_callback)
                guides_data = poe2_community_scraper.get_build_guides(query, class_name_from_xml, progress_callback=progress_callback)
                if guides_data and guides_data.get("guides"):
                    all_build_guides.extend(guides_data["guides"])
        
        if all_reddit_posts:
            additional_data["community_data"]["reddit"] = {"posts": all_reddit_posts[:10]}
        if all_forum_posts:
            additional_data["community_data"]["forum"] = {"posts": all_forum_posts[:10]}
        if all_build_guides:
            additional_data["community_data"]["guides"] = {"guides": all_build_guides[:5]}
    
    _log_message("Fetching latest patch notes from forum...", progress_callback)
    additional_data["patch_notes_data"] = patch_notes_scraper.get_patch_notes(progress_callback=progress_callback) 
    
    _log_message("Finished gathering additional data.", progress_callback)
    return additional_data

def format_additional_data(additional_data, progress_callback=None):
    """Formats the additional data into a string for the prompt."""
    _log_message("Formatting additional data for LLM prompt...", progress_callback)
    formatted = []
    
    if additional_data.get("wiki_data"):
        formatted.append("\n=== WIKI DATA ===")
        for key, data in additional_data["wiki_data"].items():
            if data and data.get("name"):
                formatted.append(f"\n--- {data['name']} ({data.get('type', 'N/A')}) ---")
                if data.get("description"): formatted.append(f"Description: {data['description']}")
                if data.get("mechanics"): formatted.append(f"Mechanics: {data['mechanics']}")
                if data.get("lore"): formatted.append(f"Lore: {data['lore']}")
                if data.get("version_history"):
                    formatted.append("Version History (from Wiki):")
                    for entry in data["version_history"][:3]: formatted.append(f"- {entry}")
    
    if additional_data.get("community_data"):
        formatted.append("\n\n=== COMMUNITY INSIGHTS (Highlights) ===")
        if additional_data["community_data"].get("reddit", {}).get("posts"):
            formatted.append("\n--- Relevant Reddit Posts (Sample) ---")
            for post in additional_data["community_data"]["reddit"]["posts"][:2]:
                formatted.append(f"\nTitle: {post.get('title', 'N/A')}")
                formatted.append(f"Snippet: {post.get('selftext', '')[:250]}...")
        if additional_data["community_data"].get("guides", {}).get("guides"):
            formatted.append("\n--- Relevant Build Guides (Sample) ---")
            for guide in additional_data["community_data"]["guides"]["guides"][:1]:
                formatted.append(f"\nTitle: {guide.get('title', 'N/A')} (Source: {guide.get('source', 'N/A')})")

    if additional_data.get("patch_notes_data"):
        patch_info = additional_data["patch_notes_data"]
        if patch_info and patch_info.get("latest_patch"): 
            latest = patch_info["latest_patch"]
            if latest: 
                formatted.append("\n\n=== LATEST PATCH NOTES (Forum) ===")
                formatted.append(f"\nTitle: {latest.get('title', 'N/A')} (Date: {latest.get('date', 'N/A')})")
                formatted.append(f"Summary: {str(latest.get('text_content', ''))[:500]}...")
    
    _log_message("Finished formatting additional data.", progress_callback)
    return "\n".join(formatted)

def analyze_build_with_gemini(build_data_json_string, user_goals_and_context="", progress_callback=None):
    """Sends the build data (XML + Scraped) to Gemini and returns its analysis."""
    _log_message("Starting build analysis with Gemini...", progress_callback)
    if not API_KEY or API_KEY == "YOUR_API_KEY_PLACEHOLDER_TEXT":
        _log_message("Error: Gemini API Key not configured for analyze_build_with_gemini.", progress_callback)
        return "Error: Gemini API Key not configured."
    try:
        model = genai.GenerativeModel(MODEL_NAME, safety_settings=SAFETY_SETTINGS)
        
        build_data_dict = json.loads(build_data_json_string)

        search_suggestion_input = {
            "main_skill_name": build_data_dict.get("skills_xml", {}).get("main_skill_name"),
            "className": build_data_dict.get("basics", {}).get("className"),
            "ascendClassName": build_data_dict.get("basics", {}).get("ascendClassName"),
            "equipped_items": build_data_dict.get("items_xml", {}).get("equipped_items", [])
        }
        
        _log_message("Generating search queries for community data...", progress_callback)
        search_queries = generate_search_suggestions(search_suggestion_input, progress_callback=progress_callback)
        
        _log_message("Gathering additional data (Wiki, Community, Patch Notes)...", progress_callback)
        additional_data_dict = gather_additional_data(build_data_dict, search_queries if search_queries else {}, progress_callback=progress_callback)
        formatted_additional_data = format_additional_data(additional_data_dict, progress_callback=progress_callback)
        
        poe2_context_clarifications = "..." 

        prompt = f"""
        You are a Path of Exile 2 build analysis expert.
        Provided build data (from Path of Building XML and poe2db):
        {build_data_json_string}

        Additional context from Wiki, Community Discussions, and Patch Notes:
        {formatted_additional_data}

        User's Goals/Context: {user_goals_and_context if user_goals_and_context else "General build improvement."}

        {poe2_context_clarifications}
        Please provide a structured analysis and actionable advice for Path of Exile 2.
        Focus on: Overall Archetype, Offense, Defense, Gear, Skills, Passive Tree, Top 3-5 Improvements.
        Integrate insights from the additional context provided.
        """
        
        _log_message(f"Sending comprehensive data to Gemini model: {MODEL_NAME}...", progress_callback)
        response = model.generate_content(prompt)
        
        if response.parts:
            _log_message("Gemini analysis successful.", progress_callback)
            return response.text
        else:
            _log_message(f"Warning: Gemini response might be empty or blocked. Prompt Feedback: {response.prompt_feedback}", progress_callback)
            if response.candidates:
                for candidate in response.candidates:
                    _log_message(f"Candidate Finish Reason: {candidate.finish_reason}", progress_callback)
                    if candidate.safety_ratings:
                        for rating in candidate.safety_ratings:
                             _log_message(f"Safety Rating: {rating.category} - {rating.probability}", progress_callback)
            return "Error: No content parts returned from Gemini. The prompt might have been blocked or the response was empty. Check console for details."

    except Exception as e:
        _log_message(f"An error occurred while communicating with Gemini: {e}", progress_callback)
        return f"Error analyzing build: {e}"

def summarize_patch_note_with_llm(processed_patch_data, progress_callback=None):
    """Generates a concise, engaging summary of a patch note using Gemini."""
    _log_message("Attempting to summarize patch note with LLM...", progress_callback)
    if not API_KEY or API_KEY == "YOUR_API_KEY_PLACEHOLDER_TEXT":
        _log_message("Error: Gemini API Key not configured for summarize_patch_note_with_llm.", progress_callback)
        return "Error: Gemini API Key not configured."
    if not processed_patch_data: 
        _log_message("Error: No processed patch data provided to summarize_patch_note_with_llm.", progress_callback)
        return "Error: No processed patch data provided."
    try:
        model = genai.GenerativeModel(MODEL_NAME, safety_settings=SAFETY_SETTINGS)
        prompt = f"""
        You are a Path of Exile news reporter. Generate a concise and engaging summary for the following game patch note. 
        Focus on the most impactful changes for players. Mention key buffs, nerfs, new content, and important fixes.

        Patch Note Title: {processed_patch_data.get('title', 'N/A')}
        Original Publication Date: {processed_patch_data.get('date', 'N/A')}
        Extracted Keywords: {", ".join(processed_patch_data.get('keywords', []))}
        Key Content Snippet:
        ---
        {processed_patch_data.get('cleaned_text', '')[:1500]}
        ---
        Provide a new, well-written summary suitable for a quick player update.
        """
        response = model.generate_content(prompt)
        if response.parts:
            _log_message("LLM summary generated successfully.", progress_callback)
            return response.text
        else:
            _log_message("Error: LLM response empty/blocked for summary.", progress_callback)
            return "Error: LLM response empty/blocked for summary."
    except Exception as e: 
        _log_message(f"Error summarizing patch note: {e}", progress_callback)
        return f"Error summarizing patch note: {e}"

def answer_question_on_patch_note_with_llm(processed_patch_data, question, progress_callback=None):
    """Answers a specific question based *solely* on the provided patch note content using Gemini."""
    _log_message(f"Attempting to answer question on patch note: '{question[:30]}...'", progress_callback)
    if not API_KEY or API_KEY == "YOUR_API_KEY_PLACEHOLDER_TEXT":
        _log_message("Error: Gemini API Key not configured for answer_question_on_patch_note_with_llm.", progress_callback)
        return "Error: Gemini API Key not configured."
    if not processed_patch_data or not question: 
        _log_message("Error: Missing data or question for answer_question_on_patch_note_with_llm.", progress_callback)
        return "Error: Missing data or question."
    try:
        model = genai.GenerativeModel(MODEL_NAME, safety_settings=SAFETY_SETTINGS)
        prompt = f"""
        Answer the user question based *only* on the provided patch note text. 
        If the answer isn't in the text, state that.

        Patch Note Context:
        Title: {processed_patch_data.get('title', 'N/A')}
        Date: {processed_patch_data.get('date', 'N/A')}
        Full Patch Note Text:
        ---
        {processed_patch_data.get('cleaned_text', '')}
        ---
        User Question: {question}
        Answer:
        """
        response = model.generate_content(prompt)
        if response.parts:
            _log_message("LLM answer generated successfully.", progress_callback)
            return response.text
        else:
            _log_message("Error: LLM response empty/blocked for Q&A.", progress_callback)
            return "Error: LLM response empty/blocked for Q&A."
    except Exception as e: 
        _log_message(f"Error answering question: {e}", progress_callback)
        return f"Error answering question: {e}"

if __name__ == "__main__":
    def _main_logger(message):
        print(f"[MainTestLogger] {message}")

    print("Gemini Analyzer - Direct Test Mode")
    if not API_KEY or API_KEY == "YOUR_API_KEY_PLACEHOLDER_TEXT":
        _main_logger("ERROR: GEMINI_API_KEY not set. Skipping LLM tests.")
    else:
        _main_logger("\n--- Testing Build Analysis (Simplified Call) ---")
        sample_build_overview_for_llm = {
            "basics": {"className": "Elementalist", "level": "90"},
            "skills_xml": {"main_skill_name": "Fireball"},
            "items_xml": {"equipped_items": [{"name": "The Consuming Dark", "rarity": "UNIQUE"}]}
        }
        build_analysis_result = analyze_build_with_gemini(
            json.dumps(sample_build_overview_for_llm), 
            "Focus on Fireball scaling for bossing.",
            progress_callback=_main_logger
        )
        _main_logger("\n--- GEMINI BUILD ANALYSIS RESULT ---")
        _main_logger(build_analysis_result)

        _main_logger("\n\n--- Testing Patch Note LLM Functions ---")
        sample_patch_data = {
            "title": "Hotfix 3.23.1b", "date": "2023-12-15T14:30:00",
            "cleaned_text": "Fixed a bug where Tornado skill dealt no damage. Buffed Fireball damage by 10%.",
            "keywords": ["tornado", "fireball", "buff"], "summary": "Tornado fix, Fireball buff."
        }
        summary = summarize_patch_note_with_llm(sample_patch_data, progress_callback=_main_logger)
        _main_logger(f"\nLLM Summary:\n{summary}")
        answer = answer_question_on_patch_note_with_llm(sample_patch_data, "What happened to Fireball?", progress_callback=_main_logger)
        _main_logger(f"\nQ: What happened to Fireball?\nA: {answer}")
