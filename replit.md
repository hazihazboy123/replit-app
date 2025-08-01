# Medical JSON to Anki Converter

## Overview
This Flask-based web application converts JSON-formatted medical flashcard data into advanced Anki deck files (.apkg). It's designed for medical students, supporting features like high-yield card highlighting, cloze deletions, hierarchical tags, image embedding, and notes sections. Users can upload JSON files or paste JSON data to generate downloadable Anki decks optimized for medical education. The project aims to streamline the creation of high-quality, specialized medical flashcards, enhancing study efficiency and knowledge retention for medical professionals and students.

## User Preferences
Preferred communication style: Simple, everyday language.
Font preference: Arial Greek font (reverted from Courier).
Clinical vignette formatting: Line spacing of at least 1.25 for improved readability.
Background styling: Keep blue backgrounds for vignettes and golden backgrounds for mnemonics.
Text highlighting: Red (#d32f2f) for ALL content (front/back cards, vignette text, and correct answers).
Pink highlighting: Red (#d32f2f) for mnemonics to match consistent highlighting scheme.
Answer formatting: A, B, C, D, E choices on separate lines with highlighting only on correct answers.
Vignette answer colors: Changed from dark blue to readable blue (#1976d2) matching vignette text color for better visibility.
Interactive features: Added click-to-reveal functionality for correct answers and explanations in clinical vignettes to enhance active learning.
Deck generation: Each API call creates a new unique deck with timestamp and unique ID to prevent card merging.
Sample data: Updated with comprehensive medical vignettes including detailed patient presentations, mnemonics with highlight-pink styling, and multiple choice questions with interactive click-to-reveal functionality.

## System Architecture

### Frontend
- **Framework**: HTML templates with Bootstrap 5 and Jinja2.
- **Styling**: Bootstrap with dark theme, Bootstrap Icons, and custom medical-focused CSS.
- **JavaScript**: Vanilla JavaScript for form validation and UX.
- **Layout**: Responsive design with a single-page interface for JSON input (file upload or text paste).

### Backend
- **Framework**: Flask (Python).
- **Application Structure**: Monolithic with `main.py` and `app.py` as entry points, utilizing a `FlashcardProcessor` class for core logic.
- **Data Processing**:
    - Validates enhanced JSON structure for medical cards (Q&A or cloze).
    - Generates Anki decks using `genanki` with unique model/deck IDs and medical-focused templates.
    - Supports high-yield highlighting, cloze deletions, hierarchical tags, and notes sections.
    - Handles stable GUID generation for consistent card updates and secure temporary file creation for downloads.

### Core Components & Features
- **FlashcardProcessor**: Validates JSON, creates Anki models with medical styling, supports Q&A and cloze, generates .apkg files, handles high-yield flags, hierarchical tags, notes, and stable GUIDs.
- **Web Interface**: Single-page application with form validation, real-time feedback, and responsive Bootstrap styling.
- **Template Structure**: `base.html` for layout, `index.html` for main interface, and a flash message system.
- **Data Flow**: User input (JSON) is processed, validated, converted to Anki format, and served as a downloadable .apkg file.
- **Medical Card Features**:
    - **High-yield flagging**: "high-yield" flag for red highlighting.
    - **Notes**: Additional context.
    - **Tags**: Hierarchical using `::` separator.
    - **Image Support**: Embeds local files or downloads/embeds images from URLs.
    - **Card Types**: Supports both basic Q&A and cloze deletion (`{{c1::text}}`) formats.
    - **Styling**: AnKing-inspired styling with Arial Greek font, responsive design, professional medical card appearance, and full night mode support. Consistent model IDs (1607392319/2059400110) for proper Anki tracking.
    - **Vignettes/Mnemonics**: Distinct visual styling with light blue backgrounds and borders for vignettes, and gold/yellow backgrounds for mnemonics.

## External Dependencies

### Python Libraries
- **Flask**: Web framework.
- **genanki**: Anki deck generation.
- **gunicorn**: WSGI server for production.

### Frontend Dependencies
- **Bootstrap 5**: CSS framework (CDN).
- **Bootstrap Icons**: Icon library (CDN).
- **Replit Bootstrap Theme**: Dark theme variant.