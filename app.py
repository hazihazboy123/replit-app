import os
import json
import tempfile
import logging
import random
import time
import requests
import hashlib
from urllib.parse import urlparse
from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
import genanki

# Import the new flexible parser
from flexible_parser import FlexibleJSONParser, N8nFlashcardParser

# Import Supabase utilities
from supabase_utils import (
    upload_deck_to_supabase, 
    generate_smart_deck_name,
    check_supabase_health,
    SUPABASE_ENABLED
)

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

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

def download_image_from_url(url, media_files_list):
    """Download image from URL and return local filename for Anki embedding"""
    try:
        parsed_url = urlparse(url)
        filename = os.path.basename(parsed_url.path)
        if not filename or '.' not in filename:
            url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
            filename = f"image_{url_hash}.jpg"

        valid_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.svg', '.webp']
        if not any(filename.lower().endswith(ext) for ext in valid_extensions):
            filename += '.jpg'

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()

        temp_path = os.path.join(tempfile.gettempdir(), filename)
        with open(temp_path, 'wb') as f:
            f.write(response.content)

        media_files_list.append(temp_path)
        return filename
    except Exception as e:
        app.logger.error(f"Error downloading image from {url}: {e}")
        return None

def cleanup_old_files(directory, days=7):
    """Clean up files older than specified days to prevent directory bloat"""
    try:
        cutoff_time = time.time() - (days * 24 * 60 * 60)
        for filename in os.listdir(directory):
            file_path = os.path.join(directory, filename)
            if os.path.isfile(file_path):
                if os.path.getmtime(file_path) < cutoff_time:
                    os.remove(file_path)
                    app.logger.debug(f"Cleaned up old file: {filename}")
    except Exception as e:
        app.logger.warning(f"Error during cleanup: {e}")

def create_enhanced_medical_model():
    """Create enhanced medical model with minimal CSS - let HTML handle styling"""
    minimal_css = """
/* Minimal base styles */
.card { 
    font-family: Arial, sans-serif;
    background-color: white;
    padding: 20px;
}

/* Night mode support */
.night_mode { 
    background-color: #272828;
}

/* Ensure images display properly - SMALLER SIZE */
img { 
    max-width: 70%;  /* Changed from 100% to 70% */
    max-height: 400px;  /* Added max height */
    height: auto;
    display: block;
    margin: 20px auto;
}

/* Ensure caption and notes styling is preserved */
div[style*="color: #FF1493"] {
    color: #FF1493 !important;
}

/* Ensure proper spacing for notes */
div[style*="margin-top: 20px"][style*="margin-bottom: 20px"] {
    margin-top: 20px !important;
    margin-bottom: 20px !important;
}
"""

    fields = [
        {'name': 'Front'},
        {'name': 'Back'}
    ]

    templates = [
        {
            'name': 'Medical Card',
            'qfmt': '''{{Front}}''',
            'afmt': '''{{FrontSide}}
<hr id="answer">
{{Back}}'''
        }
    ]

    # Handle both basic and cloze cards
    cloze_template = {
        'name': 'Cloze Card',
        'qfmt': '''{{cloze:Text}}''',
        'afmt': '''{{cloze:Text}}'''
    }

    model = genanki.Model(
        1607392320,
        'Enhanced Medical Cards',
        fields=fields,
        templates=templates,
        css=minimal_css
    )

    # Create a separate cloze model
    cloze_model = genanki.Model(
        1607392321,
        'Enhanced Medical Cloze',
        fields=[{'name': 'Text'}],
        templates=[cloze_template],
        css=minimal_css,
        model_type=1  # Cloze type
    )

    return model, cloze_model

