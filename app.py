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
from datetime import datetime, timedelta
from threading import Lock
import uuid

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

# Session storage - In-memory store with TTL
class SessionStore:
    def __init__(self, default_ttl_hours=1):
        self.sessions = {}
        self.lock = Lock()
        self.default_ttl = timedelta(hours=default_ttl_hours)
        
    def create_session(self, session_id=None, workflow_id=None, user_id=None):
        """Create a new session"""
        with self.lock:
            if not session_id:
                session_id = str(uuid.uuid4())
            
            self.sessions[session_id] = {
                'session_id': session_id,
                'workflow_id': workflow_id,
                'user_id': user_id,
                'cards': [],
                'created_at': datetime.now(),
                'last_updated': datetime.now(),
                'status': 'accumulating',
                'deck_name': None,
                'metadata': {}
            }
            return session_id
    
    def get_session(self, session_id):
        """Get session data"""
        with self.lock:
            session = self.sessions.get(session_id)
            if session:
                # Check if session has expired
                if datetime.now() - session['created_at'] > self.default_ttl:
                    del self.sessions[session_id]
                    return None
                return session
            return None
    
    def add_cards_to_session(self, session_id, cards, deck_name=None):
        """Add cards to existing session"""
        with self.lock:
            session = self.sessions.get(session_id)
            if not session:
                return None
            
            session['cards'].extend(cards)
            session['last_updated'] = datetime.now()
            
            # Update deck name if provided and not already set
            if deck_name and not session['deck_name']:
                session['deck_name'] = deck_name
            
            return session
    
    def finalize_session(self, session_id):
        """Mark session as finalized"""
        with self.lock:
            session = self.sessions.get(session_id)
            if session:
                session['status'] = 'finalized'
                session['last_updated'] = datetime.now()
                return session
            return None
    
    def cleanup_expired_sessions(self):
        """Remove expired sessions"""
        with self.lock:
            now = datetime.now()
            expired_sessions = [
                session_id for session_id, session in self.sessions.items()
                if now - session['created_at'] > self.default_ttl
            ]
            for session_id in expired_sessions:
                del self.sessions[session_id]
            return len(expired_sessions)
    
    def get_or_create_session(self, headers):
        """Get existing session from headers or create new one"""
        session_id = headers.get('X-Session-ID')
        workflow_id = headers.get('X-Workflow-ID')
        user_id = headers.get('X-User-ID')
        
        # If session_id provided, try to get it
        if session_id:
            session = self.get_session(session_id)
            if session:
                return session_id, False  # existing session
        
        # Create new session
        new_session_id = self.create_session(
            session_id=session_id,
            workflow_id=workflow_id,
            user_id=user_id
        )
        return new_session_id, True  # new session

# Initialize session store
session_store = SessionStore()

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
            # Fallback to local storage with proper URL generation
            download_url = f"/download/{filename}"
            # Get the proper host URL from request headers or environment
            host = request.headers.get('Host', request.host)
            # Use https for non-localhost hosts
            protocol = 'https' if 'localhost' not in host and '127.0.0.1' not in host else 'http'
            base_url = os.environ.get('BASE_URL', f"{protocol}://{host}")
            full_url = f"{base_url.rstrip('/')}{download_url}"
            app.logger.info(f"📁 Using local storage: {full_url}")

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

# Session-based batch processing endpoints
@app.route('/api/batch/session', methods=['POST'])
def create_batch_session():
    """Create a new batch session for accumulating flashcards"""
    try:
        data = request.get_json() or {}
        
        # Extract parameters
        workflow_id = data.get('workflow_id') or request.headers.get('X-Workflow-ID')
        user_id = data.get('user_id') or request.headers.get('X-User-ID')
        expected_batches = data.get('expected_batches')
        
        # Create session
        session_id = session_store.create_session(
            workflow_id=workflow_id,
            user_id=user_id
        )
        
        # Store expected batches if provided
        if expected_batches:
            session = session_store.get_session(session_id)
            session['metadata']['expected_batches'] = expected_batches
        
        return jsonify({
            'session_id': session_id,
            'status': 'active',
            'workflow_id': workflow_id,
            'expires_at': (datetime.now() + session_store.default_ttl).isoformat(),
            'endpoints': {
                'add_batch': f'/api/batch/session/{session_id}',
                'finalize': f'/api/batch/session/{session_id}/finalize',
                'status': f'/api/batch/session/{session_id}/status'
            }
        }), 201
    except Exception as e:
        app.logger.error(f"Error creating batch session: {e}")
        return jsonify({'error': 'Failed to create session', 'message': str(e)}), 500

