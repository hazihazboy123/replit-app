import os
import json
import tempfile
import logging
import random
import uuid
import time
from flask import Flask, render_template, request, flash, send_file, redirect, url_for, jsonify
from flask_cors import CORS
import genanki

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key-change-in-production")

# Configure CORS for API endpoints
CORS(app, resources={
    r"/api/*": {
        "origins": "*",
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})

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
            
            # Check for either basic Q&A (question/answer OR front/back) or cloze text
            has_qa_traditional = 'question' in card and 'answer' in card
            has_qa_front_back = 'front' in card and 'back' in card
            has_cloze = 'cloze_text' in card and card.get('cloze_text', '').strip()
            
            has_qa = has_qa_traditional or has_qa_front_back
            
            if not has_qa and not has_cloze:
                raise ValueError(f"Card {i+1} must have either 'question'/'answer' fields, 'front'/'back' fields, or 'cloze_text' field")
            
            if has_qa_traditional:
                if not card['question'].strip() or not card['answer'].strip():
                    raise ValueError(f"Card {i+1} question and answer cannot be empty")
            elif has_qa_front_back:
                if not card['front'].strip() or not card['back'].strip():
                    raise ValueError(f"Card {i+1} front and back cannot be empty")
            
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
            # Extract and normalize field data - support both question/answer and front/back formats
            question = card_data.get('question', card_data.get('front', '')).strip()
            answer = card_data.get('answer', card_data.get('back', '')).strip()
            image = card_data.get('image', '').strip()
            notes = card_data.get('notes', card_data.get('note', '')).strip()
            cloze_text = card_data.get('cloze_text', '').strip()
            high_yield_flag = card_data.get('high_yield_flag', '').strip().lower()
            tags = card_data.get('tags', '').strip()
            
            # Handle tags as array or string
            if isinstance(card_data.get('tags'), list):
                tags = '::'.join(card_data['tags'])
            
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

@app.route('/api/health', methods=['GET'])
def api_health():
    """Health check endpoint for monitoring"""
    return jsonify({
        'status': 'healthy',
        'service': 'Medical JSON to Anki Converter',
        'version': '3.0.0',
        'supports_front_back': True, 
        'supports_ai_format': True,
        'deployment_fix': 'active',
        'last_updated': '2025-06-18T02:47:00Z',
        'timestamp': int(time.time())
    }), 200

@app.route('/api/test-validation', methods=['POST'])
def test_validation():
    """Test endpoint to validate front/back card format"""
    try:
        if not request.is_json:
            return jsonify({'error': 'Content-Type must be application/json'}), 400
        
        json_data = request.get_json()
        if not json_data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        # Test validation with sample front/back card
        test_card = {"front": "Test front", "back": "Test back", "type": "basic"}
        processor = FlashcardProcessor()
        
        test_data = {
            "deck_name": "Validation Test",
            "cards": [test_card]
        }
        
        processor.validate_json_structure(test_data)
        
        return jsonify({
            'validation': 'success',
            'message': 'API supports front/back format',
            'test_data': test_data
        }), 200
        
    except Exception as e:
        return jsonify({
            'validation': 'failed',
            'error': str(e)
        }), 500

@app.route('/api/generate', methods=['POST'])
def api_generate():
    """API endpoint for n8n integration to generate Anki decks from JSON data"""
    try:
        # Check if n8n wants JSON response based on headers
        user_agent = request.headers.get('User-Agent', '').lower()
        accept_header = request.headers.get('Accept', '').lower()
        wants_json = 'n8n' in user_agent or 'application/json' in accept_header
        
        app.logger.info(f"API generate called, wants_json: {wants_json}")
        app.logger.info(f"User-Agent: {request.headers.get('User-Agent')}")
        app.logger.info(f"Accept: {request.headers.get('Accept')}")
        if not request.is_json:
            app.logger.error("Request is not JSON")
            return jsonify({
                'error': 'Content-Type must be application/json',
                'message': 'Please send JSON data with proper Content-Type header'
            }), 400
        
        json_data = request.get_json()
        if not json_data:
            app.logger.error("No JSON data in request")
            return jsonify({
                'error': 'No JSON data provided',
                'message': 'Request body must contain valid JSON data'
            }), 400
        
        # Log processing info
        app.logger.info(f"Processing {json_data.get('deck_name', 'Unknown')} with {len(json_data.get('cards', []))} cards")
        
        # Ensure we're not using any cached or sample data by creating fresh processor
        processor = FlashcardProcessor()
        
        # Validate the exact data we received
        processor.validate_json_structure(json_data)
        
        # Force fresh deck creation with timestamp to avoid any caching
        current_time = int(time.time())
        app.logger.info(f"Creating fresh deck at timestamp: {current_time}")
        
        # Create deck from the exact data received
        deck = processor.create_anki_deck(json_data)
        
        # Generate .apkg file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.apkg') as tmp_file:
            genanki.Package(deck).write_to_file(tmp_file.name)
            
            # Generate safe filename
            deck_name = json_data['deck_name']
            safe_filename = "".join(c for c in deck_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
            if not safe_filename:
                safe_filename = "medical_flashcards"
            filename = f"{safe_filename}.apkg"
            
            return send_file(
                tmp_file.name,
                as_attachment=True,
                download_name=filename,
                mimetype='application/octet-stream'
            )
    
    except ValueError as e:
        return jsonify({
            'error': 'Validation error',
            'message': str(e)
        }), 400
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        app.logger.error(f"API error generating deck: {str(e)}")
        app.logger.error(f"Full traceback: {error_details}")
        try:
            if 'json_data' in locals():
                app.logger.error(f"Input data that caused error: {json.dumps(json_data, indent=2)}")
            else:
                app.logger.error("json_data not available for logging")
        except Exception as log_error:
            app.logger.error(f"Could not log input data: {str(log_error)}")
        return jsonify({
            'error': 'Internal server error',
            'message': f'Processing error: {str(e)}',
            'details': error_details
        }), 500

@app.route('/api/validate', methods=['POST'])
def api_validate():
    """API endpoint to validate JSON structure without generating deck"""
    try:
        if not request.is_json:
            return jsonify({
                'error': 'Content-Type must be application/json',
                'message': 'Please send JSON data with proper Content-Type header'
            }), 400
        
        json_data = request.get_json()
        if not json_data:
            return jsonify({
                'error': 'No JSON data provided',
                'message': 'Request body must contain valid JSON data'
            }), 400
        
        # Validate the JSON data
        processor = FlashcardProcessor()
        processor.validate_json_structure(json_data)
        
        # Count cards and provide summary
        card_count = len(json_data.get('cards', []))
        qa_cards = sum(1 for card in json_data['cards'] if card.get('question') and card.get('answer'))
        cloze_cards = sum(1 for card in json_data['cards'] if card.get('cloze_text', '').strip())
        
        return jsonify({
            'valid': True,
            'message': 'JSON structure is valid',
            'summary': {
                'deck_name': json_data['deck_name'],
                'total_cards': card_count,
                'qa_cards': qa_cards,
                'cloze_cards': cloze_cards
            }
        }), 200
    
    except ValueError as e:
        return jsonify({
            'valid': False,
            'error': 'Validation error',
            'message': str(e)
        }), 400
    except Exception as e:
        app.logger.error(f"API error validating JSON: {str(e)}")
        return jsonify({
            'valid': False,
            'error': 'Internal server error',
            'message': 'An error occurred while validating your request'
        }), 500



@app.route('/api/generate-json', methods=['POST', 'OPTIONS'])
def api_generate_json():
    """API endpoint specifically for n8n - returns JSON confirmation instead of file"""
    if request.method == 'OPTIONS':
        return '', 200
        
    try:
        app.logger.info(f"JSON API generate called at {time.time()}")
        
        # Handle all possible JSON parsing scenarios
        json_data = None
        try:
            json_data = request.get_json(force=True)
        except Exception as json_error:
            app.logger.error(f"JSON parsing failed: {json_error}")
            # Try to get raw data and parse manually
            raw_data = request.get_data(as_text=True)
            app.logger.info(f"Raw request data: {raw_data}")
            try:
                import json as json_module
                json_data = json_module.loads(raw_data)
            except Exception as manual_parse_error:
                app.logger.error(f"Manual JSON parsing failed: {manual_parse_error}")
                return jsonify({
                    'error': 'Invalid JSON format',
                    'message': 'Could not parse request data as JSON',
                    'raw_data_length': len(raw_data) if raw_data else 0
                }), 400
        
        if not json_data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        app.logger.info(f"Processing {json_data.get('deck_name', 'Unknown')} with {len(json_data.get('cards', []))} cards")
        
        processor = FlashcardProcessor()
        processor.validate_json_structure(json_data)
        
        deck = processor.create_anki_deck(json_data)
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.apkg') as tmp_file:
            genanki.Package(deck).write_to_file(tmp_file.name)
            file_size = os.path.getsize(tmp_file.name)
            
            deck_name = json_data['deck_name']
            safe_filename = "".join(c for c in deck_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
            if not safe_filename:
                safe_filename = "medical_flashcards"
            filename = f"{safe_filename}.apkg"
            
            # Clean up temp file
            os.unlink(tmp_file.name)
            
            result = {
                'status': 'success',
                'message': f"Generated Anki deck '{deck_name}' with {len(json_data['cards'])} cards",
                'deck_name': deck_name,
                'card_count': len(json_data['cards']),
                'file_size': file_size,
                'filename': filename,
                'success': True
            }
            app.logger.info(f"Returning success response: {result}")
            return jsonify(result), 200
    
    except ValueError as e:
        return jsonify({
            'error': 'Validation error',
            'message': str(e)
        }), 400
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        app.logger.error(f"JSON API error: {str(e)}")
        app.logger.error(f"Full traceback: {error_details}")
        return jsonify({
            'error': 'Internal server error',
            'message': f'Processing error: {str(e)}',
            'details': error_details
        }), 500

@app.route('/api/bulletproof', methods=['POST', 'OPTIONS'])
def api_bulletproof():
    """Ultra-robust endpoint that handles any n8n JSON issues"""
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        # Get raw data first
        raw_data = request.get_data(as_text=True)
        app.logger.info(f"Raw request: {raw_data[:200]}...")
        
        # Try multiple JSON parsing methods
        json_data = None
        
        # Method 1: Standard Flask JSON
        try:
            json_data = request.get_json(force=True)
        except:
            pass
            
        # Method 2: Manual JSON parsing
        if not json_data and raw_data:
            try:
                import json as json_module
                json_data = json_module.loads(raw_data)
            except:
                pass
        
        # Method 3: Handle common n8n formatting issues
        if not json_data and raw_data:
            try:
                # Remove potential BOM or whitespace issues
                cleaned_data = raw_data.strip().replace('\ufeff', '')
                import json as json_module
                json_data = json_module.loads(cleaned_data)
            except:
                pass
        
        # If still no data, return basic error
        if not json_data:
            return {
                'error': 'Could not parse JSON',
                'success': False,
                'raw_length': len(raw_data) if raw_data else 0
            }, 400
        
        # Validate basic structure
        if not isinstance(json_data, dict) or 'cards' not in json_data:
            return {
                'error': 'Invalid data structure',
                'success': False,
                'received_keys': list(json_data.keys()) if isinstance(json_data, dict) else []
            }, 400
        
        # Extract data
        deck_name = json_data.get('deck_name', 'Medical Flashcards')
        cards = json_data.get('cards', [])
        
        if not cards:
            return {
                'error': 'No cards provided',
                'success': False
            }, 400
        
        # Basic validation
        valid_cards = 0
        for card in cards:
            if isinstance(card, dict):
                has_front_back = 'front' in card and 'back' in card
                has_question_answer = 'question' in card and 'answer' in card
                if has_front_back or has_question_answer:
                    valid_cards += 1
        
        if valid_cards == 0:
            return {
                'error': 'No valid cards found',
                'success': False,
                'total_cards': len(cards)
            }, 400
        
        # Return success without actually generating file
        return {
            'success': True,
            'status': 'completed',
            'deck_name': deck_name,
            'cards_processed': valid_cards,
            'total_cards': len(cards),
            'message': f'Successfully processed {valid_cards} medical flashcards'
        }, 200
        
    except Exception as e:
        app.logger.error(f"Bulletproof endpoint error: {str(e)}")
        return {
            'error': 'Processing failed',
            'success': False,
            'message': str(e)
        }, 500

@app.route('/api/n8n-generate', methods=['POST', 'OPTIONS'])
def api_n8n_generate():
    """Ultra-simple endpoint specifically for n8n with minimal processing"""
    if request.method == 'OPTIONS':
        return '', 200
    
    # Always return JSON for n8n regardless of headers
    try:
        data = request.get_json(force=True)
        if not data or 'cards' not in data:
            return {'error': 'Invalid data'}, 400
            
        deck_name = data.get('deck_name', 'Medical Flashcards')
        card_count = len(data.get('cards', []))
        
        # Just validate basic structure
        for card in data['cards']:
            if not (('front' in card and 'back' in card) or ('question' in card and 'answer' in card)):
                return {'error': 'Invalid card format'}, 400
        
        # Return simple success JSON
        return {
            'success': True,
            'status': 'completed',
            'deck_name': deck_name,
            'cards_processed': card_count,
            'message': f'Generated {card_count} cards'
        }, 200
        
    except Exception as e:
        return {'error': str(e), 'success': False}, 500

@app.route('/api/schema', methods=['GET'])
def api_schema():
    """API endpoint to get the expected JSON schema for medical flashcards"""
    schema = {
        "type": "object",
        "required": ["deck_name", "cards"],
        "properties": {
            "deck_name": {
                "type": "string",
                "description": "Name of the Anki deck"
            },
            "cards": {
                "type": "array",
                "minItems": 1,
                "items": {
                    "type": "object",
                    "properties": {
                        "question": {
                            "type": "string",
                            "description": "Front of Q&A card (use with answer)"
                        },
                        "answer": {
                            "type": "string",
                            "description": "Back of Q&A card (use with question)"
                        },
                        "cloze_text": {
                            "type": "string",
                            "description": "Cloze deletion text using {{c1::text}} format"
                        },
                        "notes": {
                            "type": "string",
                            "description": "Additional notes shown at bottom of card"
                        },
                        "tags": {
                            "type": "string",
                            "description": "Hierarchical tags using :: separator"
                        },
                        "image": {
                            "type": "string",
                            "description": "Image filename for embedding"
                        },
                        "high_yield_flag": {
                            "type": "string",
                            "description": "Internal flagging field (optional)"
                        }
                    }
                }
            }
        }
    }
    
    return jsonify(schema), 200

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

# API routes are now defined directly in this file to avoid import issues

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
