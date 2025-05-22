# main.py
import xml_parser
import gemini_analyzer
import poe2db_scraper 
import os
import time
import json
from datetime import datetime

def clear_console():
    if os.name == 'nt': _ = os.system('cls')
    else: _ = os.system('clear')

def main():
    build_xml_file = "sample_build.xml" 
    POE2DB_BASE_URL = "https://poe2db.tw/us/"
    
    print("Starting Path of Exile 2 Build Analyzer...")
    print("=" * 50)

    if not os.path.exists(build_xml_file):
        print(f"ERROR: Build XML file not found at '{build_xml_file}'")
        return

    print(f"Loading and parsing build from: {build_xml_file}")
    root_element = xml_parser.load_xml_from_file(build_xml_file)

    if root_element is None:
        print("Failed to parse XML. Exiting.")
        return

    print("\nExtracting build data from XML...")
    print("- Extracting basic information...")
    basics = xml_parser.extract_build_basics(root_element)
    print("- Extracting character stats...")
    char_stats = xml_parser.extract_character_stats(root_element)
    print("- Extracting skills data...")
    skills_xml_data = xml_parser.extract_skills_data(root_element)
    print("- Extracting items data...")
    items_xml_data = xml_parser.extract_items_data(root_element)
    print("- Extracting passive tree data...")
    tree = xml_parser.extract_passive_tree_data(root_element)
    
    all_scraped_details = {"skills": [], "items": []}
    processed_elements_for_scraping = set() 

    # --- Scrape Skills ---
    unique_skill_names_from_xml = set()
    for skill_group in skills_xml_data.get("all_skills", []):
        for gem in skill_group.get("gems", []):
            gem_name = gem.get("name")
            if gem_name and gem_name.strip() != "" and "vaal" not in gem_name.lower() and "skillgem" not in gem.get("skillId", "").lower(): 
                 unique_skill_names_from_xml.add(gem_name)

    print(f"\nFound {len(unique_skill_names_from_xml)} unique active skill names in PoB XML to potentially scrape.")
    for i, skill_name in enumerate(unique_skill_names_from_xml, 1):
        if skill_name in processed_elements_for_scraping:
            continue
        
        print(f"\nProcessing skill {i}/{len(unique_skill_names_from_xml)}: {skill_name}")
        skill_slug = skill_name.replace(" ", "_") 
        if not skill_slug: continue
        
        skill_url_to_scrape = f"{POE2DB_BASE_URL}{skill_slug}"
        print(f"Attempting to scrape: {skill_url_to_scrape}")
        
        scraped_detail = poe2db_scraper.get_scraped_data(skill_url_to_scrape, skill_name) 
        
        if scraped_detail and scraped_detail.get("name", "N/A") != "N/A":
            all_scraped_details["skills"].append(scraped_detail)
            processed_elements_for_scraping.add(skill_name) 
            processed_elements_for_scraping.add(scraped_detail["name"])
            print(f"✓ Successfully scraped skill: {scraped_detail['name']}")
        else:
            print(f"✗ Warning: Could not get valid details for skill '{skill_name}'")
        time.sleep(0.2)

    # --- Scrape Unique Items ---
    unique_item_names_from_xml = set()
    for item in items_xml_data.get("equipped_items", []):
        if item.get("rarity") == "UNIQUE":
            item_name = item.get("name")
            if item_name and item_name != "Unknown Item":
                unique_item_names_from_xml.add(item_name)

    print(f"\nFound {len(unique_item_names_from_xml)} unique item names in PoB XML to potentially scrape.")
    for i, item_name in enumerate(unique_item_names_from_xml, 1):
        if item_name in processed_elements_for_scraping:
            continue

        print(f"\nProcessing item {i}/{len(unique_item_names_from_xml)}: {item_name}")
        item_slug = item_name.replace(" ", "_").replace("'", "").replace("-", "_")
        if not item_slug: continue
        
        item_url_to_scrape = f"{POE2DB_BASE_URL}{item_slug}" 
        print(f"Attempting to scrape: {item_url_to_scrape}")
        
        scraped_detail = poe2db_scraper.get_scraped_data(item_url_to_scrape, item_name)
        if scraped_detail and scraped_detail.get("name", "N/A") != "N/A":
            all_scraped_details["items"].append(scraped_detail)
            processed_elements_for_scraping.add(item_name)
            processed_elements_for_scraping.add(scraped_detail["name"])
            print(f"✓ Successfully scraped item: {scraped_detail['name']}")
        else:
            print(f"✗ Warning: Could not get valid details for item '{item_name}'")
        time.sleep(0.2)

    print("\nFormatting all data for LLM analysis...")
    build_data = {
        "basics": basics,
        "char_stats": char_stats,
        "skills": skills_xml_data,
        "items": items_xml_data,
        "tree": tree,
        "scraped_details": all_scraped_details
    }
    
    llm_input_string = json.dumps(build_data, indent=2)
    
    try:
        with open("llm_input_debug.txt", "w", encoding="utf-8") as f:
            f.write(llm_input_string)
        print("Formatted data saved to llm_input_debug.txt for review.")
    except Exception as e:
        print(f"Error writing to llm_input_debug.txt: {e}")

    print("\n--- OPTIONAL: PROVIDE YOUR GOALS/CONTEXT ---")
    user_goals = input("What are your specific goals or context? (Press Enter to skip): \n> ")
    
    print("\nRequesting analysis from Gemini AI...")
    print("(This may take a moment as we gather additional data from various sources...)")
    
    analysis_result = gemini_analyzer.analyze_build_with_gemini(llm_input_string, user_goals)

    # --- Output Handling: Save to File ---
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    analysis_filename = f"PoE2_Build_Analysis_{timestamp}.md"
    
    try:
        with open(analysis_filename, "w", encoding="utf-8") as f:
            # Add a header to the file
            f.write(f"# Path of Exile 2 Build Analysis Report\n\n")
            f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            if basics:
                f.write(f"**Character:** {basics.get('className')} {basics.get('ascendClassName')}, Level {basics.get('level')}\n\n")
                f.write(f"**Main Skill (PoB):** {skills_xml_data.get('main_skill_name', 'N/A')}, **DPS (PoB):** {basics.get('totalDPS', char_stats.get('TotalDPS', 'N/A'))}\n\n")
            if user_goals:
                f.write(f"**Your Stated Goals/Context:** {user_goals}\n\n")
            f.write("---\n\n")
            
            f.write(analysis_result)

        print(f"\n--- Analysis Complete ---")
        print(f"Full analysis report saved to: {analysis_filename}")
        
        # Print a brief summary to console
        print("\n--- Summary (See file for full details) ---")
        summary_lines = analysis_result.split('\n')[:10]
        print('\n'.join(summary_lines) + '\n...')

    except Exception as e:
        print(f"\nError saving analysis report to {analysis_filename}: {e}")
        print("\n--- FULL ANALYSIS REPORT (Error saving to file) ---")
        print(analysis_result)

if __name__ == "__main__":
    main()