@app.route('/api/batch/session/<session_id>', methods=['POST'])
def add_batch_to_session(session_id):
    """Add a batch of cards to an existing session"""
    try:
        # Get session
        session = session_store.get_session(session_id)
        if not session:
            return jsonify({'error': 'Session not found or expired'}), 404
        
        if session['status'] != 'accumulating':
            return jsonify({
                'error': f'Session is {session["status"]}',
                'hint': 'Session may already be finalized or failed'
            }), 409
        
        # Get batch ID from header or generate
        batch_id = request.headers.get('X-Batch-ID', str(uuid.uuid4()))
        
        # Check for duplicate batch
        existing_batch_ids = [b.get('batch_id') for b in session.get('metadata', {}).get('batches', [])]
        if batch_id in existing_batch_ids:
            app.logger.warning(f"Duplicate batch {batch_id} for session {session_id}")
            # Return success for idempotency
            return jsonify({
                'warning': 'Duplicate batch ignored',
                'batch_id': batch_id,
                'session_id': session_id,
                'total_cards': len(session['cards'])
            }), 200
        
        # Parse batch data using flexible parser
        raw_data = request.get_data(as_text=True)
        n8n_parser = N8nFlashcardParser()
        
        app.logger.info(f"Processing batch {batch_id} for session {session_id}")
        
        try:
            parsed_result = n8n_parser.parse_flashcard_data(raw_data)
            cards = parsed_result.get('cards', [])
            
            if not cards:
                return jsonify({
                    'error': 'No cards found in batch',
                    'batch_id': batch_id
                }), 400
            
            # Add cards to session
            deck_name = parsed_result.get('deck_name')
            session_store.add_cards_to_session(session_id, cards, deck_name)
            
            # Update session metadata
            session = session_store.get_session(session_id)
            if 'batches' not in session['metadata']:
                session['metadata']['batches'] = []
            
            batch_info = {
                'batch_id': batch_id,
                'batch_number': len(session['metadata']['batches']) + 1,
                'cards_count': len(cards),
                'received_at': datetime.now().isoformat(),
                'parsing_strategy': n8n_parser.flexible_parser.last_strategy_used
            }
            session['metadata']['batches'].append(batch_info)
            
            # Check if we should auto-finalize
            should_auto_finalize = False
            expected_batches = session['metadata'].get('expected_batches')
            if expected_batches and len(session['metadata']['batches']) >= expected_batches:
                should_auto_finalize = True
                app.logger.info(f"Auto-finalizing session {session_id} - reached expected batches")
            
            result = {
                'success': True,
                'batch_id': batch_id,
                'batch_number': batch_info['batch_number'],
                'cards_added': len(cards),
                'total_cards': len(session['cards']),
                'total_batches': len(session['metadata']['batches']),
                'session_status': session['status'],
                'parsing_strategy': batch_info['parsing_strategy']
            }
            
            if should_auto_finalize:
                result['auto_finalize_scheduled'] = True
                result['message'] = 'All expected batches received - session will be finalized'
            
            return jsonify(result), 202  # 202 Accepted for async processing
            
        except Exception as e:
            # Record failed batch
            if 'failed_batches' not in session['metadata']:
                session['metadata']['failed_batches'] = []
            
            session['metadata']['failed_batches'].append({
                'batch_id': batch_id,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            })
            
            app.logger.error(f"Failed to process batch {batch_id}: {e}")
            return jsonify({
                'error': 'Batch processing failed',
                'batch_id': batch_id,
                'message': str(e)
            }), 400
            
    except Exception as e:
        app.logger.error(f"Error adding batch to session: {e}")
        return jsonify({'error': 'Failed to add batch', 'message': str(e)}), 500

