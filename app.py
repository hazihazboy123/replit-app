import os
import json
import tempfile
import logging
import random
import uuid
from flask import Flask, render_template, request, flash, send_file, redirect, url_for
import genanki

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key-change-in-production")

# Configure CORS for n8n integration
from cors_config import configure_cors
configure_cors(app)

class FlashcardProcessor:
    """Handles processing of JSON flashcard data and Anki deck generation for medical students"""
    
    def __init__(self):
        # Generate unique IDs for model and deck (recommended by genanki for proper Anki tracking)
        self.model_id = random.randrange(1 << 30, 1 << 31)
        self.deck_id = random.randrange(1 << 30, 1 << 31)
        
        # Create advanced model for medical flashcards
        self.model = self._create_medical_model()
    
    def _create_medical_model(self):
        """Create advanced Anki model for medical students with styling and multiple card types"""
        
        model_css = """
        .card {
            font-family: Arial, sans-serif;
            font-size: 20px;
            text-align: left;
            color: black;
            background-color: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
            line-height: 1.5;
            max-width: 650px;
            margin: auto;
            display: flex;
            flex-direction: column;
            min-height: 100vh;
        }
        .card.nightMode {
            color: white;
            background-color: #333;
            box-shadow: 0 4px 8px rgba(0,0,0,0.3);
        }
        .highlight-red {
            color: red;
            font-weight: bold;
        }
        .card.nightMode .highlight-red {
            color: #FF6666;
        }
        .notes-section {
            font-size: 0.9em;
            color: #666;
            margin-top: auto;
            padding-top: 15px;
            border-top: 1px solid #eee;
            text-align: left;
        }
        .card.nightMode .notes-section {
            color: #999;
            border-top-color: #444;
        }
        img {
            max-width: 100%;
            height: auto;
            display: block;
            margin: 10px auto;
            border-radius: 4px;
        }
        .cloze {
            font-weight: bold;
            color: blue;
        }
        .card.nightMode .cloze {
            color: lightblue;
        }
        hr {
            border: none;
            border-top: 1px dashed #ccc;
            margin: 20px 0;
        }
        .main-content {
            flex-grow: 1;
        }
        """
        
        fields = [
            {'name': 'Question'},
            {'name': 'Answer'},
            {'name': 'Image'},
            {'name': 'Notes'},
            {'name': 'ClozeText'},
            {'name': 'HighYieldFlag'},
            {'name': 'Tags'}
        ]
        
        templates = [
            {
                'name': 'Basic Card',
                'qfmt': '''
                <div class="main-content">
                    {{Question}}
                    {{#Image}}<img src="{{Image}}">{{/Image}}
                </div>
                {{#Notes}}
                <div class="notes-section">
                    <strong>Notes:</strong> {{Notes}}
                </div>
                {{/Notes}}
                ''',
                'afmt': '''
                <div class="main-content">
                    {{Question}}
                    {{#Image}}<img src="{{Image}}">{{/Image}}
                    <hr id="answer">
                    {{Answer}}
                </div>
                {{#Notes}}
                <div class="notes-section">
                    <strong>Notes:</strong> {{Notes}}
                </div>
                {{/Notes}}
                '''
            },
            {
                'name': 'Cloze Card',
                'qfmt': '''
                <div class="main-content">
                    {{cloze:ClozeText}}
                    {{#Image}}<img src="{{Image}}">{{/Image}}
                </div>
                {{#Notes}}
                <div class="notes-section">
                    <strong>Notes:</strong> {{Notes}}
                </div>
                {{/Notes}}
                ''',
                'afmt': '''
                <div class="main-content">
                    {{cloze:ClozeText}}
                    {{#Image}}<img src="{{Image}}">{{/Image}}
                </div>
                {{#Notes}}
                <div class="notes-section">
                    <strong>Notes:</strong> {{Notes}}
                </div>
                {{/Notes}}
                '''
            }
        ]
        
        return genanki.Model(
            self.model_id,
            'Medical High-Yield Cards',
            fields=fields,
            templates=templates,
            css=model_css
        )
    
    def validate_json_structure(self, data):
        """Validate the JSON structure for medical flashcards"""
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
            
            # Check for either basic Q&A or cloze text
            has_qa = 'question' in card and 'answer' in card
            has_cloze = 'cloze_text' in card and card.get('cloze_text', '').strip()
            
            if not has_qa and not has_cloze:
                raise ValueError(f"Card {i+1} must have either 'question'/'answer' fields or 'cloze_text' field")
            
            if has_qa:
                if not card['question'].strip() or not card['answer'].strip():
                    raise ValueError(f"Card {i+1} question and answer cannot be empty")
            
            # Validate high_yield_flag if present (for internal flagging, not automatic coloring)
            high_yield = card.get('high_yield_flag', '').strip().lower()
            if high_yield and high_yield not in ['', 'high-yield']:
                raise ValueError(f"Card {i+1} high_yield_flag must be 'high-yield' or empty")
    
    def create_anki_deck(self, data):
        """Create an Anki deck from validated JSON data with advanced medical card features"""
        deck_name = data['deck_name']
        cards_data = data['cards']
        
        # Create deck with unique ID
        deck = genanki.Deck(
            self.deck_id,
            deck_name
        )
        
        # Add cards to deck
        for card_data in cards_data:
            # Extract and normalize field data
            question = card_data.get('question', '').strip()
            answer = card_data.get('answer', '').strip()
            image = card_data.get('image', '').strip()
            notes = card_data.get('notes', '').strip()
            cloze_text = card_data.get('cloze_text', '').strip()
            high_yield_flag = card_data.get('high_yield_flag', '').strip().lower()
            tags = card_data.get('tags', '').strip()
            
            # Create note with fields in correct order matching the model
            fields_data = [
                question,           # Question
                answer,            # Answer
                image,             # Image
                notes,             # Notes
                cloze_text,        # ClozeText
                high_yield_flag,   # HighYieldFlag (for internal use, not automatic styling)
                tags               # Tags
            ]
            
            # Generate stable GUID for note updates
            guid_components = [question, answer, cloze_text, image]
            note_guid = genanki.guid_for(*[comp for comp in guid_components if comp])
            
            note = genanki.Note(
                model=self.model,
                fields=fields_data,
                guid=note_guid
            )
            
            # Add hierarchical tags if provided
            if tags:
                note.tags = [tag.strip() for tag in tags.split('::') if tag.strip()]
            
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
            if not file.filename or not str(file.filename).endswith('.json'):
                flash('Please upload a JSON file (.json extension)', 'error')
                return redirect(url_for('index'))
            
            try:
                # Read file content and parse JSON
                file_content = file.read().decode('utf-8')
                json_data = json.loads(file_content)
            except json.JSONDecodeError as e:
                flash(f'Invalid JSON file: {str(e)}', 'error')
                return redirect(url_for('index'))
            except UnicodeDecodeError:
                flash('File encoding error. Please ensure your JSON file is UTF-8 encoded.', 'error')
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

# Register API blueprint
from api_routes import api
app.register_blueprint(api)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
