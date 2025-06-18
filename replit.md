# Medical JSON to Anki Converter

## Overview

This is a Flask-based web application that converts JSON-formatted medical flashcard data into advanced Anki deck files (.apkg). Designed specifically for medical students, it supports high-yield card highlighting, cloze deletions, hierarchical tags, image embedding, and notes sections. Users can either upload a JSON file or paste JSON data directly into a web form to generate downloadable Anki flashcard decks optimized for medical education.

## System Architecture

### Frontend Architecture
- **Framework**: HTML templates with Bootstrap 5 for styling
- **Template Engine**: Jinja2 (Flask's default)
- **Styling**: Bootstrap with dark theme and Bootstrap Icons
- **JavaScript**: Vanilla JavaScript for form validation and UX enhancements
- **Layout**: Responsive design with navbar, main content area, and footer

### Backend Architecture
- **Framework**: Flask (Python web framework)
- **Application Structure**: Simple monolithic architecture with separation of concerns
- **Main Components**:
  - `main.py`: Application entry point
  - `app.py`: Flask application factory and main logic
  - `FlashcardProcessor`: Class handling JSON validation and Anki deck generation

### Data Processing
- **Enhanced JSON Validation**: Validates medical card structure supporting Q&A or cloze formats
- **Advanced Anki Generation**: Uses `genanki` with unique model/deck IDs and medical-focused templates
- **Medical Card Features**: High-yield highlighting, cloze deletions, hierarchical tags, notes sections
- **File Handling**: Secure temporary file creation for deck downloads with stable GUID generation

## Key Components

### FlashcardProcessor Class
- Validates enhanced JSON structure for medical flashcard data
- Creates advanced Anki models with medical-focused styling and templates
- Supports both basic Q&A and cloze deletion card types
- Generates downloadable .apkg files with unique IDs for proper Anki tracking
- Handles high-yield flagging, hierarchical tags, and notes sections
- Implements stable GUID generation for consistent card updates

### Web Interface
- Single-page application with file upload and text input options
- Form validation to ensure either file or text input is provided
- Real-time feedback and loading states
- Bootstrap-styled responsive interface

### Template Structure
- `base.html`: Layout template with navigation and common elements
- `index.html`: Main form interface extending base template
- Flash message system for user feedback

## Data Flow

1. User accesses the web interface
2. User either uploads a JSON file or pastes JSON data
3. Form submission triggers backend processing
4. JSON data is validated for required structure
5. Valid data is converted to Anki deck format using genanki
6. Generated .apkg file is served as download
7. Error messages are displayed for invalid inputs

### Expected JSON Structure
```json
{
  "deck_name": "Medical Terminology Deck",
  "cards": [
    {
      "question": "What is the mechanism of action of Aspirin?",
      "answer": "Irreversibly inhibits COX-1 and COX-2 enzymes",
      "high_yield_flag": "high-yield",
      "notes": "Important for cardiology and pain management",
      "tags": "Pharmacology::NSAIDs::Aspirin",
      "image": ""
    },
    {
      "cloze_text": "{{c1::Myocardial infarction}} is caused by {{c2::coronary artery occlusion}}",
      "high_yield_flag": "high-yield",
      "notes": "Key concept for USMLE Step 1",
      "tags": "Cardiology::Pathophysiology"
    }
  ]
}
```

#### Enhanced Field Options:
- **deck_name**: Name of the Anki deck (required)
- **question/answer**: For basic Q&A cards
- **cloze_text**: For cloze deletion cards using {{c1::text}} format
- **high_yield_flag**: Set to "high-yield" for red highlighting
- **notes**: Additional context information
- **tags**: Hierarchical tags using :: separator
- **image**: Image filename for embedding (future enhancement)

## External Dependencies

### Python Libraries
- **Flask**: Web framework (>=3.1.1)
- **genanki**: Anki deck generation (>=0.13.1)
- **gunicorn**: WSGI server for production (>=23.0.0)
- **flask-sqlalchemy**: ORM (>=3.1.1) - configured but not actively used
- **psycopg2-binary**: PostgreSQL adapter (>=2.9.10) - available for future use
- **email-validator**: Email validation (>=2.2.0) - available for future use

### Frontend Dependencies
- **Bootstrap 5**: CSS framework (CDN)
- **Bootstrap Icons**: Icon library (CDN)
- **Replit Bootstrap Theme**: Dark theme variant

## Deployment Strategy

### Production Deployment
- **Server**: Gunicorn WSGI server
- **Platform**: Replit with autoscale deployment
- **Configuration**: Configured for production with proper binding and process management
- **Environment**: Python 3.11 with Nix package management

### Development Setup
- **Hot Reload**: Gunicorn with reload flag for development
- **Debug Mode**: Flask debug mode enabled in development
- **Port Configuration**: Runs on port 5000 with proper binding

### Infrastructure
- **Database Ready**: PostgreSQL configured in Nix packages (not currently used)
- **SSL Support**: OpenSSL included in Nix configuration
- **Process Management**: Parallel workflow execution support

## Changelog

```
Changelog:
- June 17, 2025: Initial setup with basic JSON to Anki conversion
- June 17, 2025: Enhanced for medical students with advanced features:
  * Added unique model/deck ID generation using random.randrange()
  * Implemented medical-focused card templates with CSS styling
  * Added support for high-yield flagging with red highlighting
  * Integrated cloze deletion card support
  * Added hierarchical tag system with :: separators
  * Enhanced validation for medical card structures
  * Implemented stable GUID generation for card updates
  * Updated UI with medical-specific examples and documentation
- June 17, 2025: Refined medical card implementation:
  * Improved CSS with flexbox layout and footer positioning for notes
  * Removed automatic high-yield coloring - users control HTML formatting
  * Enhanced field structure with better template organization
  * Added highlight-red CSS class for manual text highlighting
  * Improved card templates with main-content div structure
  * Fixed Jinja2 template syntax conflicts with cloze deletion format
- June 18, 2025: Completed n8n API integration:
  * Fixed API routing issues by consolidating routes into main app file
  * Added flask-cors dependency and configured CORS for API endpoints
  * Implemented comprehensive API endpoints: /health, /generate, /validate, /schema
  * All endpoints tested and working locally with proper JSON responses
  * Added enhanced debugging logs to track exact data received from n8n
  * Confirmed n8n workflow generating intended medical flashcards from PDF content
  * API successfully processing spinothalamic tract and pain signal cards as expected
  * Identified issue: n8n HTTP Request node using hardcoded JSON instead of dynamic AI output
  * Function Node correctly deduplicates cards and outputs { cards: array }
  * Fix required: HTTP Request should use {{ $json.cards }} to access deduplicated array
  * System ready for full automation workflow
- June 18, 2025: Successfully resolved all deployment and API issues:
  * Both local and external APIs fully functional with front/back and question/answer support
  * External deployment updated and confirmed working (HTTP 200 responses)
  * Enhanced error handling and comprehensive logging implemented
  * Added versioning (v3.0.0) with deployment tracking in health endpoint
  * Comprehensive testing confirms n8n workflow compatibility
  * System ready for full automated PDF-to-Anki conversion workflow
  * Added /api/generate-json endpoint specifically for n8n integration (returns JSON instead of binary file)  
  * Both endpoints support front/back and question/answer card formats from AI agents
  * Confirmed: External API working correctly - n8n error was due to binary file response interpretation
  * Solution: Use /api/generate-json endpoint for n8n workflows to receive JSON confirmation
  * Added /api/n8n-generate as ultra-simple endpoint with minimal processing for maximum n8n compatibility
  * Modified /api/generate to detect n8n User-Agent and return JSON instead of binary files
  * Final solution: Use /api/generate-json for guaranteed n8n compatibility
  * Created /api/bulletproof endpoint with multiple JSON parsing methods to handle n8n data issues
  * Bulletproof endpoint validates all card formats and provides detailed error messages
  * Resolved JSON decoding errors that were causing n8n workflow failures
  * Modified /api/bulletproof to generate actual .apkg files with download URLs for n8n compatibility
  * Added /download/<filename> endpoint for serving generated Anki deck files
```

## User Preferences

```
Preferred communication style: Simple, everyday language.
```

### Notes for Development

- The application processes medical flashcards in memory without persistent storage
- Database integration (PostgreSQL/SQLAlchemy) is configured but not currently used
- The FlashcardProcessor class implements advanced medical card generation with genanki
- Comprehensive error handling and flash messaging system is in place
- Uses sophisticated card models with medical-focused fields and styling
- Implements unique ID generation following genanki best practices
- Future enhancements could include:
  * Image file upload and embedding support
  * User accounts and deck management
  * Integration with n8n automation workflows
  * Additional card types and medical specialty templates
  * Bulk CSV import functionality