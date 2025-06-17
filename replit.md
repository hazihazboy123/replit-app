# JSON to Anki Converter

## Overview

This is a Flask-based web application that converts JSON-formatted flashcard data into Anki deck files (.apkg). Users can either upload a JSON file or paste JSON data directly into a web form to generate downloadable Anki flashcard decks.

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
- **JSON Validation**: Custom validation for required fields (deck_name, cards)
- **Anki Generation**: Uses the `genanki` library to create .apkg files
- **File Handling**: Temporary file creation for deck downloads

## Key Components

### FlashcardProcessor Class
- Validates JSON structure for flashcard data
- Creates Anki models and templates
- Generates downloadable .apkg files
- Handles error cases and validation failures

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
  "deck_name": "Deck Name",
  "cards": [
    {
      "question": "Front of card",
      "answer": "Back of card"
    }
  ]
}
```

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
- June 17, 2025. Initial setup
```

## User Preferences

```
Preferred communication style: Simple, everyday language.
```

### Notes for Development

- The application currently processes flashcards in memory without persistent storage
- Database integration (PostgreSQL/SQLAlchemy) is configured but not implemented
- The FlashcardProcessor class is partially implemented and needs completion
- Error handling and flash messaging system is in place
- The application uses a simple card model with Question/Answer fields
- Future enhancements could include user accounts, deck management, and more card types