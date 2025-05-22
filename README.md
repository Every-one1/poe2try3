# Path of Exile 2 AI Build Analyzer

## Project Purpose

This project analyzes Path of Exile 2 builds from Path of Building (PoB) XML files. It enriches the data from the XML with information scraped from various external sources like poe2db.tw, poewiki.net, Reddit, official PoE forums, and build guide websites. Finally, it uses the Gemini AI model to provide a comprehensive analysis of the build, offering insights and suggestions for improvement.

## Key Features

*   **PoB XML Parsing:** Extracts detailed information from your Path of Building XML export.
*   **Data Enrichment:** Scrapes additional data for skills, items, and community sentiment from:
    *   `poe2db.tw` (for skill/item stats and tables)
    *   `poewiki.net` (for skill/item mechanics, synergies, patch history)
    *   `Reddit` (for community discussions)
    *   `Path of Exile Official Forums` (for community discussions and patch notes)
    *   Build guide websites (e.g., `poe-vault.com`)
*   **AI-Powered Analysis:** Leverages Google's Gemini model to:
    *   Synthesize all collected data.
    *   Provide an in-depth build review covering offensive capabilities, defensive layers, gear, skill gems, and passive tree choices.
    *   Offer actionable improvement suggestions tailored to PoE2 mechanics.
*   **Caching:** Implements caching for scraped data to speed up subsequent analyses and reduce load on external websites.

## Setup Instructions

1.  **Clone the Repository:**
    ```bash
    git clone <repository_url> # Replace <repository_url> with the actual URL
    cd <repository_directory>
    ```

2.  **Install Dependencies:**
    This project requires Python 3.x. You'll need to install the following libraries. A `requirements.txt` file is provided for convenience.
    ```bash
    pip install -r requirements.txt
    ```
    The key libraries are:
    *   `lxml`: For parsing XML files.
    *   `requests`: For making HTTP requests to scrape websites.
    *   `beautifulsoup4`: For parsing HTML content.
    *   `google-generativeai`: For interacting with the Gemini API.

3.  **Set up Gemini API Key:**
    *   **IMPORTANT:** This project requires a Google Gemini API key.
    *   You need to set an environment variable named `GEMINI_API_KEY` with your actual Gemini API key.
    *   For example, in Linux/macOS, you can set it temporarily by running `export GEMINI_API_KEY="YOUR_ACTUAL_API_KEY"` in your terminal session, or add this line to your shell's profile file (e.g., `.bashrc`, `.zshrc`) for a permanent setting. For Windows, you can use `set GEMINI_API_KEY="YOUR_ACTUAL_API_KEY"` in Command Prompt or set it via the Environment Variables system settings.

## Usage Instructions

1.  **Export Your Build from Path of Building:**
    *   In Path of Building (ensure it's a version that supports PoE2 if applicable, or a standard PoB fork), export your build to an XML file.
    *   Save this XML file in the project's root directory, or note its path.

2.  **Provide the XML File:**
    *   Currently, the script `main.py` is hardcoded to use `sample_build.xml`. You will need to replace this file with your own XML export, or modify the `build_xml_file` variable in `main.py` to point to your file.
    *   *(A future improvement will allow specifying the XML file path via a command-line argument.)*

3.  **Run the Analyzer:**
    ```bash
    python main.py
    ```

4.  **Review the Output:**
    *   The script will print progress to the console as it fetches and analyzes data.
    *   Once complete, a detailed analysis report will be saved as a Markdown file (e.g., `PoE2_Build_Analysis_YYYYMMDD_HHMMSS.md`) in the project directory.

## Project Structure

*   `main.py`: The main script to run the build analysis.
*   `xml_parser.py`: Handles loading and parsing data from the PoB XML file.
*   `poe2db_scraper.py`: Scrapes detailed skill and item information from `poe2db.tw`.
*   `poe2_wiki_scraper.py`: Scrapes information from `poewiki.net` (skills, items, patch notes).
*   `poe2_community_scraper.py`: Scrapes discussions and guides from Reddit, official forums, and build guide sites.
*   `gemini_analyzer.py`: Contains the logic for interacting with the Gemini AI, generating prompts, and producing the final analysis.
*   `sample_build.xml`: An example PoB XML file.
*   `scraper_cache/`: Directory where cached data from web scraping is stored to speed up subsequent runs.

## Future Improvements

*   Allow XML file path to be specified as a command-line argument.
*   Enhanced error handling and reporting for scraping and API interactions.
*   Support for more data sources or community build sites.
*   Interactive analysis mode (e.g., asking follow-up questions).
*   More output format options (e.g., JSON, HTML).
*   Refinement of Gemini prompts for even more targeted analysis.
