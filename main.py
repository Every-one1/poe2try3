# main.py
import click
import json
import os

# Attempt to import necessary functions
try:
    from scraper.patch_notes_scraper import get_patch_notes
    from scraper.poe2db_scraper import get_scraped_data as get_poe2db_scraped_data # Renamed for clarity
    from parsers.pob_xml_parser import load_xml_from_file, extract_build_basics, extract_character_stats, extract_skills_data, extract_items_data, extract_passive_tree_data
    from processor.patch_processor import process_patch_note
    from storage.json_storage import save_processed_patch_note, load_latest_patch_note
    from llm_interface.gemini_analyzer import summarize_patch_note_with_llm, analyze_build_with_gemini, API_KEY as GEMINI_API_KEY
    from datetime import datetime
    import time # For poe2db scraping delay
except ImportError as e:
    click.echo(f"Error: Could not import necessary modules. Please ensure all components are in place: {e}", err=True)
    # Exit if core components are missing, or handle gracefully
    # For now, we'll let Click handle it if a command that needs these is called.


@click.group()
def cli():
    """Path of Exile 2 Information Tool CLI"""
    pass

@cli.command("latest")
def latest():
    """Displays the latest processed patch note and optionally an LLM summary."""
    click.echo("Loading latest patch note...")
    try:
        latest_note_data = load_latest_patch_note()
    except Exception as e:
        click.echo(f"Error loading latest patch note: {e}", err=True)
        return

    if latest_note_data:
        click.echo(click.style("\n--- Latest Patch Note ---", fg="cyan", bold=True))
        click.echo(click.style(f"Title: {latest_note_data.get('title', 'N/A')}", fg="yellow"))
        click.echo(f"Date: {latest_note_data.get('date', 'N/A')}")
        click.echo("\nSummary (from processed data):")
        click.echo(latest_note_data.get('summary', 'No summary available.'))

        # Optional LLM Summary
        if GEMINI_API_KEY and GEMINI_API_KEY != "YOUR_API_KEY_PLACEHOLDER_TEXT":
            if click.confirm("\nDo you want an LLM-generated summary of this patch note? (requires API call)"):
                click.echo("Generating LLM summary...")
                try:
                    llm_summary = summarize_patch_note_with_llm(latest_note_data)
                    click.echo(click.style("\n--- LLM Generated Summary ---", fg="magenta", bold=True))
                    click.echo(llm_summary)
                except Exception as e:
                    click.echo(f"Error generating LLM summary: {e}", err=True)
        else:
            click.echo(click.style("\nNote: Gemini API key not configured. Skipping LLM summary option.", fg="red"))
        
        click.echo(click.style("\n--- End of Patch Note ---", fg="cyan"))
    else:
        click.echo("No processed patch notes found. Try running 'scrape-patchnotes' first.")

@cli.command("scrape-patchnotes")
def scrape_patchnotes():
    """Scrapes, processes, and stores new patch notes."""
    click.echo("Starting patch notes scraping process...")
    
    try:
        scraped_data_container = get_patch_notes() # This should return the dict with 'all_patches'
    except Exception as e:
        click.echo(f"Error during scraping: {e}", err=True)
        return

    if not scraped_data_container or not scraped_data_container.get("all_patches"):
        click.echo("Failed to fetch patch notes or no patch notes found from scraper.")
        return

    all_patches_from_scraper = scraped_data_container["all_patches"]
    click.echo(f"Scraper found {len(all_patches_from_scraper)} patch notes. Processing them now...")
    
    new_patches_processed_count = 0
    skipped_patches_count = 0

    for raw_patch_data in all_patches_from_scraper: # Assumes newest first from scraper
        click.echo(f"\nProcessing: {raw_patch_data.get('title', 'Unknown Title')}")
        try:
            processed_data = process_patch_note(raw_patch_data)
            if not processed_data:
                click.echo(f"  Skipped processing for: {raw_patch_data.get('title')}", fg="yellow")
                continue
            
            save_result = save_processed_patch_note(processed_data)
            
            if save_result is None: # None indicates already exists
                # message already printed by save_processed_patch_note
                skipped_patches_count += 1
            elif save_result is False: # False indicates a save error
                click.echo(f"  Failed to save: {processed_data.get('title')}", fg="red")
            else: # path string indicates success
                # message already printed by save_processed_patch_note
                new_patches_processed_count += 1
        except Exception as e:
            click.echo(f"  Error processing or saving patch '{raw_patch_data.get('title', 'Unknown Title')}': {e}", err=True)
            
    click.echo("\n--- Scraping and Processing Complete ---")
    click.echo(f"Successfully processed and saved: {new_patches_processed_count} new patch note(s).")
    click.echo(f"Skipped (already existing): {skipped_patches_count} patch note(s).")