class EnhancedFlashcardProcessor:
    def __init__(self):
        self.basic_model, self.cloze_model = create_enhanced_medical_model()

    def process_cards(self, cards_data, deck_name="Medical Deck"):
        deck_id = random.randrange(1 << 30, 1 << 31)
        deck = genanki.Deck(deck_id, deck_name)
        media_files = []

        for card_index, card_info in enumerate(cards_data):
            app.logger.info(f"Processing card {card_index + 1}/{len(cards_data)}")

            # Defensive check: ensure card_info is a dictionary
            if not isinstance(card_info, dict):
                app.logger.error(f"Card {card_index + 1} is not a dictionary, got: {type(card_info)}, value: {card_info}")
                continue

            card_type = card_info.get('type', 'basic').lower()

            if card_type == 'cloze':
                # Process cloze card
                self._process_cloze_card(deck, card_info, media_files)
            else:
                # Process basic card
                self._process_basic_card(deck, card_info, media_files, deck_id, card_index)

        return deck, media_files

    def _process_cloze_card(self, deck, card_info, media_files):
        """Process a cloze deletion card"""
        # For cloze cards, combine all content into the Text field
        content_parts = []

        # Add the front content (which contains the cloze deletions)
        front_html = card_info.get('front', '')
        if front_html:
            content_parts.append(front_html)

        # Add any additional components
        self._add_common_components(content_parts, card_info, media_files)

        # Combine all parts
        full_content = '\n'.join(content_parts)

        # Create cloze note
        note = genanki.Note(
            model=self.cloze_model,
            fields=[full_content],
            tags=self._process_tags(card_info.get('tags', []))
        )
        deck.add_note(note)

    def _process_basic_card(self, deck, card_info, media_files, deck_id, card_index):
        """Process a basic (front/back) card"""
        # FRONT: Use exactly as provided
        front_html = card_info.get('front', '')

        # BACK: Build from components
        back_parts = []

        # 1. Answer text - use exactly as provided
        back_text = card_info.get('back', '')
        if back_text:
            back_parts.append(back_text)

        # Add common components
        self._add_common_components(back_parts, card_info, media_files)

        # Combine all back parts
        back_content = '\n'.join(back_parts)

        # Create note with front and back
        note = genanki.Note(
            model=self.basic_model,
            fields=[front_html, back_content],
            tags=self._process_tags(card_info.get('tags', []))
        )
        deck.add_note(note)

    def _process_tags(self, tags):
        """Process tags safely, handling both strings and lists"""
        if not tags:
            return []
        
        # If it's a string, split by common delimiters
        if isinstance(tags, str):
            # Split by comma, semicolon, or double colon
            if '::' in tags:
                tag_list = tags.split('::')
            elif ',' in tags:
                tag_list = tags.split(',')
            elif ';' in tags:
                tag_list = tags.split(';')
            else:
                tag_list = [tags]
        elif isinstance(tags, list):
            tag_list = tags
        else:
            app.logger.warning(f"Unknown tags format: {type(tags)}, value: {tags}")
            return []
        
        # Clean up tags and replace spaces with underscores
        return [tag.strip().replace(' ', '_') for tag in tag_list if tag.strip()]

    def _add_common_components(self, content_parts, card_info, media_files):
        """Add common components - NOTES NOW ADDED LAST"""
        # Defensive check: ensure card_info is a dictionary
        if not isinstance(card_info, dict):
            app.logger.warning(f"card_info is not a dictionary in _add_common_components: {type(card_info)}")
            return
        
        # Store notes to add at the end
        notes_content = None
        
        # 1. Check for notes but don't add yet - preserve original font size
        notes = card_info.get('notes', '')
        if notes:
            # Only add centering if not present, preserve original font size
            if 'text-align: center' not in notes:
                # If notes don't have center alignment, add it
                if 'style="' in notes:
                    notes = notes.replace('style="', 'style="text-align: center; ')
                elif '<div' in notes:
                    notes = notes.replace('<div', '<div style="text-align: center;"')
            
            # Ensure proper spacing but preserve font size
            if 'margin-top: 10px' in notes:
                notes = notes.replace('margin-top: 10px', 'margin-top: 20px')
            elif 'margin-top: 20px' not in notes and 'margin-bottom: 20px' not in notes:
                # Add spacing wrapper if not present - no font size change
                if not notes.startswith('<div'):
                    notes = f'<div style="text-align: center; font-style: italic; margin-top: 20px; color: #FF1493;">{notes}</div>'
            
            notes_content = notes

        # 2. Images handling with captions
        # Check for 'images' array first (from n8n processing)
        images = card_info.get('images', [])
        if images:
            for image_item in images:
                # Handle both string URLs and objects with URL/caption
                if isinstance(image_item, str) and image_item.startswith('http'):
                    # Simple URL string
                    downloaded_filename = download_image_from_url(image_item, media_files)
                    if downloaded_filename:
                        content_parts.append(f'<div style="text-align: center;"><img src="{downloaded_filename}" style="width: 70%; max-height: 400px; height: auto; object-fit: contain; margin: 10px auto; display: block;"></div>')
                elif isinstance(image_item, dict):
                    # Object with url and caption
                    image_url = image_item.get('url', '')
                    image_caption = image_item.get('caption', '')

                    if image_url and image_url.startswith('http'):
                        downloaded_filename = download_image_from_url(image_url, media_files)
                        if downloaded_filename:
                            content_parts.append(f'<div style="text-align: center;"><img src="{downloaded_filename}" style="width: 70%; max-height: 400px; height: auto; object-fit: contain; margin: 10px auto; display: block;"></div>')
                            # Add caption immediately after image if it exists
                            if image_caption:
                                content_parts.append(image_caption)

        # Also check for 'image' field (legacy support) - can be string URL or object
        image_data = card_info.get('image', '')
        if image_data:
            image_url = ''
            image_caption = ''
            
            # Handle both string URLs and objects
            if isinstance(image_data, str):
                image_url = image_data
            elif isinstance(image_data, dict):
                image_url = image_data.get('url', '')
                image_caption = image_data.get('caption', '')

            if image_url and image_url.startswith('http'):
                downloaded_filename = download_image_from_url(image_url, media_files)
                if downloaded_filename:
                    content_parts.append(f'<div style="text-align: center;"><img src="{downloaded_filename}" style="width: 70%; max-height: 400px; height: auto; object-fit: contain; margin: 10px auto; display: block;"></div>')
                    # Add caption immediately after image
                    if image_caption:
                        content_parts.append(image_caption)

        # 3. Clinical vignette - comes AFTER images and captions
        clinical_vignette = card_info.get('clinical_vignette', '')
        if clinical_vignette:
            content_parts.append(clinical_vignette)

        # 4. Explanation - use exactly as provided
        explanation = card_info.get('explanation', '')
        if explanation:
            content_parts.append(explanation)

        # 5. Legacy vignette support (if using nested structure)
        vignette_data = card_info.get('vignette', {})
        if vignette_data:
            clinical_case = vignette_data.get('clinical_case', '')
            if clinical_case:
                content_parts.append(clinical_case)

            vignette_explanation = vignette_data.get('explanation', '')
            if vignette_explanation:
                content_parts.append(vignette_explanation)

        # 6. Mnemonic - use exactly as provided
        mnemonic = card_info.get('mnemonic', '')
        if mnemonic:
            content_parts.append(mnemonic)
        
        # 7. FINALLY add notes at the end (after all other content)
        if notes_content:
            content_parts.append(notes_content)

