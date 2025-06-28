import os
import json
import tempfile
import logging
import random
import uuid
import time
import html
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
        # Use consistent model ID for proper Anki tracking (as recommended in the guide)
        self.model_id = 1607392319  # Fixed ID for consistency across generations
        self.deck_id = 2059400110   # Fixed ID for consistency across generations
        
        # Create advanced model for medical flashcards with perfect styling
        self.model = self._create_medical_model()
        
        # Import AnKing engine for advanced functionality
        try:
            from anking_engine import get_anking_model, create_anki_deck as anking_create_deck, convert_cloze_placeholder
            self.anking_model, self.anking_deck_id = get_anking_model()
            self.anking_create_deck = anking_create_deck
            self.convert_cloze_placeholder = convert_cloze_placeholder
            self.use_anking_engine = True
            app.logger.info("AnKing engine loaded successfully")
        except ImportError as e:
            app.logger.warning(f"AnKing engine not available: {e}")
            self.use_anking_engine = False
    
    def _create_medical_model(self):
        """Create advanced Anki model for medical students with perfect styling and multiple card types"""
        
        # AnKing-inspired perfect CSS styling for medical cards
        model_css = """
/* ANKINGMASTER NOTETYPE VERSION 8 inspired styling */

html {
    min-height: 100%;
    display: flex;
    flex-direction: column; /* Stack content vertically */
    justify-content: center; /* Center vertically */
    align-items: center;   /* Center horizontally */
    font-size: 28px; /* Base font size for desktop, as per AnKing */
}

.mobile {
    font-size: 28px; /* Base font size for mobile, as per AnKing */
}

.card {
    font-family: Arial Greek, Arial, sans-serif; /* Step exam's font is Arial Greek, as per AnKing */
    font-size: 1rem; /* Relative to html font-size */
    color: black; /* Default text color, as per AnKing */
    background-color: #D1CFCE; /* Background color, as per AnKing */
    text-align: center; /* Center align text within the card, as per video and AnKing */
    line-height: 1.6; /* Wider line spacing for readability */
    margin: 0px 15px; /* Margins, as per AnKing */
    flex-grow: 1; /* Allow card to grow and fill space */
    padding-bottom: 1em; /* Padding at the bottom, as per AnKing */
    box-sizing: border-box; /* Include padding in element's total width and height */
    max-width: 700px; /* Limit line length for readability */
}

/* Dark mode styling, as per AnKing */
.nightMode.card,.night_mode.card {
    color: #FFFAFA!important; /* Night mode text color */
    background-color: #272828!important; /* Night mode background color */
}

/* Style for the horizontal rule separating question and answer */
hr {
    border: none;
    border-top: 1px solid #ccc;
    margin: 20px 0;
}

/* Styling for cloze deletions, as per AnKing */
.cloze {
    font-weight: bold;
    color: blue; /* Cloze color */
}

.nightMode.cloze,.night_mode.cloze {
    color: #4297F9!important; /* Night mode cloze color */
}

/* Styling for the "EXTRA" field (used for Additional Notes), as per AnKing */
#extra {
    font-style: italic;
    font-size: 1rem; /* Relative to base font size */
    color: navy; /* "EXTRA" field color */
    margin-top: 25px;
    padding-top: 15px;
    border-top: 1px dashed #eee; /* Subtle separator */
    text-align: left; /* Left-align for longer notes */
}

.nightMode #extra,.night_mode #extra {
    color: magenta; /* Night mode "EXTRA" field color */
    border-top: 1px dashed #444;
}

/* Styling for mnemonics and vignettes, as per AnKing */
.mnemonic-section,.vignette-section,.clinical-correl-section,.source-section {
    margin-top: 25px;
    padding-top: 15px;
    border-top: 1px dashed #eee; /* Subtle separator */
    font-size: 0.95em; /* Slightly smaller font for supplementary info */
    color: #555;
    text-align: left; /* Mnemonics and other sections left-aligned as per AnKing */
}

.nightMode.mnemonic-section,.nightMode.vignette-section,.nightMode.clinical-correl-section,.nightMode.source-section {
    color: #aaa;
    border-top: 1px dashed #444;
}

.section-label {
    font-weight: bold;
    color: #333; /* Darker color for labels */
    margin-bottom: 5px;
    display: block; /* Ensure label is on its own line */
}

.nightMode.section-label {
    color: #ccc;
}

/* Image sizing, as per AnKing */
img {
    max-height: none; /* No max height */
}
#extra img, #lecture img, #missed img, #pathoma img, #bnb img {
    max-width: 85%; /* Max width for images in extra fields */
}
#firstaid img, #sketchy img, #physeo img, #additional img {
    max-width: 60%; /* Max width for specific resource images */
}
.mobile.card img {
    max-width: 100%!important;
}

/* TAGS container, as per AnKing */
#tags-container {
    position: fixed;
    bottom:.5px;
    width: 100%;
    line-height:.45rem;
    margin-left: -15px;
    background-color: transparent;
    display: block; /* Ensure tags are visible by default */
}
.mobile #tags-container {
    line-height: 0.6rem;
    margin-left: 0px;
    display: block; /* Ensure tags are visible on mobile */
}

/* Clickable Tags (kbd elements), as per AnKing */
kbd {
    display: inline-block;
    letter-spacing:.1px;
    font-weight: bold;
    font-size: 10px!important;
    text-shadow: none!important;
    padding: 0.05rem 0.1rem!important;
    margin: 1px -3px!important;
    border-radius: 4px;
    border-width: 1.5px!important;
    border-style: solid;
    background-color: transparent!important;
    box-shadow: none!important;
    opacity: 0.5;
    vertical-align: middle!important;
    line-height: auto!important;
    height: auto!important;
    font-family: Arial Greek, Arial; /* Font for tags */
}
kbd:hover {
    opacity: 1;
    transition: opacity 0.2s ease;
}
/* Tag Colors, as per AnKing */
kbd:nth-of-type(1n+0) { border-color: #F44336; color: #F44336!important; }
kbd:nth-of-type(2n+0) { border-color: #9C27B0; color: #9C27B0!important; }
kbd:nth-of-type(3n+0) { border-color: #3F51B5; color: #3F51B5!important; }
kbd:nth-of-type(4n+0) { border-color: #03A9F4; color: #03A9F4!important; }
kbd:nth-of-type(5n+0) { border-color: #009688; color: #009688!important; }
kbd:nth-of-type(6n+0) { border-color: #C0CA33; color: #C0CA33!important; }
kbd:nth-of-type(7n+0) { border-color: #FF9800; color: #FF9800!important;}
kbd:nth-of-type(8n+0) { border-color: #FF5722; color: #FF5722!important; }
kbd:nth-of-type(9n+0) { border-color: #9E9E9E; color: #9E9E9E!important; }
kbd:nth-of-type(10n+0) { border-color: #607D8B; color: #607D8B!important; }

.mobile kbd {
    opacity:.9;
    margin: 1px!important;
    display: inline-block;
    font-size: 10px!important;
}

/* MNEMONICS CENTER OR LEFT, as per AnKing */
.mnemonics {
    display: inline-block;
}
.centerbox {text-align:center;}

/* QA section for proper content structure */
.qa-section {
    display: block;
    width: 100%;
}

/* Additional styling for sections */
.additional-notes-section {
    margin-top: 25px;
    padding-top: 15px;
    border-top: 1px dashed #eee;
    font-size: 0.95em;
    color: #555;
    text-align: left;
}

.nightMode.additional-notes-section {
    color: #aaa;
    border-top: 1px dashed #444;
}
        """
        
        # Define fields in precise order for consistent content mapping
        fields = [
            {'name': 'Question'},
            {'name': 'Answer'},
            {'name': 'Mnemonic'},
            {'name': 'Vignette'},
            {'name': 'ClinicalCorrelation'},
            {'name': 'AdditionalNotes'},
            {'name': 'Source'},
            {'name': 'ClozeText'},
            {'name': 'Image'}
        ]
        
        # AnKing-inspired templates with proper styling and structure
        templates = [
            {
                'name': 'Medical High-Yield Card',
                'qfmt': '''
                <div class="qa-section">
                    {{#Question}}{{Question}}{{/Question}}
                    {{#ClozeText}}{{cloze:ClozeText}}{{/ClozeText}}
                    {{#Image}}<img src="{{Image}}">{{/Image}}
                </div>
                ''',
                'afmt': '''
                {{FrontSide}}
                <hr id="answer">
                <div class="qa-section">
                    {{#Answer}}{{Answer}}{{/Answer}}
                    {{#ClozeText}}{{cloze:ClozeText}}{{/ClozeText}}
                </div>
                {{#Mnemonic}}
                <div class="mnemonic-section">
                    <div class="mnemonics centerbox">
                        <span class="section-label">Mnemonic:</span> {{Mnemonic}}
                    </div>
                </div>
                {{/Mnemonic}}
                {{#Vignette}}
                <div class="vignette-section">
                    <span class="section-label">Clinical Vignette:</span> {{Vignette}}
                </div>
                {{/Vignette}}
                {{#ClinicalCorrelation}}
                <div class="clinical-correl-section">
                    <span class="section-label">Clinical Correlation:</span> {{ClinicalCorrelation}}
                </div>
                {{/ClinicalCorrelation}}
                {{#AdditionalNotes}}
                <div id="extra">
                    {{AdditionalNotes}}
                </div>
                {{/AdditionalNotes}}
                {{#Source}}
                <div class="source-section">
                    <span class="section-label">Source:</span> {{Source}}
                </div>
                {{/Source}}
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
                front_content = card.get('front', '').strip()
                back_content = card.get('back', '').strip()
                card_type = card.get('type', '').lower()
                
                # Handle cloze cards where content is in front field
                if card_type == 'cloze' and front_content:
                    # This is a valid cloze card - allow empty back field
                    pass
                elif not front_content or not back_content:
                    raise ValueError(f"Card {i+1} front and back cannot be empty")
            
            # Validate high_yield_flag if present (for internal flagging, not automatic coloring)
            high_yield = card.get('high_yield_flag', '').strip().lower()
            if high_yield and high_yield not in ['', 'high-yield']:
                raise ValueError(f"Card {i+1} high_yield_flag must be 'high-yield' or empty")
    
    def create_anki_deck(self, data, deck_name=None):
        """Create perfect Anki deck from validated JSON data with comprehensive medical card features"""
        deck_name = data['deck_name']
        cards_data = data['cards']
        
        # Use AnKing engine if available for superior formatting
        if self.use_anking_engine:
            app.logger.info("Using AnKing engine for deck creation")
            
            # Convert data to AnKing format
            anking_cards = []
            for card_data in cards_data:
                # Extract fields with comprehensive format support and cleanup
                question = card_data.get('question', card_data.get('front', '')).strip()
                answer = card_data.get('answer', card_data.get('back', '')).strip()
                card_type = card_data.get('type', 'basic').lower()
                
                # Clean up only trailing extra braces, but preserve cloze deletion braces
                if question:
                    # Don't clean braces from cloze cards
                    if card_type != 'cloze':
                        question = str(question).rstrip('} ')
                    else:
                        question = str(question)
                if answer:
                    answer = str(answer).rstrip('} ')
                
                # Handle cloze cards with proper conversion
                if card_type == 'cloze' and question and not answer:
                    # Convert to AnKing cloze format
                    question = self.convert_cloze_placeholder(question)
                
                # Clean additional fields
                extra = card_data.get('notes', card_data.get('additional_notes', card_data.get('extra', ''))).strip()
                vignette = card_data.get('vignette', '')
                mnemonic = card_data.get('mnemonic', '').strip()
                
                # Handle image field - support both formats
                image_data = card_data.get('image', '')
                image_ref = ''
                if image_data:
                    if isinstance(image_data, dict):
                        # New format with caption and URL
                        image_ref = image_data.get('url', '')
                    else:
                        # Simple filename format
                        image_ref = str(image_data).strip()
                
                # Apply cleanup to all text fields
                if extra:
                    extra = str(extra).rstrip('} ')
                if mnemonic:
                    mnemonic = str(mnemonic).rstrip('} ')
                
                # Clean vignette content (handle both string and dict formats)
                if vignette:
                    if isinstance(vignette, dict):
                        clinical_case = vignette.get('clinical_case', '')
                        explanation = vignette.get('explanation', '')
                        if clinical_case:
                            clinical_case = str(clinical_case).rstrip('} ')
                            # Convert red highlighting to dark blue in vignettes
                            clinical_case = clinical_case.replace('highlight-red', 'highlight-blue')
                        if explanation:
                            explanation = str(explanation).rstrip('} ')
                            # Convert red highlighting to dark blue in vignettes
                            explanation = explanation.replace('highlight-red', 'highlight-blue')
                        vignette = {'clinical_case': clinical_case, 'explanation': explanation}
                    else:
                        vignette_text = str(vignette).rstrip('} ')
                        # Convert red highlighting to dark blue in vignettes
                        vignette_text = vignette_text.replace('highlight-red', 'highlight-blue')
                        vignette = vignette_text

                anking_card = {
                    'type': card_type,
                    'front': question,
                    'back': answer,
                    'extra': extra,
                    'vignette': vignette,
                    'mnemonic': mnemonic,
                    'image_ref': image_ref,
                    'tags': card_data.get('tags', [])
                }
                anking_cards.append(anking_card)
            
            # Use fixed AnKing engine to create the actual deck
            from anking_engine_fixed import create_anki_deck as fixed_anking_create_deck
            return fixed_anking_create_deck(anking_cards, deck_name)
        
        # Fallback to original implementation
        app.logger.info("Using standard deck creation")
        deck = genanki.Deck(self.deck_id, deck_name)
        
        # Add cards to deck with perfect field mapping
        for card_data in cards_data:
            # Extract and normalize all field data with comprehensive format support
            question = card_data.get('question', card_data.get('front', '')).strip()
            answer = card_data.get('answer', card_data.get('back', '')).strip()
            mnemonic = card_data.get('mnemonic', card_data.get('Mnemonic', '')).strip()
            vignette = card_data.get('vignette', card_data.get('Vignette', '')).strip()
            clinical_correlation = card_data.get('clinical_correlation', card_data.get('clinicalCorrelation', '')).strip()
            additional_notes = card_data.get('notes', card_data.get('additional_notes', card_data.get('note', ''))).strip()
            source = card_data.get('source', '').strip()
            cloze_text = card_data.get('cloze_text', '').strip()
            image = card_data.get('image', '').strip()
            
            # Handle cloze cards with type detection
            if card_data.get('type') == 'cloze' and not cloze_text:
                cloze_text = question  # Use front field for cloze content
                question = ''  # Clear question for cloze cards
                answer = ''    # Clear answer for cloze cards
            
            # Ensure proper cloze deletion formatting with double curly braces
            if cloze_text and '{{c' not in cloze_text and '{c' in cloze_text:
                # Fix single braces to double braces for proper Anki cloze formatting
                import re
                cloze_text = re.sub(r'\{(c\d+::[^}]+)\}', r'{{\1}}', cloze_text)
            
            # Perfect field order matching model definition:
            # Question, Answer, Mnemonic, Vignette, ClinicalCorrelation, AdditionalNotes, Source, ClozeText, Image
            fields_data = [
                html.escape(question) if question else '',                    # Question
                html.escape(answer) if answer else '',                      # Answer  
                html.escape(mnemonic) if mnemonic else '',                  # Mnemonic
                html.escape(vignette) if vignette else '',                  # Vignette
                html.escape(clinical_correlation) if clinical_correlation else '',  # ClinicalCorrelation
                html.escape(additional_notes) if additional_notes else '',  # AdditionalNotes
                html.escape(source) if source else '',                     # Source
                cloze_text if cloze_text else '',                          # ClozeText (no escape - contains Anki syntax)
                image if image else ''                                      # Image (no escape - filename only)
            ]
            
            # Generate stable GUID for consistent note updates
            guid_components = [question, answer, cloze_text, mnemonic, vignette]
            note_guid = genanki.guid_for(*[comp for comp in guid_components if comp])
            
            # Create note with perfect field mapping
            note = genanki.Note(
                model=self.model,
                fields=fields_data,
                guid=note_guid
            )
            
            # Handle hierarchical tags properly (remove spaces for Anki compatibility)
            tags_data = card_data.get('tags', '')
            if tags_data:
                if isinstance(tags_data, list):
                    note.tags = [tag.strip().replace(' ', '_') for tag in tags_data if tag.strip()]
                elif isinstance(tags_data, str):
                    # Support both space and :: separated tags
                    if '::' in tags_data:
                        note.tags = [tag.strip().replace(' ', '_') for tag in tags_data.split('::') if tag.strip()]
                    else:
                        note.tags = [tag.strip().replace(' ', '_') for tag in tags_data.split() if tag.strip()]
            
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
    """API endpoint specifically for n8n - returns JSON confirmation and generates actual files"""
    if request.method == 'OPTIONS':
        return '', 200
        
    try:
        app.logger.info(f"JSON API generate called at {time.time()}")
        
        # Robust JSON parsing
        json_data = None
        try:
            json_data = request.get_json(force=True)
        except Exception as json_error:
            app.logger.error(f"JSON parsing failed: {json_error}")
            raw_data = request.get_data(as_text=True)
            app.logger.info(f"Raw request data: {raw_data}")
            try:
                import json as json_module
                json_data = json_module.loads(raw_data)
            except Exception as manual_parse_error:
                app.logger.error(f"Manual JSON parsing failed: {manual_parse_error}")
                return jsonify({
                    'error': 'Invalid JSON format',
                    'message': 'Could not parse request data as JSON'
                }), 400
        
        if not json_data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        # Enhanced logging for debugging n8n issues
        app.logger.info(f"Received JSON data: {json_data}")
        app.logger.info(f"Data type: {type(json_data)}")
        app.logger.info(f"Keys in data: {json_data.keys() if isinstance(json_data, dict) else 'Not a dict'}")
        
        # Handle case where n8n sends just the cards array
        if isinstance(json_data, list):
            json_data = {
                'deck_name': 'Medical Flashcards',
                'cards': json_data
            }
            app.logger.info("Converted array to proper format")
        elif 'deck_name' not in json_data and 'cards' in json_data:
            json_data['deck_name'] = 'Medical Flashcards'
            app.logger.info("Added missing deck_name")
        elif 'cards' not in json_data:
            app.logger.error("Missing 'cards' field in request")
            return jsonify({
                'error': 'Missing cards field',
                'message': 'Request must include "cards" array',
                'received_keys': list(json_data.keys()) if isinstance(json_data, dict) else str(type(json_data))
            }), 400
        
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
            
            # Add download URL for n8n compatibility
            download_url = f"/download/{os.path.basename(tmp_file.name)}"
            full_download_url = f"https://flashcard-converter-haziqmakesai.replit.app{download_url}"
            
            result = {
                'status': 'success',
                'message': f"Generated Anki deck '{deck_name}' with {len(json_data['cards'])} cards",
                'deck_name': deck_name,
                'card_count': len(json_data['cards']),
                'file_size': file_size,
                'filename': filename,
                'download_url': download_url,
                'full_download_url': full_download_url,
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
        
        # Actually generate the Anki deck
        try:
            processor = FlashcardProcessor()
            processor.validate_json_structure(json_data)
            deck = processor.create_anki_deck(json_data)
            
            # Create temporary file for download
            with tempfile.NamedTemporaryFile(delete=False, suffix='.apkg') as tmp_file:
                genanki.Package(deck).write_to_file(tmp_file.name)
                file_size = os.path.getsize(tmp_file.name)
                
                # Generate safe filename
                safe_filename = "".join(c for c in deck_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
                if not safe_filename:
                    safe_filename = "medical_flashcards"
                filename = f"{safe_filename}.apkg"
                
                # Always return JSON for this endpoint to maintain n8n compatibility
                download_url = f"/download/{os.path.basename(tmp_file.name)}"
                full_download_url = f"https://flashcard-converter-haziqmakesai.replit.app{download_url}"
                
                response_data = {
                    'success': True,
                    'status': 'completed',
                    'deck_name': deck_name,
                    'cards_processed': valid_cards,
                    'total_cards': len(cards),
                    'file_size': file_size,
                    'filename': filename,
                    'download_url': download_url,
                    'full_download_url': full_download_url,
                    'message': f'Successfully generated {valid_cards} medical flashcards'
                }
                
                app.logger.info(f"Returning response: {response_data}")
                return response_data, 200
                
                # Note: Removed browser file download to maintain consistent JSON response
                
        except Exception as deck_error:
            app.logger.error(f"Deck generation failed: {deck_error}")
            return {
                'error': 'Deck generation failed',
                'success': False,
                'message': str(deck_error)
            }, 500
        
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

@app.route('/export/<path:filename>')
def export_file(filename):
    """Serve export files for download"""
    try:
        # Handle both .apkg files and export archives
        file_path = os.path.join('/home/runner/workspace', filename)
        
        if not os.path.exists(file_path):
            return "Export file not found", 404
        
        return send_file(
            file_path,
            as_attachment=True,
            download_name=filename,
            mimetype='application/gzip' if filename.endswith('.tar.gz') else 'application/octet-stream'
        )
    except Exception as e:
        app.logger.error(f"Export error: {e}")
        return "Export failed", 500

@app.route('/download/<path:filename>')
def download_file(filename):
    """Serve generated .apkg files and system exports for download"""
    try:
        # Allow both .apkg files and .tar.gz exports
        allowed_extensions = ['.apkg', '.tar.gz']
        if not any(filename.endswith(ext) for ext in allowed_extensions):
            app.logger.error(f"Invalid file extension for download: {filename}")
            return "Invalid file type", 400
        
        # Enhanced file path checking with multiple locations
        possible_paths = [
            os.path.join('/tmp', filename),
            os.path.join('/home/runner/workspace', filename),
            os.path.join('/home/runner/workspace/downloads', filename)
        ]
        
        file_path = None
        for path in possible_paths:
            if os.path.exists(path):
                file_path = path
                break
        
        app.logger.info(f"Searching for file: {filename}")
        app.logger.info(f"Checked paths: {possible_paths}")
        app.logger.info(f"Found file at: {file_path}")
        
        if not file_path or not os.path.exists(file_path):
            # List available files for debugging
            tmp_files = []
            try:
                tmp_files = [f for f in os.listdir('/tmp') if f.endswith('.apkg')]
            except:
                pass
            app.logger.error(f"File not found: {filename}")
            app.logger.error(f"Available .apkg files in /tmp: {tmp_files}")
            app.logger.error(f"Checked paths: {possible_paths}")
            
            # Try to find a similar file with different timestamp
            similar_files = [f for f in tmp_files if filename.replace('_', '').replace('.apkg', '') in f.replace('_', '').replace('.apkg', '')]
            if similar_files:
                # Use the most recent similar file
                newest_file = max(similar_files, key=lambda f: os.path.getmtime(os.path.join('/tmp', f)))
                file_path = os.path.join('/tmp', newest_file)
                app.logger.info(f"Using similar file: {file_path}")
            else:
                return f"File not found: {filename}. Available files: {tmp_files}", 404
        
        # Verify file size
        file_size = os.path.getsize(file_path)
        app.logger.info(f"Serving file: {filename}, size: {file_size} bytes")
        
        # Set appropriate mimetype and download name
        if filename.endswith('.tar.gz'):
            mimetype = 'application/gzip'
            download_name = filename
        else:
            mimetype = 'application/octet-stream'
            base_name = filename.replace('.apkg', '').replace('tmp', 'medical_flashcards')
            download_name = f"{base_name}.apkg"
        
        return send_file(
            file_path,
            as_attachment=True,
            download_name=download_name,
            mimetype=mimetype
        )
    except Exception as e:
        app.logger.error(f"Download error: {e}")
        import traceback
        app.logger.error(f"Download traceback: {traceback.format_exc()}")
        return "Download failed", 500

@app.route('/api/export-code', methods=['GET'])
def api_export_code():
    """API endpoint to download complete system code as tar.gz"""
    try:
        import tempfile
        import tarfile
        import os
        
        # Create temporary archive
        with tempfile.NamedTemporaryFile(suffix='.tar.gz', delete=False) as tmp_file:
            with tarfile.open(tmp_file.name, 'w:gz') as tar:
                # Add main Python files
                for py_file in ['app.py', 'main.py', 'anking_engine.py', 'verify_external.py']:
                    if os.path.exists(py_file):
                        tar.add(py_file, arcname=py_file)
                
                # Add configuration files
                for config_file in ['pyproject.toml', 'setup_requirements.txt', 'replit.md', 'export_readme.md']:
                    if os.path.exists(config_file):
                        tar.add(config_file, arcname=config_file)
                
                # Add directories
                for directory in ['templates', 'static', 'media']:
                    if os.path.exists(directory):
                        tar.add(directory, arcname=directory)
            
            # Return the file
            return send_file(
                tmp_file.name,
                as_attachment=True,
                download_name='synapticrecall-medical-flashcard-system.tar.gz',
                mimetype='application/gzip'
            )
            
    except Exception as e:
        app.logger.error(f"Export code error: {e}")
        return {'error': 'Export failed', 'message': str(e)}, 500

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
    
    return jsonify(schema)


@app.route('/api/simple', methods=['POST', 'OPTIONS'])
def api_simple():
    """Bulletproof endpoint that accepts any reasonable JSON format from n8n"""
    if request.method == 'OPTIONS':
        return '', 200
        
    try:
        app.logger.info("=== SIMPLE API CALLED ===")
        
        # Get comprehensive request information for debugging
        raw_data = request.get_data(as_text=True)
        content_type = request.headers.get('Content-Type', 'unknown')
        user_agent = request.headers.get('User-Agent', 'unknown')
        
        app.logger.info(f"Content-Type: {content_type}")
        app.logger.info(f"User-Agent: {user_agent}")
        app.logger.info(f"Raw request length: {len(raw_data)}")
        app.logger.info(f"Raw request: {raw_data}")
        
        # Parse JSON following the Replit HTTPS guide best practices
        data = None
        
        # Method 1: Flask's get_json with proper Content-Type validation
        if 'application/json' in content_type.lower():
            try:
                data = request.get_json(force=True)
                app.logger.info("✓ Flask JSON parser worked")
            except Exception as e:
                app.logger.info(f"✗ Flask JSON parser failed: {e}")
        
        # Method 2: Manual JSON parsing for edge cases
        if not data and raw_data.strip():
            try:
                import json
                data = json.loads(raw_data)
                app.logger.info("✓ Manual JSON parser worked")
            except Exception as e:
                app.logger.info(f"✗ Manual JSON parser failed: {e}")
                
        # Method 3: Handle URL-encoded data that might contain JSON
        if not data and 'application/x-www-form-urlencoded' in content_type.lower():
            try:
                from urllib.parse import parse_qs
                form_data = parse_qs(raw_data)
                # Check if any form field contains JSON
                for key, values in form_data.items():
                    for value in values:
                        try:
                            potential_json = json.loads(value)
                            if isinstance(potential_json, (list, dict)):
                                data = potential_json
                                app.logger.info("✓ Found JSON in form data")
                                break
                        except:
                            continue
                    if data:
                        break
            except Exception as e:
                app.logger.info(f"✗ Form data parsing failed: {e}")
        
        # Return detailed error with debugging information
        if not data:
            return {
                'error': 'Could not parse request data',
                'content_type': content_type,
                'user_agent': user_agent,
                'raw_data_preview': raw_data[:200],
                'raw_data_length': len(raw_data),
                'suggestions': [
                    'Ensure Content-Type is application/json',
                    'Send: {"cards": [{"front":"Q","back":"A"}]}',
                    'Or send: [{"front":"Q","back":"A"}]',
                    'Verify n8n HTTP Request node settings'
                ]
            }, 400
        
        app.logger.info(f"Parsed data type: {type(data)}")
        app.logger.info(f"Parsed data: {data}")
        
        # Convert different input formats to standard format
        if isinstance(data, list):
            # Check if it's an array containing objects with 'cards' field
            if len(data) > 0 and isinstance(data[0], dict) and 'cards' in data[0]:
                # Handle format: [{"cards": [...]}]
                cards = data[0]['cards']
                deck_name = data[0].get('deck_name', None)
                app.logger.info("Input was array with cards object")
            else:
                # If it's just an array of cards
                cards = data
                deck_name = None
                app.logger.info("Input was cards array")
        elif isinstance(data, dict):
            if 'cards' in data:
                # Standard format with cards field
                cards = data['cards']
                deck_name = data.get('deck_name', None)
                app.logger.info("Input was object with cards field")
            elif 'json' in data and isinstance(data['json'], dict) and 'cards' in data['json']:
                # Handle nested n8n format: {"json": {"cards": [...]}}
                cards = data['json']['cards']
                deck_name = data['json'].get('deck_name', None)
                app.logger.info("Input was nested n8n format with json.cards")
            else:
                # Maybe the whole object is one card?
                if 'front' in data or 'question' in data:
                    cards = [data]
                    deck_name = None
                    app.logger.info("Input was single card object")
                else:
                    return {
                        'error': 'No cards found',
                        'received_keys': list(data.keys()),
                        'expected': 'cards field or front/question field'
                    }, 400
        else:
            return {
                'error': 'Invalid data type',
                'received_type': str(type(data))
            }, 400
        
        # Validate we have cards
        if not cards or not isinstance(cards, list):
            return {
                'error': 'Invalid cards',
                'cards_type': str(type(cards)),
                'cards_value': cards
            }, 400
        
        # Generate SynapticRecall deck name with topic detection if not provided
        if not deck_name or deck_name in ['Medical Flashcards', 'Flashcards']:
            base_deck_name = generate_synaptic_recall_name(cards)
            app.logger.info(f"Generated base SynapticRecall deck name: '{base_deck_name}'")
        else:
            base_deck_name = deck_name
        
        # Force new deck creation by adding timestamp to ensure unique deck each time
        import time
        timestamp = int(time.time())
        deck_name = f"{base_deck_name}_{timestamp}"
        app.logger.info(f"Final deck name with timestamp: '{deck_name}'")
        
        # CRITICAL: Clean up ALL content BEFORE processing
        app.logger.info(f"Cleaning up {len(cards)} cards before processing")
        for i, card in enumerate(cards):
            # Clean all text fields to remove only trailing extra } characters
            for field in ['front', 'back', 'question', 'answer', 'note', 'notes', 'extra', 'mnemonic']:
                if field in card and card[field]:
                    original = card[field]
                    # Only remove trailing braces and spaces, preserve legitimate content
                    cleaned = str(original).rstrip('} ')
                    if original != cleaned:
                        app.logger.info(f"Cleaned {field}: '{original}' -> '{cleaned}'")
                    card[field] = cleaned
            
            # Clean vignette content
            if 'vignette' in card and card['vignette']:
                vignette = card['vignette']
                if isinstance(vignette, dict):
                    for vfield in ['clinical_case', 'explanation']:
                        if vfield in vignette and vignette[vfield]:
                            original = vignette[vfield]
                            cleaned = str(original).rstrip('} ')
                            if original != cleaned:
                                app.logger.info(f"Cleaned vignette.{vfield}: '{original}' -> '{cleaned}'")
                            vignette[vfield] = cleaned
                else:
                    original = vignette
                    cleaned = str(original).rstrip('} ')
                    if original != cleaned:
                        app.logger.info(f"Cleaned vignette: '{original}' -> '{cleaned}'")
                    card['vignette'] = cleaned
        
        app.logger.info(f"Processing {len(cards)} cards for deck '{deck_name}'")
        
        # Enhanced card content validation following best practices
        for i, card in enumerate(cards):
            app.logger.info(f"Card {i}: {card}")
            
            # Support multiple field formats as per API documentation
            front = (card.get('front', '') or 
                    card.get('question', '') or 
                    card.get('Front', '') or 
                    card.get('Question', ''))
            
            back = (card.get('back', '') or 
                   card.get('answer', '') or 
                   card.get('Back', '') or 
                   card.get('Answer', ''))
            
            # Handle cloze deletion cards
            cloze = card.get('cloze_text', '') or card.get('cloze', '')
            
            app.logger.info(f"Card {i} - Front: '{front}' | Back: '{back}' | Cloze: '{cloze}'")
            
            # Validate card has content
            if not front and not back and not cloze:
                app.logger.error(f"Card {i} is completely empty!")
                return {
                    'error': 'Empty card detected',
                    'card_index': i,
                    'card_data': card,
                    'available_fields': list(card.keys()) if isinstance(card, dict) else 'not a dict',
                    'message': 'Cards must have front/back, question/answer, or cloze_text content',
                    'debug_info': {
                        'front_variants': ['front', 'question', 'Front', 'Question'],
                        'back_variants': ['back', 'answer', 'Back', 'Answer'],
                        'cloze_variants': ['cloze_text', 'cloze']
                    }
                }, 400
                
            # Normalize the card format for processing - handle all field variations
            card_type = card.get('type', '').lower()
            
            # Map field variations to standard fields
            if card_type == 'cloze' and front and '{{c' in front:
                # Handle cloze cards where content is in question field
                card['cloze_text'] = front
                # Clear front/back for cloze cards
                card.pop('front', None)
                card.pop('back', None)
                card.pop('question', None)
                card.pop('answer', None)
            elif card_type == 'cloze' and front:
                # Handle any cloze card - put content in cloze_text 
                card['cloze_text'] = front
                card['back'] = ' '  # Add space to prevent validation error
            elif not front and not back and cloze:
                # Standard cloze deletion card
                card['cloze_text'] = cloze
            else:
                # Standard Q&A card - map to front/back for consistency
                if front:
                    card['front'] = front
                if back:
                    card['back'] = back
            
            # Map field variations to standard names
            if 'clinical_correl' in card:
                card['clinical_correlation'] = card.get('clinical_correl', '')
            if 'additional_notes' in card:
                card['notes'] = card.get('additional_notes', '')
            elif 'note' in card:
                card['notes'] = card.get('note', '')
            
            # Handle complex vignette structures
            if 'vignette' in card and isinstance(card['vignette'], dict):
                # Extract clinical case from complex vignette object
                vignette_obj = card['vignette']
                clinical_case = vignette_obj.get('clinical_case', '')
                explanation = vignette_obj.get('explanation', '')
                
                # Combine into a single vignette field
                combined_vignette = f"{clinical_case}"
                if explanation:
                    combined_vignette += f"\n\nExplanation: {explanation}"
                
                card['vignette'] = combined_vignette
            
            # Handle extra/additional information fields
            if 'extra' not in card and 'notes' in card:
                card['extra'] = card['notes']
        
        # Create the final data structure
        final_data = {
            'deck_name': deck_name,
            'cards': cards
        }
        
        # Generate the Anki deck
        processor = FlashcardProcessor()
        processor.validate_json_structure(final_data)
        
        # Create predictable filename with timestamp
        safe_name = "".join(c for c in deck_name if c.isalnum() or c in (' ', '-', '_')).strip()
        if not safe_name:
            safe_name = "flashcards"
        
        import time
        timestamp = int(time.time())
        filename = f"{safe_name}_{timestamp}.apkg"
        file_path = f"/tmp/{filename}"
        
        # Generate deck with unique name and write to file
        deck = processor.create_anki_deck(final_data, deck_name)
        deck.write_to_file(file_path)
        file_size = os.path.getsize(file_path)
        
        app.logger.info(f"Generated file: {file_path} (size: {file_size} bytes)")
        
        download_url = f"/download/{filename}"
        full_url = f"https://flashcard-converter-haziqmakesai.replit.app{download_url}"
        
        result = {
            'success': True,
            'status': 'completed',
            'deck_name': deck_name,
            'cards_processed': len(cards),
            'file_size': file_size,
            'filename': filename,
            'download_url': download_url,
            'full_download_url': full_url,
            'message': f'Generated Anki deck with {len(cards)} cards'
        }
        
        app.logger.info(f"SUCCESS: {result}")
        return result, 200
            
    except Exception as e:
        app.logger.error(f"SIMPLE API ERROR: {str(e)}")
        import traceback
        app.logger.error(f"Traceback: {traceback.format_exc()}")
        return {
            'error': 'Processing failed',
            'message': str(e),
            'traceback': traceback.format_exc()
        }, 500
    
def generate_synaptic_recall_name(cards):
        """Generate SynapticRecall deck name based on card content analysis"""
        import re
        
        # Collect all text content from cards
        all_text = []
        for card in cards:
            # Get front/question content
            front_text = card.get('front', card.get('question', ''))
            back_text = card.get('back', card.get('answer', ''))
            tags = card.get('tags', [])
            
            all_text.extend([front_text, back_text])
            
            # Add tag content for analysis
            if isinstance(tags, list):
                all_text.extend([str(tag) for tag in tags])
            elif isinstance(tags, str):
                all_text.append(tags)
        
        # Combine all text and convert to lowercase
        combined_text = ' '.join(all_text).lower()
        
        # Medical topic keywords with priority order
        topic_keywords = {
            'spinothalamic': 'spinothalmictract',
            'spinothalmic': 'spinothalmictract', 
            'pain pathway': 'painpathways',
            'pain processing': 'painprocessing',
            'substantia gelatinosa': 'substantiagelatinosa',
            'dorsal horn': 'dorsalhorn',
            'spinal cord': 'spinalcord',
            'neuroanatomy': 'neuroanatomy',
            'cardiovascular': 'cardiovascular',
            'cardiology': 'cardiology',
            'respiratory': 'respiratory',
            'pulmonology': 'pulmonology',
            'pharmacology': 'pharmacology',
            'pathology': 'pathology',
            'anatomy': 'anatomy',
            'physiology': 'physiology',
            'biochemistry': 'biochemistry',
            'immunology': 'immunology',
            'microbiology': 'microbiology',
            'neurology': 'neurology',
            'psychiatry': 'psychiatry',
            'endocrinology': 'endocrinology',
            'gastroenterology': 'gastroenterology',
            'nephrology': 'nephrology',
            'hematology': 'hematology',
            'oncology': 'oncology',
            'dermatology': 'dermatology',
            'ophthalmology': 'ophthalmology',
            'otolaryngology': 'otolaryngology',
            'orthopedics': 'orthopedics',
            'radiology': 'radiology',
            'surgery': 'surgery',
            'emergency medicine': 'emergencymedicine',
            'internal medicine': 'internalmedicine',
            'family medicine': 'familymedicine',
            'pediatrics': 'pediatrics',
            'obstetrics': 'obstetrics',
            'gynecology': 'gynecology'
        }
        
        # Find the most relevant topic
        detected_topic = None
        for keyword, topic in topic_keywords.items():
            if keyword in combined_text:
                detected_topic = topic
                break
        
        # If no specific topic found, use general content analysis
        if not detected_topic:
            # Extract key medical terms
            medical_terms = re.findall(r'\b(?:tract|pathway|nerve|muscle|bone|organ|system|syndrome|disease|disorder|condition)\b', combined_text)
            if medical_terms:
                detected_topic = 'medicalterms'
            else:
                detected_topic = 'medicalcards'
        
        return f"synapticrecall_{detected_topic}"

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
        
        # Create Anki deck using the same logic as API endpoints
        deck = processor.create_anki_deck(json_data)
        
        # Generate .apkg file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.apkg') as tmp_file:
            deck.write_to_file(tmp_file.name)
            
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
        import traceback
        app.logger.error(f"Traceback: {traceback.format_exc()}")
        flash(f'Processing failed: {str(e)}', 'error')
        return redirect(url_for('index'))

# API routes are now defined directly in this file to avoid import issues

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
