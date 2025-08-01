# SynapticRecall Medical Flashcard Converter

A specialized web application that converts JSON-formatted flashcard data into professional Anki deck files (.apkg) for medical students and healthcare professionals.

## Features

- **JSON to Anki Conversion**: Convert JSON data to .apkg format compatible with Anki
- **Medical-Specific Formatting**: Support for clinical vignettes, mnemonics, and medical terminology
- **AnKing-Compatible Styling**: Uses AnKing medical deck styling (version 8)
- **Smart Card Types**: Supports both basic Q&A and cloze deletion cards
- **Image Support**: Downloads and embeds images from URLs
- **API Integration**: RESTful endpoints for automation with tools like n8n
- **Permanent Downloads**: Generated files never expire

## Tech Stack

- **Backend**: Python Flask with Genanki library
- **Frontend**: Bootstrap 5 with vanilla JavaScript
- **Package Manager**: UV (modern Python package manager)

## API Endpoints

- `POST /api/enhanced-medical` - Main conversion endpoint
- `POST /api/simple` - Legacy compatibility endpoint
- `GET /api/health` - System health check
- `GET /download/<filename>` - Permanent download links

## Installation

1. Clone the repository
2. Install dependencies: `uv pip install -r pyproject.toml`
3. Run the application: `python main.py`

## Usage

1. Upload a JSON file or paste JSON data directly
2. The system will convert it to an Anki-compatible .apkg file
3. Download the generated deck file
4. Import into Anki

## Version

Current version: 10.5.1

For deployment instructions, see [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)