def extract_deck_name(data):
    """Extract deck name from various data formats or use smart naming"""
    # First try traditional deck_name field
    if isinstance(data, list) and len(data) > 0:
        if isinstance(data[0], dict) and 'deck_name' in data[0]:
            return data[0].get('deck_name')
    elif isinstance(data, dict):
        deck_name = data.get('deck_name')
        if deck_name:
            return deck_name
    
    # If no deck_name provided, we'll use smart naming from tags later
    return None

def extract_cards(data):
    """Extract cards from various data formats including nested card wrappers"""
    cards = []
    
    # Handle the structure from your n8n output
    if isinstance(data, dict) and 'cards' in data:
        cards = data['cards']
    elif isinstance(data, list):
        # Check if it's an array with objects containing 'cards'
        if len(data) > 0 and isinstance(data[0], dict) and 'cards' in data[0]:
            # Flatten all cards from all objects in the array
            all_cards = []
            for item in data:
                if isinstance(item, dict) and 'cards' in item:
                    item_cards = item['cards']
                    if isinstance(item_cards, list):
                        all_cards.extend(item_cards)
            cards = all_cards
        else:
            cards = data
    
    # Process cards and handle nested "card" wrappers
    if isinstance(cards, list):
        valid_cards = []
        for i, card_item in enumerate(cards):
            if isinstance(card_item, dict):
                # Check if this item has a nested "card" wrapper
                if 'card' in card_item and isinstance(card_item['card'], dict):
                    # Extract the nested card
                    valid_cards.append(card_item['card'])
                    app.logger.debug(f"Extracted nested card with ID: {card_item['card'].get('card_id', 'unknown')}")
                else:
                    # Direct card format
                    valid_cards.append(card_item)
            else:
                app.logger.warning(f"Skipping invalid card at index {i}: {type(card_item)} - {card_item}")
        return valid_cards
    
    return []

