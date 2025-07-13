import os
import json
import tempfile
import logging
import random
import time
import requests
import hashlib
import re
from urllib.parse import urlparse
from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
import genanki
from bs4 import BeautifulSoup

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

def process_html_images(html_content, media_files):
    """Find all images in HTML, download them, and replace URLs with local filenames"""
    if not html_content:
        return html_content
    
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Find all img tags
    for img in soup.find_all('img'):
        src = img.get('src')
        if src and src.startswith('http'):
            # Download the image
            local_filename = download_image_from_url(src, media_files)
            if local_filename:
                # Replace the URL with the local filename
                img['src'] = local_filename
                app.logger.info(f"Replaced image URL with local file: {local_filename}")
    
    return str(soup)

def create_simple_model():
    """Create a simple model with minimal CSS"""
    minimal_css = """
.card { 
    font-family: Arial, sans-serif;
    background-color: white;
    padding: 20px;
}

.night_mode { 
    background-color: #272828;
}

img { 
    max-width: 70%;
    max-height: 400px;
    height: auto;
    display: block;
    margin: 20px auto;
}
"""

    fields = [
        {'name': 'Front'},
        {'name': 'Back'}
    ]

    templates = [
        {
            'name': 'Card',
            'qfmt': '''{{Front}}''',
            'afmt': '''{{FrontSide}}
<hr id="answer">
{{Back}}'''
        }
    ]

    model = genanki.Model(
        1607392320,
        'Simple Medical Cards',
        fields=fields,
        templates=templates,
        css=minimal_css
    )

    # Create a separate cloze model
    cloze_model = genanki.Model(
        1607392321,
        'Simple Medical Cloze',
        fields=[{'name': 'Text'}],
        templates=[{
            'name': 'Cloze Card',
            'qfmt': '''{{cloze:Text}}''',
            'afmt': '''{{cloze:Text}}'''
        }],
        css=minimal_css,
        model_type=1  # Cloze type
    )

    return model, cloze_model

class SimpleFlashcardProcessor:
    def __init__(self):
        self.basic_model, self.cloze_model = create_simple_model()

    def process_cards(self, cards_data, deck_name="Medical Deck"):
        deck_id = random.randrange(1 << 30, 1 << 31)
        deck = genanki.Deck(deck_id, deck_name)
        media_files = []

        for card_index, card_info in enumerate(cards_data):
            app.logger.info(f"Processing card {card_index + 1}/{len(cards_data)}")

            if not isinstance(card_info, dict):
                app.logger.error(f"Card {card_index + 1} is not a dictionary")
                continue

            card_type = card_info.get('type', 'basic').lower()

            if card_type == 'cloze':
                self._process_cloze_card(deck, card_info, media_files)
            else:
                self._process_basic_card(deck, card_info, media_files)

        return deck, media_files

    def _process_cloze_card(self, deck, card_info, media_files):
        """Process a cloze deletion card"""
        # Get the front content (which contains the cloze deletions)
        front_html = card_info.get('front', '')
        
        # Process images in the HTML
        front_html = process_html_images(front_html, media_files)
        
        # For cloze cards, the front becomes the Text field
        note = genanki.Note(
            model=self.cloze_model,
            fields=[front_html],
            tags=self._process_tags(card_info.get('tags', []))
        )
        deck.add_note(note)

    def _process_basic_card(self, deck, card_info, media_files):
        """Process a basic (front/back) card"""
        # Get front and back content
        front_html = card_info.get('front', '')
        back_html = card_info.get('back', '')
        
        # Process images in both front and back HTML
        front_html = process_html_images(front_html, media_files)
        back_html = process_html_images(back_html, media_files)
        
        # Add notes section if it exists (at the bottom of back)
        notes = card_info.get('notes', '')
        if notes:
            # Style the notes section
            notes_styled = f'''<div style="text-align: center; font-style: italic; margin-top: 30px; color: #FF1493; font-size: 1.2em; padding-top: 20px; border-top: 1px solid #ddd;">
{notes}
</div>'''
            back_html += notes_styled
        
        # Create note with processed HTML
        note = genanki.Note(
            model=self.basic_model,
            fields=[front_html, back_html],
            tags=self._process_tags(card_info.get('tags', []))
        )
        deck.add_note(note)

    def _process_tags(self, tags):
        """Process tags safely"""
        if not tags:
            return []
        
        if isinstance(tags, str):
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
            return []
        
        return [tag.strip().replace(' ', '_') for tag in tag_list if tag.strip()]

def extract_cards(data):
    """Extract cards from various data formats"""
    cards = []
    
    # Handle array with objects containing 'output'
    if isinstance(data, list) and len(data) > 0:
        if isinstance(data[0], dict) and 'output' in data[0]:
            cards = data[0]['output']
        # Handle direct card array
        elif isinstance(data[0], dict) and ('front' in data[0] or 'type' in data[0]):
            cards = data
    # Handle object with 'cards' key
    elif isinstance(data, dict) and 'cards' in data:
        cards = data['cards']
    # Handle object with 'output' key
    elif isinstance(data, dict) and 'output' in data:
        cards = data['output']
    # Handle single card object
    elif isinstance(data, dict) and ('front' in data or 'type' in data):
        cards = [data]
    # Handle direct card array
    elif isinstance(data, list):
        cards = data
    
    app.logger.info(f"Data type: {type(data)}, Extracted cards: {len(cards)}")
    return cards

