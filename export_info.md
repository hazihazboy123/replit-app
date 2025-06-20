# Medical Flashcard Converter - Complete AnKing Integration

## Export Package Contents

This export contains the complete medical flashcard converter system with full AnKing integration:

### Core Components
- `app.py` - Main Flask application with comprehensive API endpoints
- `main.py` - Application entry point
- `anking_engine.py` - Complete AnKing engine with CSS, JavaScript, and automation features
- `pyproject.toml` - Python dependencies configuration
- `replit.md` - Complete project documentation and user preferences

### Features Included

**Complete AnKing Integration:**
- Full AnKingMaster note type version 8 CSS styling
- Advanced JavaScript with cloze one-by-one reveal, timers, and interactive features
- Image Style Editor add-on compatibility configurations
- Professional tag styling with colorful kbd elements
- Mobile responsiveness and button layouts

**Automation Compatibility:**
- [CLOZE::text] to {{c1::text}} placeholder conversion for n8n workflows
- Multiple JSON input format support (arrays, objects, nested structures)
- Robust error handling and fallback systems
- API endpoints: /api/simple, /api/generate, /api/generate-json, /health

**Medical Card Features:**
- High-yield highlighting with red, bold, uppercase formatting
- Clinical vignette sections with professional styling
- Mnemonic sections with distinct visual appearance
- Extra information fields with proper organization
- Hierarchical tag system with :: separators

### Deployment Instructions

1. Extract the tar.gz file to your target deployment environment
2. Ensure Python 3.11+ is available
3. Install dependencies: `pip install -r requirements.txt` (generated from pyproject.toml)
4. Configure environment variables if needed
5. Run with: `gunicorn --bind 0.0.0.0:5000 --reuse-port --reload main:app`

### API Usage

**For n8n Integration:**
```bash
curl -X POST http://your-domain/api/simple \
  -H "Content-Type: application/json" \
  -d '[{"cards":[{"type":"cloze","front":"Your [CLOZE::content] here"}]}]'
```

**Response includes:**
- Download URL for .apkg file
- File size and card count
- Success/error status

### System Capabilities

- Processes complex medical content with proper AnKing styling
- Generates professional Anki decks with interactive features
- Supports both basic Q&A and cloze deletion card types
- Handles clinical vignettes, mnemonics, and medical imagery
- Full compatibility with AnKing add-ons and styling standards

### Version Information
- AnKing Engine: Complete integration (June 2025)
- CSS: AnKingMaster note type version 8 with add-on compatibility
- JavaScript: Full feature set including persistence, timers, and shortcuts
- Automation: Full n8n workflow compatibility with robust error handling

## Generated: June 20, 2025
## Export Size: Complete system with all dependencies and assets