@app.route('/api/enhanced-medical', methods=['POST', 'OPTIONS'])
def api_enhanced_medical():
    if request.method == 'OPTIONS':
        return '', 200

    try:
        app.logger.info("=== ENHANCED MEDICAL API CALLED ===")

        # Get JSON data
        data = request.get_json(force=True)
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400

        # Log the structure we received
        app.logger.debug(f"Received data structure: {type(data)}")
        if isinstance(data, dict):
            app.logger.debug(f"Dict keys: {list(data.keys())}")

        # Extract deck name and cards
        deck_name = extract_deck_name(data)
        cards = extract_cards(data)

        app.logger.debug(f"Extracted {len(cards) if cards else 0} cards")
        if cards:
            app.logger.debug(f"First card type: {type(cards[0]) if len(cards) > 0 else 'N/A'}")
            app.logger.debug(f"First card content: {cards[0] if len(cards) > 0 else 'N/A'}")

        if not cards:
            return jsonify({'error': 'No valid cards provided'}), 400

        # Generate smart deck name based on lecture tags if not provided
        if not deck_name:
            deck_name = generate_smart_deck_name(cards)
            app.logger.info(f"Generated smart deck name from tags: '{deck_name}'")
        
        app.logger.info(f"Processing {len(cards)} cards for deck '{deck_name}'")

        # Process cards
        processor = EnhancedFlashcardProcessor()
        deck, media_files = processor.process_cards(cards, deck_name)

        # Create package
        package = genanki.Package(deck)
        package.media_files = media_files

        # Generate filename and use persistent downloads directory
        safe_name = "".join(c for c in deck_name if c.isalnum() or c in (' ', '-', '_')).strip()
        if not safe_name:
            safe_name = "medical_deck"
        
        # Add timestamp to make filename unique
        timestamp = int(time.time())
        filename = f"{safe_name}_{timestamp}.apkg"
        
        # Create downloads directory if it doesn't exist
        downloads_dir = os.path.join(os.getcwd(), 'downloads')
        os.makedirs(downloads_dir, exist_ok=True)
        
        # Files persist permanently - no automatic cleanup
        # Use /api/cleanup endpoint if manual cleanup is needed
        
        file_path = os.path.join(downloads_dir, filename)

        # Write package
        package.write_to_file(file_path)

        # Get file info
        file_size = os.path.getsize(file_path)
        app.logger.info(f"Generated deck: {file_path} (size: {file_size} bytes)")

        # Clean up media files
        for media_file in media_files:
            try:
                os.remove(media_file)
            except:
                pass

        # Try to upload to Supabase
        session_id = request.headers.get('X-Session-ID')
        user_id = request.headers.get('X-User-ID')
        
        supabase_result = upload_deck_to_supabase(
            file_path,
            deck_name,
            session_id=session_id,
            user_id=user_id
        )
        
        if supabase_result and supabase_result.get('success'):
            # Use Supabase URL
            download_url = supabase_result['download_url']
            full_url = download_url
            app.logger.info(f"✅ Using Supabase URL: {download_url}")
        else:
            # Fallback to local storage
            download_url = f"/download/{filename}"
            full_url = f"{request.host_url.rstrip('/')}{download_url}"
            app.logger.info("📁 Using local storage (Supabase unavailable)")

        result = {
            'success': True,
            'status': 'completed',
            'deck_name': deck_name,
            'cards_processed': len(cards),
            'media_files_downloaded': len(media_files),
            'file_size': file_size,
            'filename': filename,
            'download_url': download_url,
            'full_download_url': full_url,
            'storage_type': 'supabase' if supabase_result else 'local',
            'permanent_link': supabase_result is not None,
            'message': f'Successfully generated deck "{deck_name}" with {len(cards)} cards'
        }

        return jsonify(result), 200

    except Exception as e:
        app.logger.error(f"ERROR: {str(e)}")
        import traceback
        app.logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            'error': 'Processing failed',
            'message': str(e),
            'traceback': traceback.format_exc()
        }), 500