@app.route('/api/generate', methods=['POST', 'OPTIONS'])
def api_generate():
    if request.method == 'OPTIONS':
        return '', 200

    try:
        app.logger.info("=== ANKI GENERATION STARTED ===")

        # Get JSON data
        data = request.get_json(force=True)
        if not data:
            return jsonify({
                'error': 'No JSON data provided',
                'help': 'Send POST request with JSON body containing card data',
                'example': [{
                    "output": [{
                        "type": "basic",
                        "front": "<div>Question</div>",
                        "back": "<div>Answer</div>",
                        "tags": ["tag1"]
                    }]
                }]
            }), 400

        app.logger.info(f"Received data: {data}")

        # Extract cards
        cards = extract_cards(data)
        
        app.logger.info(f"Extracted {len(cards)} cards")

        if not cards:
            return jsonify({
                'error': 'No valid cards provided', 
                'received_data': data,
                'help': 'Check that your JSON contains cards in one of these formats: [{"output":[cards]}], {"cards":[cards]}, or [cards]'
            }), 400

        # Generate deck name
        deck_name = f"Medical_Deck_{time.strftime('%Y%m%d_%H%M%S')}"

        # Process cards
        processor = SimpleFlashcardProcessor()
        deck, media_files = processor.process_cards(cards, deck_name)

        # Create package
        package = genanki.Package(deck)
        package.media_files = media_files

        # Generate filename
        timestamp = int(time.time())
        filename = f"{deck_name}_{timestamp}.apkg"
        
        # Create downloads directory
        downloads_dir = os.path.join(os.getcwd(), 'downloads')
        os.makedirs(downloads_dir, exist_ok=True)
        
        # Clean up old files before creating new ones
        cleanup_old_files(downloads_dir)
        
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

        # Generate response
        download_url = f"/download/{filename}"
        full_url = f"{request.host_url.rstrip('/')}{download_url}"

        result = {
            'success': True,
            'deck_name': deck_name,
            'cards_processed': len(cards),
            'media_files_count': len(media_files),
            'file_size': file_size,
            'filename': filename,
            'download_url': download_url,
            'full_download_url': full_url
        }

        return jsonify(result), 200

    except Exception as e:
        app.logger.error(f"ERROR: {str(e)}")
        import traceback
        app.logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            'error': 'Processing failed',
            'message': str(e)
        }), 500

@app.route('/download/<path:filename>')
def download_file(filename):
    try:
        downloads_dir = os.path.join(os.getcwd(), 'downloads')
        file_path = os.path.join(downloads_dir, filename)
        
        if not os.path.exists(file_path):
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

@app.route('/api/enhanced-medical', methods=['POST', 'OPTIONS'])
def api_enhanced_medical():
    """Legacy compatibility endpoint - redirects to new /api/generate"""
    return api_generate()

@app.route('/api/simple', methods=['POST', 'OPTIONS'])
def api_simple():
    """Legacy compatibility endpoint - redirects to new /api/generate"""
    return api_generate()

@app.route('/health', methods=['GET'])
@app.route('/api/health', methods=['GET'])
def api_health():
    return jsonify({
        'status': 'healthy',
        'service': 'Simple Anki Generator',
        'version': '11.0.0',
        'features': [
            'html_image_extraction',
            'automatic_image_download',
            'basic_and_cloze_support',
            'notes_section_support',
            'simplified_structure',
            'persistent_download_links',
            'legacy_endpoint_compatibility'
        ]
    }), 200

@app.route('/')
def index():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Simple Anki Generator</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                max-width: 800px;
                margin: 50px auto;
                padding: 20px;
            }
            .endpoint {
                background: #f5f5f5;
                padding: 15px;
                border-radius: 8px;
                margin: 20px 0;
            }
            code {
                background: #e0e0e0;
                padding: 2px 6px;
                border-radius: 3px;
            }
        </style>
    </head>
    <body>
        <h1>Simple Anki Generator</h1>
        <p>Version 11.0.0 - Simplified structure with automatic image processing</p>

        <div class="endpoint">
            <h3>API Endpoint: <code>POST /api/generate</code></h3>
            <p>Send your card data with the following structure:</p>
            <pre>[
  {
    "output": [
      {
        "card_id": 1,
        "type": "basic",
        "front": "&lt;div&gt;Question HTML&lt;/div&gt;",
        "back": "&lt;div&gt;Answer HTML with &lt;img src='url'&gt;&lt;/div&gt;",
        "tags": ["tag1", "tag2"],
        "notes": "Optional notes text"
      }
    ]
  }
]</pre>
        </div>

        <div class="endpoint">
            <h3>Features:</h3>
            <ul>
                <li>Automatically extracts and downloads images from HTML</li>
                <li>Supports both basic and cloze card types</li>
                <li>Optional notes section (appears at bottom of card back)</li>
                <li>Simplified structure - just front, back, type, and tags</li>
                <li>Images styled at 70% width with proper centering</li>
                <li>Persistent download links (7-day retention)</li>
                <li>Automatic cleanup of old files</li>
            </ul>
        </div>
    </body>
    </html>
    """

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)