# --- Refactored Pipeline Function ---
def run_patch_notes_pipeline(is_manual_run=True):
    """
    Core logic for scraping, processing, and storing patch notes.
    Can be called manually or by the scheduler.
    """
    if is_manual_run:
        click.echo("Starting patch notes pipeline (manual run)...")
    else:
        print(f"[{datetime.now()}] Running scheduled patch notes pipeline...") # Use print for scheduler logs

    try:
        scraped_data_container = get_patch_notes()
    except Exception as e:
        if is_manual_run:
            click.echo(f"Error during scraping: {e}", err=True)
        else:
            print(f"Error during scraping: {e}")
        return

    if not scraped_data_container or not scraped_data_container.get("all_patches"):
        if is_manual_run:
            click.echo("Failed to fetch patch notes or no patch notes found from scraper.")
        else:
            print("Failed to fetch patch notes or no patch notes found from scraper.")
        return

    all_patches_from_scraper = scraped_data_container["all_patches"]
    if is_manual_run:
        click.echo(f"Scraper found {len(all_patches_from_scraper)} patch notes. Processing them now...")
    else:
        print(f"Scraper found {len(all_patches_from_scraper)} patch notes. Processing them now...")
    
    new_patches_processed_count = 0
    skipped_patches_count = 0
    errors_count = 0

    for raw_patch_data in all_patches_from_scraper:
        title_for_log = raw_patch_data.get('title', 'Unknown Title')
        if is_manual_run:
            click.echo(f"\nProcessing: {title_for_log}")
        else:
            print(f"\nProcessing: {title_for_log}")
            
        try:
            processed_data = process_patch_note(raw_patch_data)
            if not processed_data:
                if is_manual_run:
                    click.echo(f"  Skipped processing for: {title_for_log}", fg="yellow")
                else:
                    print(f"  Skipped processing for: {title_for_log}")
                continue
            
            save_result = save_processed_patch_note(processed_data)
            
            if save_result is None:
                skipped_patches_count += 1
                # Message already printed by save_processed_patch_note
            elif save_result is False:
                errors_count +=1
                if is_manual_run:
                    click.echo(f"  Failed to save: {processed_data.get('title')}", fg="red")
                else:
                    print(f"  Failed to save: {processed_data.get('title')}")
            else:
                new_patches_processed_count += 1
                # Message already printed by save_processed_patch_note
        except Exception as e:
            errors_count +=1
            if is_manual_run:
                click.echo(f"  Error processing or saving patch '{title_for_log}': {e}", err=True)
            else:
                 print(f"  Error processing or saving patch '{title_for_log}': {e}")
    
    summary_message = f"""
--- Patch Notes Pipeline Summary ({'Manual' if is_manual_run else 'Scheduled'} Run) ---
Successfully processed and saved: {new_patches_processed_count} new patch note(s).
Skipped (already existing): {skipped_patches_count} patch note(s).
Errors during processing/saving: {errors_count} patch note(s).
--- End of Summary ---
"""
    if is_manual_run:
        click.echo(summary_message)
    else:
        print(summary_message)

# Modified Click command to call the pipeline function
@cli.command("scrape-patchnotes")
def scrape_patchnotes_command():
    """Scrapes, processes, and stores new patch notes."""
    run_patch_notes_pipeline(is_manual_run=True)

