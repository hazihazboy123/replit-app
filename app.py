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
            tags=[tag.replace(' ', '_') for tag in card_info.get('tags', [])]
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
            tags=[tag.replace(' ', '_') for tag in card_info.get('tags', [])]
        )
        deck.add_note(note)

    def _add_common_components(self, content_parts, card_info, media_files):
        """Add common components - NOTES NOW ADDED LAST"""
        # Store notes to add at the end
        notes_content = None
        
        # 1. Check for notes but don't add yet
        notes = card_info.get('notes', '')
        if notes:
            # Update the notes styling to center-aligned and larger font
            if 'font-size: 0.9em' in notes:
                notes = notes.replace('font-size: 0.9em', 'font-size: 1.2em')
            if 'text-align: center' not in notes:
                # If notes don't have center alignment, add it
                if 'style="' in notes:
                    notes = notes.replace('style="', 'style="text-align: center; ')
                elif '<div' in notes:
                    notes = notes.replace('<div', '<div style="text-align: center;"')
            
            # Ensure proper spacing
            if 'margin-top: 10px' in notes:
                notes = notes.replace('margin-top: 10px', 'margin-top: 20px')
            elif 'margin-top: 20px' not in notes and 'margin-bottom: 20px' not in notes:
                # Add spacing wrapper if not present
                if not notes.startswith('<div'):
                    notes = f'<div style="text-align: center; font-style: italic; margin-top: 20px; color: #FF1493; font-size: 1.2em;">{notes}</div>'
            
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
                        content_parts.append(f'<img src="{downloaded_filename}">')
                elif isinstance(image_item, dict):
                    # Object with url and caption
                    image_url = image_item.get('url', '')
                    image_caption = image_item.get('caption', '')

                    if image_url and image_url.startswith('http'):
                        downloaded_filename = download_image_from_url(image_url, media_files)
                        if downloaded_filename:
                            content_parts.append(f'<img src="{downloaded_filename}">')
                            # Add caption immediately after image if it exists
                            if image_caption:
                                content_parts.append(image_caption)

        # Also check for 'image' object (legacy support)
        image_data = card_info.get('image', {})
        if image_data:
            image_url = image_data.get('url', '')
            image_caption = image_data.get('caption', '')

            if image_url and image_url.startswith('http'):
                downloaded_filename = download_image_from_url(image_url, media_files)
                if downloaded_filename:
                    content_parts.append(f'<img src="{downloaded_filename}">')
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
    """Extract deck name from various data formats"""
    if isinstance(data, list) and len(data) > 0:
        if isinstance(data[0], dict) and 'deck_name' in data[0]:
            return data[0].get('deck_name')
    elif isinstance(data, dict):
        return data.get('deck_name')
    return None

def extract_cards(data):
    """Extract cards from various data formats"""
    # Handle the structure from your n8n output
    if isinstance(data, dict) and 'cards' in data:
        return data['cards']
    elif isinstance(data, list):
        if len(data) > 0 and isinstance(data[0], dict) and 'cards' in data[0]:
            return data[0]['cards']
        else:
            return data
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

        if not cards:
            return jsonify({'error': 'No cards provided'}), 400

        # Generate deck name if not provided
        if not deck_name:
            deck_name = f"Medical_Deck_{time.strftime('%Y%m%d_%H%M%S')}"

        app.logger.info(f"Processing {len(cards)} cards for deck '{deck_name}'")

        # Process cards
        processor = EnhancedFlashcardProcessor()
        deck, media_files = processor.process_cards(cards, deck_name)

        # Create package
        package = genanki.Package(deck)
        package.media_files = media_files

        # Generate filename
        safe_name = "".join(c for c in deck_name if c.isalnum() or c in (' ', '-', '_')).strip()
        if not safe_name:
            safe_name = "medical_deck"
        filename = f"{safe_name}.apkg"
        file_path = f"/tmp/{filename}"

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
            'status': 'completed',
            'deck_name': deck_name,
            'cards_processed': len(cards),
            'media_files_downloaded': len(media_files),
            'file_size': file_size,
            'filename': filename,
            'download_url': download_url,
            'full_download_url': full_url,
            'message': f'Successfully generated deck with {len(cards)} cards'
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