@app.route('/api/batch/session/<session_id>/finalize', methods=['POST'])
def finalize_batch_session(session_id):
    """Finalize session and generate the complete deck"""
    try:
        session = session_store.get_session(session_id)
        if not session:
            return jsonify({'error': 'Session not found or expired'}), 404
        
        # Check if already finalized (idempotent)
        if session['status'] == 'finalized' and 'final_result' in session:
            app.logger.info(f"Session {session_id} already finalized - returning cached result")
            return jsonify(session['final_result']), 200
        
        # Check if there are cards to process
        cards = session['cards']
        if not cards:
            return jsonify({
                'error': 'No cards to process',
                'session_id': session_id,
                'batches_received': len(session['metadata'].get('batches', []))
            }), 400
        
        app.logger.info(f"Finalizing session {session_id} with {len(cards)} cards")
        
        # Generate deck name
        deck_name = session['deck_name'] or generate_smart_deck_name(cards)
        
        # Process all cards
        processor = EnhancedFlashcardProcessor()
        deck, media_files = processor.process_cards(cards, deck_name)
        
        # Create package
        package = genanki.Package(deck)
        package.media_files = media_files
        
        # Generate filename
        safe_name = "".join(c for c in deck_name if c.isalnum() or c in (' ', '-', '_')).strip()
        if not safe_name:
            safe_name = "medical_deck"
        
        # Use session ID in filename for uniqueness
        filename = f"{safe_name}_{session_id[:8]}.apkg"
        
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
        
        # Upload to Supabase
        supabase_result = upload_deck_to_supabase(
            file_path,
            deck_name,
            session_id=session_id,
            user_id=session['user_id']
        )
        
        if supabase_result and supabase_result.get('success'):
            download_url = supabase_result['download_url']
            full_url = download_url
            storage_type = 'supabase'
            app.logger.info(f"✅ Using Supabase URL: {download_url}")
        else:
            # Fallback to local storage
            download_url = f"/download/{filename}"
            host = request.headers.get('Host', request.host)
            protocol = 'https' if 'localhost' not in host and '127.0.0.1' not in host else 'http'
            base_url = os.environ.get('BASE_URL', f"{protocol}://{host}")
            full_url = f"{base_url.rstrip('/')}{download_url}"
            storage_type = 'local'
            app.logger.info(f"📁 Using local storage: {full_url}")
        
        # Calculate processing time
        processing_time_ms = (datetime.now() - session['created_at']).total_seconds() * 1000
        
        # Create final result
        final_result = {
            'success': True,
            'status': 'completed',
            'session_id': session_id,
            'workflow_id': session.get('workflow_id'),
            'deck_name': deck_name,
            'total_cards': len(cards),
            'total_batches': len(session['metadata'].get('batches', [])),
            'failed_batches': len(session['metadata'].get('failed_batches', [])),
            'media_files_downloaded': len(media_files),
            'file_size': file_size,
            'filename': filename,
            'download_url': download_url,
            'full_download_url': full_url,
            'storage_type': storage_type,
            'processing_time_ms': processing_time_ms,
            'message': f'Successfully generated deck "{deck_name}" with {len(cards)} cards from {len(session["metadata"].get("batches", []))} batches'
        }
        
        # Update session
        session['status'] = 'finalized'
        session['final_result'] = final_result
        session_store.finalize_session(session_id)
        
        return jsonify(final_result), 200
        
    except Exception as e:
        app.logger.error(f"Error finalizing session {session_id}: {e}")
        import traceback
        app.logger.error(f"Traceback: {traceback.format_exc()}")
        
        # Mark session as failed
        session = session_store.get_session(session_id)
        if session:
            session['status'] = 'failed'
            session['error'] = str(e)
        
        return jsonify({
            'error': 'Failed to finalize session',
            'session_id': session_id,
            'message': str(e),
            'traceback': traceback.format_exc()
        }), 500

@app.route('/api/batch/session/<session_id>/status', methods=['GET'])
def get_session_status(session_id):
    """Get the status of a batch session"""
    session = session_store.get_session(session_id)
    if not session:
        return jsonify({'error': 'Session not found or expired'}), 404
    
    # Calculate session age and time until expiry
    age_seconds = (datetime.now() - session['created_at']).total_seconds()
    ttl_seconds = session_store.default_ttl.total_seconds()
    remaining_seconds = max(0, ttl_seconds - age_seconds)
    
    status_info = {
        'session_id': session_id,
        'workflow_id': session.get('workflow_id'),
        'status': session['status'],
        'created_at': session['created_at'].isoformat(),
        'last_updated': session['last_updated'].isoformat(),
        'age_seconds': age_seconds,
        'expires_in_seconds': remaining_seconds,
        'statistics': {
            'total_cards': len(session['cards']),
            'total_batches': len(session['metadata'].get('batches', [])),
            'failed_batches': len(session['metadata'].get('failed_batches', [])),
            'expected_batches': session['metadata'].get('expected_batches')
        }
    }
    
    # Add batch details
    if session['metadata'].get('batches'):
        status_info['batches'] = [
            {
                'batch_number': b['batch_number'],
                'cards_count': b['cards_count'],
                'received_at': b['received_at']
            }
            for b in session['metadata']['batches']
        ]
    
    # Add final result if finalized
    if session['status'] == 'finalized' and 'final_result' in session:
        status_info['final_result'] = session['final_result']
    
    return jsonify(status_info), 200