@app.route('/api/simple', methods=['POST', 'OPTIONS'])
def api_simple():
    """Legacy compatibility endpoint"""
    return api_enhanced_medical()

@app.route('/api/flexible-convert', methods=['POST', 'OPTIONS'])
def api_flexible_convert():
    """
    New flexible endpoint that handles n8n output format and other wrapped JSON structures.
    Supports triple-layer JSON parsing and various malformed inputs.
    """
    if request.method == 'OPTIONS':
        return '', 200

    try:
        app.logger.info("=== FLEXIBLE CONVERT API CALLED ===")
        
        # Initialize parsers
        n8n_parser = N8nFlashcardParser()
        
        # Get raw data - don't force JSON parsing
        raw_data = request.get_data(as_text=True)
        
        if not raw_data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Log raw data size and preview
        app.logger.info(f"Received {len(raw_data)} bytes of data")
        app.logger.debug(f"Data preview: {raw_data[:200]}..." if len(raw_data) > 200 else f"Data: {raw_data}")
        
        # Parse the data using flexible parser
        try:
            parsed_result = n8n_parser.parse_flashcard_data(raw_data)
        except ValueError as e:
            # Provide helpful error response
            return jsonify({
                'error': 'Failed to parse input data',
                'message': str(e),
                'hints': [
                    'Ensure data is valid JSON or wrapped in supported format',
                    'For n8n: Check that output contains markdown-wrapped JSON',
                    'Remove any trailing commas in JSON',
                    'Ensure all strings are properly quoted'
                ],
                'data_preview': raw_data[:500] + '...' if len(raw_data) > 500 else raw_data
            }), 400
        
        # Extract cards and deck name
        cards = parsed_result.get('cards', [])
        deck_name = parsed_result.get('deck_name')
        
        # Validate we have cards
        if not cards:
            return jsonify({
                'error': 'No cards found in parsed data',
                'parsed_structure': list(parsed_result.keys()) if isinstance(parsed_result, dict) else 'not a dict',
                'hint': 'Ensure your data contains a "cards" array or is an array of card objects'
            }), 400
        
        app.logger.info(f"Parsed {len(cards)} cards successfully")
        
        # Generate smart deck name based on lecture tags if not provided
        if not deck_name:
            deck_name = generate_smart_deck_name(cards)
            app.logger.info(f"Generated smart deck name from tags: '{deck_name}'")
        
        app.logger.info(f"Processing {len(cards)} cards for deck '{deck_name}'")
        
        # Process cards using existing processor
        processor = EnhancedFlashcardProcessor()
        deck, media_files = processor.process_cards(cards, deck_name)
        
        # Create package
        package = genanki.Package(deck)
        package.media_files = media_files
        
        # Generate filename
        safe_name = "".join(c for c in deck_name if c.isalnum() or c in (' ', '-', '_')).strip()
        if not safe_name:
            safe_name = "medical_deck"
        
        timestamp = int(time.time())
        filename = f"{safe_name}_{timestamp}.apkg"
        
        # Create downloads directory
        downloads_dir = os.path.join(os.getcwd(), 'downloads')
        os.makedirs(downloads_dir, exist_ok=True)
        
        file_path = os.path.join(downloads_dir, filename)
        
        # Write package
        package.write_to_file(file_path)
        
        # Get file info
        file_size = os.path.getsize(file_path)
        app.logger.info(f"Generated deck: {file_path} (size: {file_size} bytes)")
        
        # Clean up media files
        for media_file in media_files:
            try:
                os.remove(media_file)
            except:
                pass
        
        # Try to upload to Supabase
        session_id = request.headers.get('X-Session-ID')
        user_id = request.headers.get('X-User-ID')
        
        supabase_result = upload_deck_to_supabase(
            file_path,
            deck_name,
            session_id=session_id,
            user_id=user_id
        )
        
        if supabase_result and supabase_result.get('success'):
            # Use Supabase URL
            download_url = supabase_result['download_url']
            full_url = download_url
            app.logger.info(f"✅ Using Supabase URL: {download_url}")
        else:
            # Fallback to local storage
            download_url = f"/download/{filename}"
            full_url = f"{request.host_url.rstrip('/')}{download_url}"
            app.logger.info("📁 Using local storage (Supabase unavailable)")
        
        result = {
            'success': True,
            'status': 'completed',
            'deck_name': deck_name,
            'cards_processed': len(cards),
            'media_files_downloaded': len(media_files),
            'file_size': file_size,
            'filename': filename,
            'download_url': download_url,
            'full_download_url': full_url,
            'parsing_strategy': n8n_parser.flexible_parser.last_strategy_used,
            'storage_type': 'supabase' if supabase_result else 'local',
            'permanent_link': supabase_result is not None,
            'message': f'Successfully generated deck "{deck_name}" with {len(cards)} cards'
        }
        
        return jsonify(result), 200
        
    except Exception as e:
        app.logger.error(f"ERROR in flexible-convert: {str(e)}")
        import traceback
        app.logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            'error': 'Processing failed',
            'message': str(e),
            'traceback': traceback.format_exc()
        }), 500