@cli.command("analyze-build")
@click.argument('xml_filepath', type=click.Path(exists=True, dir_okay=False, readable=True))
def analyze_build(xml_filepath):
    """Analyzes a Path of Building XML file and provides LLM-based insights."""
    click.echo(click.style(f"Starting build analysis for: {xml_filepath}", fg="cyan", bold=True))

    # 1. Load and Parse XML
    click.echo("Loading and parsing build XML...")
    try:
        root_element = load_xml_from_file(xml_filepath)
        if root_element is None:
            click.echo(click.style("Error: Failed to parse XML. The file might be corrupted or not a valid PoB XML.", fg="red"), err=True)
            return

        basics = extract_build_basics(root_element)
        char_stats = extract_character_stats(root_element)
        skills_xml_data = extract_skills_data(root_element)
        items_xml_data = extract_items_data(root_element)
        tree_data = extract_passive_tree_data(root_element)
        click.echo("XML data extracted successfully.")
    except Exception as e:
        click.echo(click.style(f"Error during XML parsing: {e}", fg="red"), err=True)
        return

    # 2. Scrape Additional Skill/Item Details (from poe2db)
    click.echo("Scraping additional details from poe2db.tw (this may take a moment)...")
    all_scraped_details = {"skills": [], "items": []}
    processed_elements_for_scraping = set()
    POE2DB_BASE_URL = "https://poe2db.tw/us/" # As used previously

    # Scrape Skills
    unique_skill_names_from_xml = set()
    if skills_xml_data and skills_xml_data.get("all_skills"):
        for skill_group in skills_xml_data.get("all_skills", []):
            for gem in skill_group.get("gems", []):
                gem_name = gem.get("name")
                # Filter for active, non-vaal, non-skillgem placeholder skills
                if gem_name and gem_name.strip() and gem.get("enabled") and \
                   "vaal" not in gem_name.lower() and "skillgem" not in gem.get("skillId", "").lower():
                    unique_skill_names_from_xml.add(gem_name)
    
    click.echo(f"Found {len(unique_skill_names_from_xml)} unique active skills in XML to scrape from poe2db.")
    for skill_name in unique_skill_names_from_xml:
        if skill_name in processed_elements_for_scraping:
            continue
        
        skill_slug = skill_name.replace(" ", "_")
        skill_url_to_scrape = f"{POE2DB_BASE_URL}{skill_slug}"
        click.echo(f"  Scraping skill: {skill_name} from {skill_url_to_scrape}")
        scraped_detail = get_poe2db_scraped_data(skill_url_to_scrape, skill_name)
        if scraped_detail and scraped_detail.get("name", "N/A") != "N/A":
            all_scraped_details["skills"].append(scraped_detail)
            processed_elements_for_scraping.add(skill_name)
            processed_elements_for_scraping.add(scraped_detail["name"]) # Add scraped name too
        else:
            click.echo(f"  Warning: Could not get valid details for skill '{skill_name}' from poe2db.", fg="yellow")
        time.sleep(0.3) # Be respectful to the server

    # Scrape Unique Items
    unique_item_names_from_xml = set()
    if items_xml_data and items_xml_data.get("equipped_items"):
        for item in items_xml_data.get("equipped_items", []):
            if item.get("rarity") == "UNIQUE":
                item_name = item.get("name")
                if item_name and item_name != "Unknown Item":
                    unique_item_names_from_xml.add(item_name)

    click.echo(f"Found {len(unique_item_names_from_xml)} unique items in XML to scrape from poe2db.")
    for item_name in unique_item_names_from_xml:
        if item_name in processed_elements_for_scraping:
            continue
        
        item_slug = item_name.replace(" ", "_").replace("'", "").replace("-", "_")
        item_url_to_scrape = f"{POE2DB_BASE_URL}{item_slug}"
        click.echo(f"  Scraping item: {item_name} from {item_url_to_scrape}")
        scraped_detail = get_poe2db_scraped_data(item_url_to_scrape, item_name)
        if scraped_detail and scraped_detail.get("name", "N/A") != "N/A":
            all_scraped_details["items"].append(scraped_detail)
            processed_elements_for_scraping.add(item_name)
            processed_elements_for_scraping.add(scraped_detail["name"])
        else:
            click.echo(f"  Warning: Could not get valid details for item '{item_name}' from poe2db.", fg="yellow")
        time.sleep(0.3)
    click.echo("Additional scraping complete.")

    # 3. Format Data for LLM
    build_data_for_llm = {
        "basics": basics,
        "char_stats": char_stats,
        "skills_xml": skills_xml_data, # Renamed for clarity in LLM prompt
        "items_xml": items_xml_data,   # Renamed for clarity
        "tree": tree_data,
        "scraped_poe2db_details": all_scraped_details # Added scraped data
    }
    try:
        llm_input_string = json.dumps(build_data_for_llm, indent=2)
    except TypeError as e:
        click.echo(click.style(f"Error: Could not serialize build data to JSON: {e}", fg="red"), err=True)
        click.echo("This might be due to non-serializable data types from parsing or scraping.")
        return


    # 4. User Goals (Optional)
    user_goals = click.prompt(click.style("What are your specific goals or context for this build analysis? (e.g., improve bossing, better survivability, specific budget)", fg="green"), default="", show_default=False)

    # 5. Call Gemini Analyzer
    if not GEMINI_API_KEY or GEMINI_API_KEY == "YOUR_API_KEY_PLACEHOLDER_TEXT":
        click.echo(click.style("Error: Gemini API key not configured. Cannot perform build analysis.", fg="red"), err=True)
        click.echo("Please set the API_KEY in llm_interface/gemini_analyzer.py or as an environment variable if configured to do so.")
        return
    
    click.echo("Requesting analysis from Gemini (this may take a while, especially with additional data gathering)...")
    try:
        analysis_result = analyze_build_with_gemini(llm_input_string, user_goals)
    except Exception as e:
        click.echo(click.style(f"Error during Gemini analysis: {e}", fg="red"), err=True)
        return

    # 6. Output Handling
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # Create a slug from the character name or class if available for a more descriptive filename
    # Ensure slugify is available or define it here if it's not imported/accessible
    # For now, assuming slugify is accessible (it's in storage.json_storage, might need to import or redefine)
    # Simplified slugify for this context if not directly available:
    def _slugify_for_filename(text):
        if not text: return "unknown"
        text = str(text).lower().replace(" ", "-")
        return "".join(c for c in text if c.isalnum() or c == '-')

    char_name_slug = _slugify_for_filename(basics.get("className", "build")) if basics else "build"
    analysis_filename = f"PoE2_Build_Analysis_{char_name_slug}_{timestamp}.md"
    
    output_dir = "build_analyses"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    analysis_filepath = os.path.join(output_dir, analysis_filename)

    try:
        with open(analysis_filepath, "w", encoding="utf-8") as f:
            f.write(f"# Path of Exile 2 Build Analysis Report\n\n")
            f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            if basics:
                f.write(f"**Character:** {basics.get('className', 'N/A')} {basics.get('ascendClassName', '')}, Level {basics.get('level', 'N/A')}\n")
            if skills_xml_data and skills_xml_data.get("main_skill_name"):
                 f.write(f"**Main Skill (from PoB):** {skills_xml_data.get('main_skill_name', 'N/A')}\n")
            if user_goals:
                f.write(f"**User Goals/Context:** {user_goals}\n\n")
            f.write("---\n\n")
            f.write(analysis_result if analysis_result else "No analysis content returned.")

        click.echo(click.style(f"\n--- Analysis Complete ---", fg="green", bold=True))
        click.echo(f"Full analysis report saved to: {analysis_filepath}")
        
        # Optional: Print a short summary to console (e.g., first few lines of the LLM response)
        if analysis_result:
            summary_lines = analysis_result.split('\n')[:15] # Show more lines for build analysis
            click.echo("\n--- Analysis Summary (see file for full details) ---")
            click.echo('\n'.join(summary_lines) + ('\n...' if len(analysis_result.split('\n')) > 15 else ''))

    except Exception as e:
        click.echo(click.style(f"Error saving analysis report: {e}", fg="red"), err=True)
        click.echo("\n--- Full Analysis Report (Error saving to file) ---")
        click.echo(analysis_result if analysis_result else "No analysis content.")

# --- Scheduler Command ---
try:
    from scheduler import start_scheduler
    scheduler_available = True
except ImportError:
    scheduler_available = False

if scheduler_available:
    @cli.command("run-scheduler")
    def run_scheduler_command():
        """Starts the background scheduler for periodic tasks (e.g., patch notes scraping)."""
        click.echo("Starting the scheduler...")
        start_scheduler() # This function will block and run the scheduler loop
else:
    @cli.command("run-scheduler")
    def run_scheduler_command():
        """Scheduler component not available."""
        click.echo(click.style("Scheduler component is not available. Please check for 'scheduler.py' and 'schedule' library.", fg="red"), err=True)


if __name__ == '__main__':
    cli()