@app.route('/api/flexible-convert', methods=['POST', 'OPTIONS'])
def api_flexible_convert():
    """
    Enhanced flexible endpoint that supports both single-shot and session-based operations.
    Maintains backward compatibility while adding session support.
    """
    if request.method == 'OPTIONS':
        return '', 200

    try:
        app.logger.info("=== FLEXIBLE CONVERT API CALLED ===")
        
        # Check for session/workflow headers
        workflow_id = request.headers.get('X-Workflow-ID')
        session_id = request.headers.get('X-Session-ID')
        batch_id = request.headers.get('X-Batch-ID')
        user_id = request.headers.get('X-User-ID')
        
        # If workflow_id is provided, use session-based processing
        if workflow_id:
            app.logger.info(f"Detected workflow ID: {workflow_id}, using session-based processing")
            
            # Check if we have an existing session for this workflow
            existing_session = None
            for sid, session in session_store.sessions.items():
                if session.get('workflow_id') == workflow_id and session['status'] == 'accumulating':
                    existing_session = session
                    session_id = sid
                    break
            
            # Create new session if needed
            if not existing_session:
                session_id = session_store.create_session(
                    workflow_id=workflow_id,
                    user_id=user_id
                )
                app.logger.info(f"Created new session {session_id} for workflow {workflow_id}")
            else:
                app.logger.info(f"Using existing session {session_id} for workflow {workflow_id}")
            
            # Add batch to session
            return add_batch_to_session(session_id)
        
        # Otherwise, process as single-shot operation (original behavior)
        app.logger.info("No workflow ID detected, processing as single-shot operation")
        
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
            # Fallback to local storage with proper URL generation
            download_url = f"/download/{filename}"
            # Get the proper host URL from request headers or environment
            host = request.headers.get('Host', request.host)
            # Use https for non-localhost hosts
            protocol = 'https' if 'localhost' not in host and '127.0.0.1' not in host else 'http'
            base_url = os.environ.get('BASE_URL', f"{protocol}://{host}")
            full_url = f"{base_url.rstrip('/')}{download_url}"
            app.logger.info(f"📁 Using local storage: {full_url}")
        
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

# Background task for auto-finalization and cleanup
def auto_finalize_and_cleanup():
    """Background task to auto-finalize inactive sessions and clean up expired ones"""
    while True:
        try:
            time.sleep(60)  # Check every minute
            
            with session_store.lock:
                now = datetime.now()
                sessions_to_finalize = []
                sessions_to_cleanup = []
                
                for session_id, session in list(session_store.sessions.items()):
                    # Skip if already finalized
                    if session['status'] != 'accumulating':
                        # Check if expired
                        if now - session['created_at'] > session_store.default_ttl:
                            sessions_to_cleanup.append(session_id)
                        continue
                    
                    # Check for auto-finalization conditions
                    time_since_last_activity = now - session['last_updated']
                    auto_finalize_timeout = timedelta(minutes=5)  # 5 minutes of inactivity
                    
                    # Auto-finalize if:
                    # 1. Inactive for timeout period AND has cards
                    # 2. Expected batches reached
                    should_finalize = False
                    reason = ""
                    
                    if time_since_last_activity > auto_finalize_timeout and session['cards']:
                        should_finalize = True
                        reason = "inactivity timeout"
                    
                    expected_batches = session['metadata'].get('expected_batches')
                    if expected_batches and len(session['metadata'].get('batches', [])) >= expected_batches:
                        should_finalize = True
                        reason = "expected batches reached"
                    
                    if should_finalize:
                        sessions_to_finalize.append((session_id, reason))
            
            # Finalize sessions (outside the lock to avoid deadlock)
            for session_id, reason in sessions_to_finalize:
                try:
                    app.logger.info(f"Auto-finalizing session {session_id} due to {reason}")
                    # Create a mock request context for finalization
                    with app.test_request_context():
                        finalize_batch_session(session_id)
                except Exception as e:
                    app.logger.error(f"Failed to auto-finalize session {session_id}: {e}")
            
            # Clean up expired sessions
            with session_store.lock:
                for session_id in sessions_to_cleanup:
                    app.logger.info(f"Cleaning up expired session {session_id}")
                    del session_store.sessions[session_id]
            
            if sessions_to_finalize or sessions_to_cleanup:
                app.logger.info(f"Auto-finalized {len(sessions_to_finalize)} sessions, cleaned up {len(sessions_to_cleanup)} sessions")
                
        except Exception as e:
            app.logger.error(f"Error in auto-finalization task: {e}")
            import traceback
            app.logger.error(f"Traceback: {traceback.format_exc()}")

# Start background thread for auto-finalization
import threading
cleanup_thread = threading.Thread(target=auto_finalize_and_cleanup, daemon=True)
cleanup_thread.start()
app.logger.info("Background auto-finalization task started")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)