@app.route('/download/<path:filename>')
def download_file(filename):
    try:
        # Look for file in persistent downloads directory
        downloads_dir = os.path.join(os.getcwd(), 'downloads')
        file_path = os.path.join(downloads_dir, filename)
        
        if not os.path.exists(file_path):
            app.logger.warning(f"File not found: {file_path}")
            return f"File not found: {filename}", 404

        return send_file(
            file_path,
            as_attachment=True,
            download_name=filename,
            mimetype='application/octet-stream'
        )
    except Exception as e:
        app.logger.error(f"Download error: {e}")
        return "Download failed", 500

@app.route('/api/health', methods=['GET'])
def api_health():
    return jsonify({
        'status': 'healthy',
        'service': 'Enhanced Medical Anki Generator',
        'version': '11.0.0',
        'features': [
            'pure_html_preservation',
            'cloze_card_support',
            'images_array_support',
            'optimized_image_sizing_70_percent',
            'notes_positioned_last',
            'preserved_notes_font_size',
            'robust_error_handling',
            'invalid_card_filtering',
            'safe_tags_processing',
            'flexible_image_handling',
            'nested_array_support',
            'centered_image_layout',
            'nested_card_wrapper_support',
            'permanent_download_links',
            'no_style_modification',
            'clinical_vignettes_preserved',
            'mnemonics_preserved',
            'smaller_images_70_percent',
            'magenta_captions_support',
            'enhanced_notes_spacing',
            'flexible_json_parsing',
            'n8n_triple_layer_support',
            'malformed_json_recovery',
            'markdown_code_block_extraction',
            'llm_output_cleanup',
            'smart_deck_naming_from_tags',
            'supabase_permanent_storage',
            'intelligent_lecture_detection'
        ],
        'storage': {
            'supabase_enabled': SUPABASE_ENABLED,
            'bucket': 'synapticrecall-links' if SUPABASE_ENABLED else None,
            'fallback': 'local_storage'
        },
        'endpoints': {
            '/api/enhanced-medical': 'Original endpoint with basic JSON parsing',
            '/api/flexible-convert': 'New endpoint with flexible parsing for n8n and LLM outputs',
            '/api/simple': 'Legacy compatibility endpoint'
        },
        'timestamp': int(time.time())
    }), 200