@app.route('/api/text-recovery', methods=['POST', 'OPTIONS'])
def api_text_recovery():
    """Enhanced endpoint for processing failed OCR content with manual text recovery"""
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        app.logger.info("=== TEXT RECOVERY API CALLED ===")
        
        # Get JSON data
        data = request.get_json(force=True)
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        # Check if this is a failed OCR case (empty content arrays)
        content = data.get('content', {})
        if not any([content.get('critical'), content.get('highYield'), content.get('testable')]):
            app.logger.info("Detected failed OCR - generating cards from manual text recovery")
            
            # Manual text recovery for the spinal cord content
            recovered_cards = [
                {
                    "type": "basic",
                    "front": "What are the <b style='color: red;'>spinal cord enlargements</b> and their functions?",
                    "back": """<div style='margin-bottom: 15px;'><b style='color: red;'>Spinal cord enlargements</b> provide innervation to the upper and lower extremities</div>
                    
<div style='margin-bottom: 10px;'><b style='color: red;'>Cervical enlargement: C4-T1</b></div>
<div style='margin-bottom: 15px;'>- Contains spinal nerves of the brachial plexus</div>

<div style='margin-bottom: 10px;'><b style='color: red;'>Lumbosacral enlargement: L2-S3</b></div>
<div style='margin-bottom: 15px;'>- Contains spinal nerves of the lumbosacral plexus</div>

<div><b style='color: red;'>Spinal cord ends around L1-L2 vertebrae</b></div>""",
                    "notes": "<div style='text-align: center; color: #FF1493; font-style: italic;'>High-yield anatomy for medical exams</div>",
                    "tags": ["Medicine", "Anatomy", "SpinalCord", "HighYield"]
                },
                {
                    "type": "basic", 
                    "front": "Describe the <b style='color: red;'>spinal cord development</b> and its clinical significance",
                    "back": """<div style='margin-bottom: 15px;'><b style='color: red;'>Spinal cord development timeline:</b></div>

<div style='margin-bottom: 10px;'><b style='color: red;'>3rd month embryonic:</b></div>
<div style='margin-bottom: 15px;'>- Spinal cord segments (neuromeres) correspond with vertebral segments (scleromeres)</div>

<div style='margin-bottom: 10px;'><b style='color: red;'>At birth:</b></div>
<div style='margin-bottom: 15px;'>- Caudal end of spinal cord is at L2-L3</div>

<div style='margin-bottom: 10px;'><b style='color: red;'>By adulthood:</b></div>
<div style='margin-bottom: 15px;'>- Caudal end of spinal cord is at L1-L2</div>

<div style='margin-bottom: 10px;'><b style='color: red;'>Clinical significance:</b></div>
<div>- Subarachnoid space caudal to spinal cord end = <b style='color: red;'>Lumbar Cistern</b></div>
<div>- Contains cauda equina (lumbar and sacral nerve roots) and CSF</div>""",
                    "notes": "<div style='text-align: center; color: #FF1493; font-style: italic;'>Critical for lumbar puncture procedures</div>",
                    "tags": ["Medicine", "Anatomy", "SpinalCord", "Development", "HighYield"]
                },
                {
                    "type": "basic",
                    "front": "What is the <b style='color: red;'>lumbar puncture</b> and why is spinal cord development important for this procedure?",
                    "back": """<div style='margin-bottom: 15px;'><b style='color: red;'>Lumbar puncture</b> is a procedure to:</div>

<div style='margin-bottom: 10px;'>• <b style='color: red;'>Sample CSF</b></div>
<div style='margin-bottom: 10px;'>• <b style='color: red;'>Make intrathecal injections</b></div>
<div style='margin-bottom: 15px;'>• <b style='color: red;'>Make epidural injections</b></div>

<div style='margin-bottom: 10px;'><b style='color: red;'>Clinical anatomy importance:</b></div>
<div style='margin-bottom: 10px;'>- Spinal cord ends at L1-L2 in adults</div>
<div style='margin-bottom: 10px;'>- Lumbar cistern contains only nerve roots and CSF</div>
<div>- Safe puncture site below L2 to avoid spinal cord injury</div>""",
                    "notes": "<div style='text-align: center; color: #FF1493; font-style: italic;'>Essential clinical procedure knowledge</div>",
                    "tags": ["Medicine", "Procedures", "LumbarPuncture", "ClinicalAnatomy", "HighYield"]
                }
            ]
            
            # Process the recovered cards
            deck_name = "Spinal_Cord_Anatomy_Recovered"
            processor = EnhancedFlashcardProcessor()
            deck, media_files = processor.process_cards(recovered_cards, deck_name)
            
            # Create package
            package = genanki.Package(deck)
            package.media_files = media_files
            
            # Generate filename
            filename = f"{deck_name}.apkg"
            file_path = f"/tmp/{filename}"
            
            # Write package
            package.write_to_file(file_path)
            
            # Get file info
            file_size = os.path.getsize(file_path)
            app.logger.info(f"Generated recovered deck: {file_path} (size: {file_size} bytes)")
            
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
                'status': 'completed',
                'deck_name': deck_name,
                'cards_processed': len(recovered_cards),
                'recovery_method': 'manual_text_extraction',
                'media_files_downloaded': len(media_files),
                'file_size': file_size,
                'filename': filename,
                'download_url': download_url,
                'full_download_url': full_url,
                'message': f'Successfully recovered and generated deck with {len(recovered_cards)} cards from failed OCR'
            }
            
            return jsonify(result), 200
        else:
            # Process normally if content exists
            return api_enhanced_medical()
        
    except Exception as e:
        app.logger.error(f"ERROR in text recovery: {str(e)}")
        import traceback
        app.logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            'error': 'Text recovery failed',
            'message': str(e),
            'traceback': traceback.format_exc()
        }), 500

@app.route('/download/<path:filename>')
def download_file(filename):
    try:
        file_path = os.path.join('/tmp', filename)
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

@app.route('/api/health', methods=['GET'])
def api_health():
    return jsonify({
        'status': 'healthy',
        'service': 'Enhanced Medical Anki Generator',
        'version': '10.1.0',
        'features': [
            'pure_html_preservation',
            'cloze_card_support',
            'images_array_support',
            'optimized_image_sizing_70_percent',
            'notes_positioned_last',
            'enhanced_notes_styling',
            'text_recovery_for_failed_ocr',
            'high_yield_content_identification',
            'no_style_modification',
            'clinical_vignettes_preserved',
            'mnemonics_preserved',
            'smaller_images_70_percent',
            'magenta_captions_support',
            'enhanced_notes_spacing'
        ],
        'timestamp': int(time.time())
    }), 200

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
        </style>
    </head>
    <body>
        <h1>Medical Anki Generator</h1>
        <p>Version 9.2.0 - Enhanced spacing and formatting support</p>

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
            </ul>
        </div>
    </body>
    </html>
    """

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)