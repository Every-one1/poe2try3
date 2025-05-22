# Path of Exile 2 Build Analyzer

This tool analyzes Path of Exile 2 builds using data scraped from various sources and potentially uses an LLM for analysis.

## Features

- Data scraping from multiple sources (patch notes, community forums, wikis, poe2db).
- Parsing of Path of Building (PoB) XML files.
- Patch processing.
- LLM-based analysis (Gemini Analyzer).
- CLI for interaction.
- Scheduling capabilities.

## Setup and Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/your-username/poe2-build-analyzer.git
   cd poe2-build-analyzer
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

To run the main script:
```bash
python main.py
```

To use the CLI:
```bash
python cli/main.py [commands]
```

## Contributing

Contributions are welcome! Please feel free to submit a pull request or open an issue.

## License

MIT License