@app.route('/api/health/supabase', methods=['GET'])
def api_health_supabase():
    """Check Supabase storage health"""
    health_status = check_supabase_health()
    status_code = 200 if health_status.get('status') in ['healthy', 'disabled'] else 503
    return jsonify(health_status), status_code

@app.route('/api/cleanup', methods=['POST'])
def api_cleanup():
    """Manual cleanup endpoint for administrative use"""
    try:
        days = request.json.get('days', 30) if request.json else 30
        downloads_dir = os.path.join(os.getcwd(), 'downloads')
        
        cleaned_files = []
        cutoff_time = time.time() - (days * 24 * 60 * 60)
        
        for filename in os.listdir(downloads_dir):
            file_path = os.path.join(downloads_dir, filename)
            if os.path.isfile(file_path):
                if os.path.getmtime(file_path) < cutoff_time:
                    os.remove(file_path)
                    cleaned_files.append(filename)
        
        return jsonify({
            'status': 'completed',
            'cleaned_files': cleaned_files,
            'days_threshold': days,
            'message': f'Cleaned {len(cleaned_files)} files older than {days} days'
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/')
def index():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Enhanced Medical Anki Generator</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                max-width: 800px;
                margin: 50px auto;
                padding: 20px;
            }
            .features {
                background: #f5f5f5;
                padding: 20px;
                border-radius: 8px;
                margin-top: 20px;
            }
            .features h3 {
                margin-top: 0;
            }
            .features ul {
                margin: 10px 0;
            }
            .endpoints {
                background: #e8f4f8;
                padding: 20px;
                border-radius: 8px;
                margin-top: 20px;
            }
            .endpoints h3 {
                margin-top: 0;
            }
            code {
                background: #f0f0f0;
                padding: 2px 4px;
                border-radius: 3px;
                font-family: monospace;
            }
        </style>
    </head>
    <body>
        <h1>Medical Anki Generator</h1>
        <p>Version 11.0.0 - Flexible JSON parsing with n8n support</p>

        <div class="features">
            <h3>Features:</h3>
            <ul>
                <li>Pure HTML preservation - no style stripping</li>
                <li>Full cloze card support</li>
                <li>Images displayed at 70% width (max 400px height)</li>
                <li>Magenta (#FF1493) caption and notes support</li>
                <li>Enhanced spacing for notes (20px margins)</li>
                <li>Captions positioned between images and clinical vignettes</li>
                <li>Support for both image arrays and legacy image objects</li>
                <li>Clinical vignettes and mnemonics preserved exactly as provided</li>
                <li><strong>NEW:</strong> Flexible JSON parsing for n8n and LLM outputs</li>
                <li><strong>NEW:</strong> Triple-layer JSON structure support</li>
                <li><strong>NEW:</strong> Markdown code block extraction</li>
                <li><strong>NEW:</strong> Malformed JSON recovery</li>
            </ul>
        </div>

        <div class="endpoints">
            <h3>API Endpoints:</h3>
            <ul>
                <li><code>POST /api/flexible-convert</code> - NEW endpoint with flexible parsing for n8n/LLM outputs</li>
                <li><code>POST /api/enhanced-medical</code> - Original endpoint with standard JSON parsing</li>
                <li><code>POST /api/simple</code> - Legacy compatibility endpoint</li>
                <li><code>GET /api/health</code> - Health check and feature list</li>
            </ul>
        </div>
    </body>
    </html>
    """

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)