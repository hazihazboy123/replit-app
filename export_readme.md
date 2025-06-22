# Medical Flashcard Converter - Complete Python Export

## Overview
This is a complete export of the SynapticRecall medical flashcard converter system that transforms JSON data into professionally styled Anki deck files (.apkg) with AnKingMaster note type version 8 compatibility.

## System Components

### Core Application Files
- `main.py` - Application entry point for Flask server
- `app.py` - Main Flask application with all API endpoints and flashcard processing logic
- `anking_engine.py` - Complete AnKing styling engine with CSS, JavaScript, and model definitions

### Configuration Files
- `pyproject.toml` - Python package dependencies and project metadata
- `replit.md` - Complete system documentation and user preferences

### Web Interface
- `templates/` - HTML templates for the web interface
- `static/` - CSS and JavaScript files for frontend
- `media/` - Media files and assets

## Key Features

### Intelligent Deck Naming
- Automatic "synapticrecall_[topic]" naming based on content analysis
- Topic detection for spinothalamic tract, cardiovascular, respiratory, pharmacology, etc.
- Example: Spinothalamic content → "synapticrecall_spinothalmictract"

### AnKing Compatibility
- Complete AnKingMaster note type version 8 styling
- Arial Greek font with proper medical exam formatting
- Center-aligned text and professional card appearance
- Full CSS and JavaScript integration

### n8n Automation Ready
- Multiple API endpoints for external integration
- Handles various JSON input formats from AI agents
- [CLOZE::text] to {{c1::text}} conversion for automation workflows
- Comprehensive error handling and logging

### Medical Card Features
- Basic Q&A and cloze deletion card types
- High-yield flagging and hierarchical tags
- Vignette and mnemonic sections
- Image embedding support (configured)
- Notes and extra information fields

## Installation & Setup

1. Install dependencies:
   ```bash
   pip install -r setup_requirements.txt
   # OR using uv:
   uv add flask genanki gunicorn flask-cors flask-sqlalchemy psycopg2-binary
   ```

2. Run the application:
   ```bash
   python main.py
   # OR for production:
   gunicorn --bind 0.0.0.0:5000 --reuse-port --reload main:app
   ```

3. Access the web interface at `http://localhost:5000`

## API Endpoints

### Primary Endpoints
- `POST /api/simple` - Main endpoint for n8n integration (recommended)
- `POST /api/generate-json` - Returns JSON confirmation instead of binary file
- `GET /health` - Health check and system status

### Input Format
```json
{
  "cards": [
    {
      "type": "basic",
      "front": "Question text",
      "back": "Answer text",
      "tags": ["Medical::Topic"]
    },
    {
      "type": "cloze",
      "front": "The [CLOZE::spinothalamic tract] carries [CLOZE::pain signals]",
      "extra": "Additional information",
      "vignette": "Clinical scenario",
      "mnemonic": "Memory aid",
      "tags": ["Neuroanatomy::Pathways"]
    }
  ]
}
```

### Output
- Generates .apkg files compatible with Anki
- Automatic SynapticRecall naming based on content
- Professional medical card styling
- Complete AnKing feature set

## Development Notes

- Uses Flask framework with SQLAlchemy (configured but not required)
- PostgreSQL support available for future enhancements
- Comprehensive logging for debugging
- Tag sanitization (spaces → underscores for genanki compatibility)
- Stable GUID generation for consistent card updates

## Deployment

Configured for Replit deployment with:
- Gunicorn WSGI server
- Proper port binding (0.0.0.0:5000)
- Auto-reload in development
- Production-ready configuration

## Version History

Latest version includes:
- Fixed "0 notes found" issue with proper card generation
- Intelligent SynapticRecall deck naming system
- Complete AnKing styling compatibility
- Full n8n automation support
- Professional medical card templates

For complete changelog and technical details, see `replit.md`.