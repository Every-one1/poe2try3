# gemini_analyzer.py
import google.generativeai as genai
import os
import poe2_wiki_scraper
import poe2_community_scraper
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
MODEL_NAME = "gemini-2.5-flash-preview-04-17" 

def generate_search_suggestions(build_data):
    """Uses Gemini to generate relevant search terms for community research."""
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
                suggestions = json.loads(response.text)
                if isinstance(suggestions, list):
                    return suggestions
            except json.JSONDecodeError:
                print("Warning: Could not parse Gemini's search suggestions")
        return []
    except Exception as e:
        print(f"Error generating search suggestions: {e}")
        return []

def gather_additional_data(build_data, search_queries):
    """Gathers additional data from various sources to enhance the analysis."""
    additional_data = {
        "wiki_data": {},
        "community_data": {},
        "patch_notes": None
    }
    
    # Get main skill name from build data
    main_skill = build_data.get("main_skill_name", "")
    if main_skill:
        print(f"\nFetching wiki data for main skill: {main_skill}")
        additional_data["wiki_data"]["main_skill"] = poe2_wiki_scraper.get_wiki_data(main_skill, "skill")
        
        # Search using the generated queries
        print("\nSearching community resources...")
        
        # Search Reddit
        print("\nSearching Reddit for relevant discussions...")
        reddit_posts = []
        for category, queries in search_queries.items():
            for query in queries:
                print(f"Searching for: {query}")
                reddit_data = poe2_community_scraper.get_reddit_posts(query)
                if reddit_data and reddit_data.get("posts"):
                    reddit_posts.extend(reddit_data["posts"])
        if reddit_posts:
            additional_data["community_data"]["reddit"] = {"posts": reddit_posts}
        
        # Search forums
        print("\nSearching official forums...")
        forum_posts = []
        for category, queries in search_queries.items():
            for query in queries:
                print(f"Searching for: {query}")
                forum_data = poe2_community_scraper.get_forum_posts(query)
                if forum_data and forum_data.get("posts"):
                    forum_posts.extend(forum_data["posts"])
        if forum_posts:
            additional_data["community_data"]["forum"] = {"posts": forum_posts}
        
        # Search build guides
        print("\nSearching for build guides...")
        class_name = build_data.get("className", "")
        guide_posts = []
        for category, queries in search_queries.items():
            for query in queries:
                print(f"Searching for: {query}")
                guides_data = poe2_community_scraper.get_build_guides(query, class_name)
                if guides_data and guides_data.get("guides"):
                    guide_posts.extend(guides_data["guides"])
        if guide_posts:
            additional_data["community_data"]["guides"] = {"guides": guide_posts}
    
    # Get wiki data for unique items
    print("\nFetching wiki data for unique items...")
    unique_items = []
    for item in build_data.get("equipped_items", []):
        if item.get("rarity") == "UNIQUE":
            unique_items.append(item.get("name"))
    
    for item_name in unique_items:
        print(f"Fetching data for: {item_name}")
        additional_data["wiki_data"][f"item_{item_name}"] = poe2_wiki_scraper.get_wiki_data(item_name, "item")
    
    # Get latest patch notes
    print("\nFetching patch notes...")
    additional_data["patch_notes"] = poe2_wiki_scraper.get_patch_notes()
    
    return additional_data

