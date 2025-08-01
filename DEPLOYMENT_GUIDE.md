# Medical Flashcard System - Deployment Guide

## Version: 10.5.1
## GitHub Repository: hazihazboy123/replit-app

### Key Files to Copy to Your Repository:

**Core Application:**
- `app.py` - Main Flask application with enhanced medical features
- `main.py` - Entry point for the application
- `pyproject.toml` - Python dependencies and project configuration

**Documentation:**
- `replit.md` - Complete project documentation and changelog
- `DEPLOYMENT_GUIDE.md` - This deployment guide

**Directories:**
- `downloads/` - Persistent download directory (create empty)
- `static/` - Static assets (if exists)
- `templates/` - HTML templates (if exists)

### Dependencies (from pyproject.toml):
```
flask
flask-cors
flask-sqlalchemy
genanki
gunicorn
pillow
psycopg2-binary
requests
beautifulsoup4
email-validator
```

### Current Features (Version 10.5.1):
- ✅ Permanent download links (never expire)
- ✅ Pure HTML preservation without font size modifications
- ✅ Enhanced image handling with 70% sizing
- ✅ Cloze card support
- ✅ Clinical vignettes and mnemonics support
- ✅ Robust error handling and validation
- ✅ Notes font size preservation (per user request)

### Deployment Steps:
1. Clone your repository: `git clone https://github.com/hazihazboy123/replit-app.git`
2. Copy all the key files listed above
3. Create empty `downloads/` directory
4. Install dependencies: `pip install -r requirements.txt` or use pyproject.toml
5. Run: `gunicorn --bind 0.0.0.0:5000 --reuse-port --reload main:app`

### API Endpoint:
- POST `/api/enhanced-medical` - Main endpoint for JSON to Anki conversion
- GET `/api/health` - Health check endpoint
- GET `/download/<filename>` - Permanent download endpoint

### Recent Updates:
- July 20, 2025: Removed font size modifications from notes section
- July 14, 2025: Implemented permanent download links system
- Complete elimination of automatic file cleanup for persistent storage