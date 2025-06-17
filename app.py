import os
import json
import tempfile
import logging
from flask import Flask, render_template, request, flash, send_file, redirect, url_for
import genanki

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key-change-in-production")

class FlashcardProcessor:
    """Handles processing of JSON flashcard data and Anki deck generation"""
    
    def __init__(self):
        # Create a model for the flashcards
        self.model = genanki.Model(
            1607392319,
            'Simple Model',
            fields=[
                {'name': 'Question'},
                {'name': 'Answer'},
            ],
            templates=[
                {
                    'name': 'Card 1',
                    'qfmt': '{{Question}}',
                    'afmt': '{{FrontSide}}<hr id="answer">{{Answer}}',
                },
            ])
    
    def validate_json_structure(self, data):
        """Validate the JSON structure for flashcards"""
        if not isinstance(data, dict):
            raise ValueError("JSON must be an object")
        
        if 'deck_name' not in data:
            raise ValueError("Missing required field 'deck_name'")
        
        if 'cards' not in data:
            raise ValueError("Missing required field 'cards'")
        
        if not isinstance(data['cards'], list):
            raise ValueError("'cards' must be an array")
        
        if len(data['cards']) == 0:
            raise ValueError("At least one card is required")
        
        for i, card in enumerate(data['cards']):
            if not isinstance(card, dict):
                raise ValueError(f"Card {i+1} must be an object")
            
            if 'question' not in card or 'answer' not in card:
                raise ValueError(f"Card {i+1} must have 'question' and 'answer' fields")
            
            if not card['question'].strip() or not card['answer'].strip():
                raise ValueError(f"Card {i+1} question and answer cannot be empty")
    
    def create_anki_deck(self, data):
        """Create an Anki deck from validated JSON data"""
        deck_name = data['deck_name']
        cards_data = data['cards']
        
        # Create deck
        deck = genanki.Deck(
            2059400110,
            deck_name
        )
        
        # Add cards to deck
        for card_data in cards_data:
            note = genanki.Note(
                model=self.model,
                fields=[card_data['question'], card_data['answer']]
            )
            deck.add_note(note)
        
        return deck

@app.route('/')
def index():
    """Main page with the form for JSON input"""
    return render_template('index.html')

@app.route('/process', methods=['POST'])
def process_flashcards():
    """Process the submitted JSON data and generate Anki deck"""
    try:
        json_data = None
        
        # Check if data was submitted via textarea or file upload
        if 'json_file' in request.files and request.files['json_file'].filename:
            # File upload
            file = request.files['json_file']
            if not file.filename.endswith('.json'):
                flash('Please upload a JSON file (.json extension)', 'error')
                return redirect(url_for('index'))
            
            try:
                json_data = json.load(file)
            except json.JSONDecodeError as e:
                flash(f'Invalid JSON file: {str(e)}', 'error')
                return redirect(url_for('index'))
        
        elif 'json_text' in request.form and request.form['json_text'].strip():
            # Text input
            try:
                json_data = json.loads(request.form['json_text'])
            except json.JSONDecodeError as e:
                flash(f'Invalid JSON format: {str(e)}', 'error')
                return redirect(url_for('index'))
        
        else:
            flash('Please provide JSON data either by uploading a file or entering text', 'error')
            return redirect(url_for('index'))
        
        # Process the JSON data
        processor = FlashcardProcessor()
        processor.validate_json_structure(json_data)
        
        # Create Anki deck
        deck = processor.create_anki_deck(json_data)
        
        # Generate .apkg file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.apkg') as tmp_file:
            genanki.Package(deck).write_to_file(tmp_file.name)
            
            # Generate safe filename
            deck_name = json_data['deck_name']
            safe_filename = "".join(c for c in deck_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
            if not safe_filename:
                safe_filename = "flashcards"
            filename = f"{safe_filename}.apkg"
            
            return send_file(
                tmp_file.name,
                as_attachment=True,
                download_name=filename,
                mimetype='application/octet-stream'
            )
    
    except ValueError as e:
        flash(f'Validation error: {str(e)}', 'error')
        return redirect(url_for('index'))
    except Exception as e:
        app.logger.error(f"Error processing flashcards: {str(e)}")
        flash('An error occurred while processing your flashcards. Please try again.', 'error')
        return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