def format_additional_data(additional_data):
    """Formats the additional data into a string for the prompt."""
    formatted = []
    
    # Format wiki data
    if additional_data["wiki_data"]:
        formatted.append("\n=== WIKI DATA ===")
        for key, data in additional_data["wiki_data"].items():
            if data:
                formatted.append(f"\n{key.upper()}:")
                if data.get("description"):
                    formatted.append(f"Description: {data['description']}")
                if data.get("mechanics"):
                    formatted.append("Mechanics:")
                    for mechanic in data["mechanics"]:
                        formatted.append(f"- {mechanic}")
                if data.get("synergies"):
                    formatted.append("Synergies:")
                    for synergy in data["synergies"]:
                        formatted.append(f"- {synergy}")
    
    # Format community data
    if additional_data["community_data"]:
        formatted.append("\n=== COMMUNITY DATA ===")
        
        # Reddit posts
        if additional_data["community_data"].get("reddit", {}).get("posts"):
            formatted.append("\nRelevant Reddit Posts:")
            for post in additional_data["community_data"]["reddit"]["posts"]:
                formatted.append(f"\n- {post['title']}")
                formatted.append(f"  Score: {post['score']}, Comments: {post['num_comments']}")
                formatted.append(f"  {post['selftext'][:200]}...")
        
        # Forum posts
        if additional_data["community_data"].get("forum", {}).get("posts"):
            formatted.append("\nRelevant Forum Posts:")
            for post in additional_data["community_data"]["forum"]["posts"]:
                formatted.append(f"\n- {post['title']}")
                formatted.append(f"  Author: {post['author']}")
                formatted.append(f"  {post['content'][:200]}...")
        
        # Build guides
        if additional_data["community_data"].get("guides", {}).get("guides"):
            formatted.append("\nRelevant Build Guides:")
            for guide in additional_data["community_data"]["guides"]["guides"]:
                formatted.append(f"\n- {guide['title']}")
                formatted.append(f"  Author: {guide['author']}")
                formatted.append(f"  Source: {guide['source']}")
    
    # Format patch notes
    if additional_data["patch_notes"]:
        formatted.append("\n=== LATEST PATCH NOTES ===")
        latest_patch = additional_data["patch_notes"].get("latest_patch")
        if latest_patch:
            formatted.append(f"\n{latest_patch['title']}")
            formatted.append(f"Date: {latest_patch['date']}")
            for content in latest_patch["content"]:
                formatted.append(f"\n{content}")
        
        # Add a summary of other recent patches
        all_patches = additional_data["patch_notes"].get("all_patches", [])
        if len(all_patches) > 1:
            formatted.append("\nOther Recent Patches:")
            for patch in all_patches[1:4]:  # Show up to 3 more recent patches
                formatted.append(f"\n- {patch['title']} ({patch['date']})")
    
    return "\n".join(formatted)

