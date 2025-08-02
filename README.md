# SynapticRecall Medical Flashcard Converter

A bulletproof Flask API that converts n8n-generated JSON medical flashcards into Anki .apkg files with 100% reliability using `json_repair`.

## Features

- **100% Reliable Parsing**: Uses `json_repair` to handle ANY LLM-generated JSON, even with syntax errors
- **n8n Integration**: Specifically designed for n8n automation workflows
- **Medical-Specific Formatting**: Support for clinical vignettes, mnemonics, and medical terminology
- **AnKing-Compatible Styling**: Uses AnKing medical deck styling (version 8)
- **Smart Card Types**: Supports both basic Q&A and cloze deletion cards
- **Image Support**: Downloads and embeds images from URLs
- **Supabase Integration**: Permanent cloud storage for generated decks
- **Smart Deck Naming**: Automatically names decks based on content tags

## Tech Stack

- **Backend**: Python Flask with Genanki library
- **JSON Parsing**: json_repair (bulletproof LLM JSON parser)
- **Frontend**: Bootstrap 5 with vanilla JavaScript
- **Package Manager**: UV (modern Python package manager)
- **Cloud Storage**: Supabase

## API Endpoints

- `POST /api/flexible-convert` - Main n8n integration endpoint (uses json_repair)
- `POST /api/enhanced-medical` - Standard conversion endpoint
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

## n8n Integration

### HTTP Request Node Setup

1. **Method**: POST
2. **URL**: `http://your-domain.com/api/flexible-convert`
3. **Body Type**: Raw
4. **Content Type**: text/plain
5. **Body**: `{{ $json.output }}`

That's it! The API handles all JSON parsing issues automatically.

## Version

Current version: 11.0.0 (json_repair integration)

For deployment instructions, see [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)