def analyze_build_with_gemini(build_data_string, user_goals_and_context=""):
    """Sends the build data to Gemini and returns its analysis."""
    try:
        model = genai.GenerativeModel(MODEL_NAME, safety_settings=SAFETY_SETTINGS)
        
        # Parse build data string into a dictionary
        try:
            build_data = json.loads(build_data_string)
        except json.JSONDecodeError:
            build_data = {"raw_data": build_data_string}

        # First, get Gemini to analyze the build and suggest search queries
        print("\nPerforming initial build analysis to generate search queries...")
        initial_analysis_prompt = f"""
        Analyze this Path of Exile 2 build and identify key aspects that would be important to research.
        Focus on:
        1. Main skill mechanics and potential synergies
        2. Unique items and their interactions
        3. Build archetype and playstyle
        4. Potential optimization points
        5. Recent changes that might affect the build

        For each aspect, suggest 2-3 specific search queries that would help find relevant discussions, guides, or feedback.
        Format your response as a JSON object with the following structure:
        {{
            "main_skill_queries": ["query1", "query2"],
            "item_queries": ["query1", "query2"],
            "archetype_queries": ["query1", "query2"],
            "optimization_queries": ["query1", "query2"],
            "recent_changes_queries": ["query1", "query2"]
        }}

        Build Data:
        {json.dumps(build_data, indent=2)}
        """

        print("Requesting initial analysis from Gemini...")
        initial_response = model.generate_content(initial_analysis_prompt)
        
        if not initial_response.parts:
            print("Warning: Initial analysis failed, proceeding with basic search terms")
            search_queries = {
                "main_skill_queries": [build_data.get("main_skill_name", "")],
                "item_queries": [],
                "archetype_queries": [],
                "optimization_queries": [],
                "recent_changes_queries": []
            }
        else:
            try:
                search_queries = json.loads(initial_response.text)
                print("\nGenerated search queries:")
                for category, queries in search_queries.items():
                    print(f"\n{category.replace('_', ' ').title()}:")
                    for query in queries:
                        print(f"- {query}")
            except json.JSONDecodeError:
                print("Warning: Could not parse Gemini's search queries, proceeding with basic terms")
                search_queries = {
                    "main_skill_queries": [build_data.get("main_skill_name", "")],
                    "item_queries": [],
                    "archetype_queries": [],
                    "optimization_queries": [],
                    "recent_changes_queries": []
                }
        
        # Gather additional data using the generated queries
        print("\nGathering additional data from various sources...")
        additional_data = gather_additional_data(build_data, search_queries)
        formatted_additional_data = format_additional_data(additional_data)
        
        poe2_context_clarifications = """
IMPORTANT CONTEXT FOR PATH OF EXILE 2 ANALYSIS:
- This analysis is strictly for PATH OF EXILE 2. Ignore Path of Exile 1 mechanics where they differ significantly.
- Armour: In PoE2, Armour's effectiveness and typical investment levels differ from PoE1. Do not over-criticize a lack of heavy Armour if other defensive layers suitable for PoE2 are present.
- Flasks, Support Gems, Ascendancies: Mechanics for these are specific to PoE2.
- If detailed information for the main skill is provided from an external database (like poe2db.tw), please give that information high importance when analyzing the skill's mechanics, scaling, and potential.
- Consider the latest patch notes and community feedback when making recommendations.
- Focus on PoE2-specific synergies and mechanics rather than PoE1 knowledge.
"""
        if user_goals_and_context:
            poe2_context_clarifications += f"\nUSER-SPECIFIC GOALS & CONTEXT:\n{user_goals_and_context}\n"

        prompt_template = f"""
You are a Path of Exile 2 build optimization expert. I will provide you with data extracted from a Path of Building 2 XML file, augmented with details from various sources including the PoE2 wiki, community forums, and build guides.
Your task is to analyze this build in detail and provide actionable advice, focusing specifically on PoE2 mechanics and synergies.

{poe2_context_clarifications}

Please consider the following aspects based on the provided PoE2 context:
1.  **Overall Build Archetype:** Identify the primary damage dealing skill, its damage type(s), and core scaling mechanics within PoE2.
2.  **Offensive Evaluation:** Assess DPS, key contributing stats, and any damage scaling bottlenecks.
3.  **Defensive Evaluation (PoE2 specific):** Assess survivability based on relevant PoE2 layers (Life, ES, Evasion, Ward, Resists, Spell Suppression, etc.). Comment on EHP.
4.  **Gear Analysis:** Evaluate gear suitability for PoE2. Identify weak pieces and suggest upgrade stats.
5.  **Skill Gem Analysis (PoE2 specific):** Review main skill supports. Comment on utility skills for PoE2.
6.  **Passive Tree Analysis:** General assessment for PoE2. Suggest pathing or key clusters for the archetype in PoE2.
7.  **Top 3-5 Actionable Improvement Suggestions:** Summarize critical improvements for damage and survivability, tailored for PoE2.
8.  **Community Insights:** Reference relevant community discussions and build guides to support your analysis.
9.  **Patch Notes Impact:** Consider how recent changes might affect the build's performance.

Here is the build data:
--- BUILD DATA START ---
{build_data_string}
--- BUILD DATA END ---

Additional data from various sources:
--- ADDITIONAL DATA START ---
{formatted_additional_data}
--- ADDITIONAL DATA END ---

Provide your analysis in a clear, structured format. Use markdown for readability.
Focus on providing practical and actionable advice for a player looking to improve this character in Path of Exile 2.
"""
        
        print(f"\nSending data to Gemini model: {MODEL_NAME}...")
        response = model.generate_content(prompt_template)
        
        if response.parts:
            return response.text
        else:
            print("Gemini response might be empty or blocked.")
            print(f"Prompt Feedback: {response.prompt_feedback}")
            if not response.candidates:
                return "Error: No candidates returned from Gemini. This often indicates a blocking issue or an internal error."
            for candidate in response.candidates:
                print(f"Candidate Finish Reason: {candidate.finish_reason}")
                if candidate.safety_ratings:
                    for rating in candidate.safety_ratings:
                        print(f"Safety Rating: {rating.category} - {rating.probability}")
            return "Error: No content parts returned from Gemini. The prompt might have been blocked. Check console for details."

    except Exception as e:
        print(f"An error occurred while communicating with Gemini: {e}")
        if "API key not valid" in str(e) or "API_KEY_INVALID" in str(e):
            print("CRITICAL ERROR: The provided API key is invalid.")
            return "Error: Invalid Gemini API Key."
        return f"Error analyzing build: {e}"

if __name__ == "__main__":
    print("Gemini Analyzer - Direct Test Mode (using placeholder data)")
    placeholder_build_data = "Minimal placeholder data for direct gemini_analyzer.py test."
    
    if not API_KEY or API_KEY == "YOUR_API_KEY_PLACEHOLDER_TEXT":
        print("ERROR: Please set your GEMINI_API_KEY in the script for this test.")
    else:
        analysis = analyze_build_with_gemini(placeholder_build_data, "User goal: test basic response.")
        print("\n--- GEMINI ANALYSIS (Placeholder Test) ---")
        print(analysis)
