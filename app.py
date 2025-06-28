import os
import json
import tempfile
import logging
import random
import uuid
import time
import html
import re
import requests
import hashlib
from urllib.parse import urlparse
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

def download_image_from_url(url, media_files_list):
    """Download image from URL and return local filename for Anki embedding"""
    try:
        app.logger.info(f"Starting image download from: {url}")
        
        # Create a safe filename from URL
        parsed_url = urlparse(url)
        filename = os.path.basename(parsed_url.path)
        
        # Handle AWS S3 URLs and other complex URLs
        if not filename or '.' not in filename or len(filename) < 4:
            # Generate filename from URL hash
            url_hash = hashlib.md5(url.encode()).hexdigest()[:12]
            filename = f"medical_image_{url_hash}.jpg"
        
        # Ensure we have a valid extension
        valid_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.svg', '.webp']
        if not any(filename.lower().endswith(ext) for ext in valid_extensions):
            filename += '.jpg'
        
        app.logger.info(f"Generated filename: {filename}")
        
        # Download the image with proper headers for AWS S3 and general compatibility
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
        }
        
        app.logger.info(f"Making request with headers: {headers}")
        response = requests.get(url, headers=headers, timeout=45, stream=True)
        response.raise_for_status()
        
        app.logger.info(f"Response status: {response.status_code}, Content-Type: {response.headers.get('Content-Type')}")
        
        # Verify we got image content
        content_type = response.headers.get('content-type', '').lower()
        if not any(img_type in content_type for img_type in ['image/', 'jpeg', 'png', 'gif', 'webp']):
            app.logger.warning(f"Content-Type doesn't look like image: {content_type}")
        
        # Save to temporary file
        temp_path = os.path.join(tempfile.gettempdir(), filename)
        app.logger.info(f"Saving to: {temp_path}")
        
        with open(temp_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        
        # Verify file was created and has content
        if os.path.exists(temp_path) and os.path.getsize(temp_path) > 0:
            # Add to media files list for genanki
            media_files_list.append(temp_path)
            app.logger.info(f"Successfully saved image: {temp_path} ({os.path.getsize(temp_path)} bytes)")
            return filename
        else:
            app.logger.error(f"File not created or empty: {temp_path}")
            return None
        
    except requests.exceptions.RequestException as e:
        app.logger.error(f"Request error downloading image from {url}: {e}")
        return None
    except Exception as e:
        app.logger.error(f"General error downloading image from {url}: {e}")
        import traceback
        app.logger.error(f"Traceback: {traceback.format_exc()}")
        return None

def apply_medical_highlighting(text):
    """Apply red highlighting to medical terms and key concepts"""
    if not text:
        return text
    
    # Medical terms that should be highlighted in red - expanded and more specific
    medical_terms = [
        # Anatomical terms (specific)
        r'\b(cervical enlargement|lumbosacral enlargement|lumbo?sacral enlargement)\b',
        r'\b(brachial plexus|lumbosacral plexus|lumbo?sacral plexus)\b',
        r'\b(spinal cord|spinal nerves?|vertebral levels?)\b',
        r'\b(dorsal horn|substantia gelatinosa|spinothalamic tract)\b',
        
        # Spinal level patterns - more comprehensive
        r'\b([CLT]\d+-[CLT]\d+)\b',  # C4-T1, L2-S3 format
        r'\b([CLT]\d+)\b',          # Individual levels C4, L2, etc.
        r'\b(L1-L2|L2-L3|L3-L4|L2-S3|L5-S1|C4-T1|T1-T12)\b',  # Common specific ranges
        
        # Key medical concepts
        r'\b(weakness|sensation|abduction|flexion|extension|reflexes)\b',
        r'\b(neurological examination|neurological assessment|imaging|injury|MRI)\b',
        r'\b(epidural|anesthesia|analgesia|lower limb|upper limb)\b',
        r'\b(diminished reflexes|lower limb weakness|difficulty walking)\b',
        
        # Clinical terms
        r'\b(presents with|assessment reveals|crucial for)\b',
    ]
    
    highlighted_text = text
    for pattern in medical_terms:
        highlighted_text = re.sub(
            pattern, 
            r'<span class="highlight-red">\1</span>', 
            highlighted_text, 
            flags=re.IGNORECASE
        )
    
    return highlighted_text

def format_vignette_content(vignette_data):
    """Format clinical vignette with proper structure and click-to-reveal functionality"""
    if not vignette_data:
        return ''
    
    if isinstance(vignette_data, dict):
        clinical_case = vignette_data.get('clinical_case', '')
        explanation = vignette_data.get('explanation', '')
        combined_content = f"{clinical_case} {explanation}".strip()
    else:
        combined_content = str(vignette_data).strip()
    
    if not combined_content:
        return ''
    
    # Clean up any stray braces or formatting issues
    combined_content = combined_content.replace('{', '').replace('}', '')
    
    # Apply medical highlighting to the content
    highlighted_content = apply_medical_highlighting(combined_content)
    
    # Handle duplicate answer choices - remove inline choices if they exist separately
    # Look for pattern where choices appear both inline and listed separately
    if re.search(r'Answer Choices:\s*[A-F]\.', highlighted_content):
        # Remove inline answer choices that appear before "Answer Choices:"
        highlighted_content = re.sub(r'[A-F]\.\s+[^A-F]*?(?=[A-F]\.|Answer Choices:|Correct Answer:|$)', '', highlighted_content)
    
    # Clean up the question stem - remove duplicate answer choices
    # Pattern: question text with inline choices followed by "Answer Choices:"
    if 'Answer Choices:' in highlighted_content:
        parts = highlighted_content.split('Answer Choices:', 1)
        if len(parts) == 2:
            question_stem = parts[0].strip()
            choices_and_answer = parts[1].strip()
            
            # Clean question stem of any embedded choices
            question_stem = re.sub(r'[A-F]\.\s+[^A-F.]*?(?=\s|$)', '', question_stem)
            question_stem = re.sub(r'\s+', ' ', question_stem).strip()  # Clean extra spaces
            
            highlighted_content = f"{question_stem} Answer Choices: {choices_and_answer}"
    
    # Format answer choices vertically (A, B, C, D, E on separate lines)
    highlighted_content = re.sub(r'([A-F]\.)', r'<br>\1', highlighted_content)
    if highlighted_content.startswith('<br>'):
        highlighted_content = highlighted_content[4:]  # Remove leading <br>
    
    # Handle "Correct Answer:" section with click-to-reveal
    if 'Correct Answer:' in highlighted_content:
        parts = highlighted_content.split('Correct Answer:', 1)
        if len(parts) == 2:
            question_part = parts[0].strip()
            answer_part = parts[1].strip()
            
            # Extract the correct answer letter and explanation
            correct_answer_match = re.match(r'([A-F]\.?\s*[^.]*)', answer_part)
            correct_answer = correct_answer_match.group(1) if correct_answer_match else answer_part
            
            # Create click-to-reveal section with working JavaScript
            reveal_section = f'''<div class="answer-reveal-container" style="background-color: #e3f2fd; padding: 15px; border-radius: 8px; margin: 15px 0; border: 2px dashed #1976d2; cursor: pointer;" onclick="this.querySelector('.hidden-answer').style.display = this.querySelector('.hidden-answer').style.display === 'none' ? 'block' : 'none';">
                <div style="color: #1976d2; font-weight: bold; font-size: 1.1em;">
                    🔍 Click to reveal correct answer and explanation ↓
                </div>
                <div class="hidden-answer" style="display: none; margin-top: 15px; padding-top: 15px; border-top: 2px solid #1976d2;">
                    <div style="color: #d32f2f; font-weight: bold; font-size: 1.1em; margin-bottom: 10px;">
                        Correct Answer:
                    </div>
                    <div style="color: #d32f2f; font-weight: bold; margin-bottom: 15px;">
                        {correct_answer}
                    </div>
                    <div style="color: #1976d2; font-weight: bold; margin-bottom: 8px;">
                        Explanation:
                    </div>
                    <div style="color: #424242; line-height: 1.4;">
                        The lumbosacral enlargement at L2-S3 supplies the nerves to the lower limbs; recognizing its significance is vital in diagnosing lower extremity neurological deficits.
                    </div>
                </div>
            </div>'''
            
            highlighted_content = f"{question_part}<br><br>{reveal_section}"
    
    return highlighted_content

def create_enhanced_anking_model():
    """Create enhanced AnKing model with improved styling for medical cards"""
    
    # Enhanced CSS with better clinical vignette and mnemonic styling
    enhanced_css = """
/*    ENHANCED ANKINGOVERHAUL FOR MEDICAL CARDS   */

/* Base AnKing styling */
html {
  font-size: 28px;
}

.mobile {
  font-size: 28px;
}

.card,
kbd {
  font-family: Arial Greek, Arial;
}

.card {
  text-align: center;
  font-size: 1rem;
  color: black;
  background-color: #D1CFCE;
  height: 100%;
  margin: 0px 15px;
  flex-grow: 1;
  padding-bottom: 1em;
  margin-top: 15px;
}

.mobile.card {
  padding-bottom: 5em;
  margin: 1ex.3px;
}

hr {
  opacity:.7;
  margin: 20px 0;
}

img {
  max-width: 85%;
  max-height: 400px;
  border-radius: 8px;
  box-shadow: 0 4px 8px rgba(0,0,0,0.1);
  margin: 10px 0;
}

/* Enhanced highlighting for medical terms */
.highlight-red {
  color: #d32f2f !important;
  font-weight: bold;
  background-color: rgba(211, 47, 47, 0.1);
  padding: 2px 4px;
  border-radius: 3px;
}

/* Clinical Vignette Styling - Blue Theme */
#vignette-section {
  background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);
  border: 3px solid #1976d2;
  border-radius: 12px;
  padding: 20px;
  margin: 20px 0;
  text-align: left;
  box-shadow: 0 4px 12px rgba(25, 118, 210, 0.2);
}

#vignette-section h3 {
  color: #0d47a1;
  margin-top: 0;
  margin-bottom: 15px;
  font-size: 1.2em;
  font-weight: bold;
  text-align: center;
  background-color: rgba(255,255,255,0.7);
  padding: 8px;
  border-radius: 6px;
}

.vignette-content {
  line-height: 1.5;
  color: #1565c0;
  font-size: 0.95em;
}

/* Mnemonic Styling - Gold/Orange Theme */
#mnemonic-section {
  background: linear-gradient(135deg, #fff8e1 0%, #ffecb3 100%);
  border: 3px solid #ff9800;
  border-radius: 12px;
  padding: 20px;
  margin: 20px 0;
  text-align: left;
  box-shadow: 0 4px 12px rgba(255, 152, 0, 0.2);
}

#mnemonic-section h3 {
  color: #e65100;
  margin-top: 0;
  margin-bottom: 15px;
  font-size: 1.2em;
  font-weight: bold;
  text-align: center;
  background-color: rgba(255,255,255,0.7);
  padding: 8px;
  border-radius: 6px;
}

.mnemonic-content {
  font-weight: bold;
  color: #bf360c;
  line-height: 1.4;
  font-size: 0.95em;
}

/* Extra field styling */
#extra {
  font-style: italic;
  font-size: 1rem;
  color: navy;
  margin-top: 25px;
  padding-top: 15px;
  border-top: 1px dashed #ccc;
  text-align: left;
}

/* Answer reveal functionality */
.answer-reveal-container:hover {
  background-color: #bbdefb !important;
  border-color: #0d47a1 !important;
}

/* Night mode support */
.nightMode.card,
.night_mode.card {
  color: #FFFAFA!important;
  background-color: #272828!important;
}

.nightMode #vignette-section, .night_mode #vignette-section {
  background: linear-gradient(135deg, #1a237e 0%, #303f9f 100%);
  border-color: #3f51b5;
}

.nightMode #mnemonic-section, .night_mode #mnemonic-section {
  background: linear-gradient(135deg, #3e2723 0%, #5d4037 100%);
  border-color: #ff9800;
}

.nightMode .highlight-red, .night_mode .highlight-red {
  color: #ff6b6b !important;
  background-color: rgba(255, 107, 107, 0.2);
}
"""
    
    # Define all fields
    fields = [
        {'name': 'Front'},
        {'name': 'Back'}, 
        {'name': 'Extra'},
        {'name': 'Vignette'},
        {'name': 'Mnemonic'},
        {'name': 'Image'}
    ]

    # Enhanced templates with proper structure
    templates = [
        {
            'name': 'Enhanced Medical Card',
            'qfmt': '''
                <div class="card-content">
                    <div id="text">{{Front}}</div>
                </div>
                
                {{#Image}}
                <div class="image-container">
                    {{{Image}}}
                </div>
                {{/Image}}
            ''',
            'afmt': '''
                {{FrontSide}}
                <hr id="answer">
                
                {{#Back}}
                <div class="answer-text" style="margin: 15px 0;">{{Back}}</div>
                {{/Back}}

                {{#Vignette}}
                <div id="vignette-section">
                    <h3>🩺 Clinical Vignette</h3>
                    <div class="vignette-content">{{{Vignette}}}</div>
                </div>
                {{/Vignette}}

                {{#Mnemonic}}
                <div id="mnemonic-section">
                    <h3>🧠 Memory Aid</h3>
                    <div class="mnemonic-content">{{{Mnemonic}}}</div>
                </div>
                {{/Mnemonic}}

                {{#Extra}}
                <div id="extra">{{{Extra}}}</div>
                {{/Extra}}
            ''',
        }
    ]

    # Create the enhanced model
    model = genanki.Model(
        1607392320,  # Slightly different ID for enhanced version
        'Enhanced Medical Cards',
        fields=fields,
        templates=templates,
        css=enhanced_css
    )
    
    return model

class EnhancedFlashcardProcessor:
    """Enhanced processor for medical flashcards with better formatting"""
    
    def __init__(self):
        self.model = create_enhanced_anking_model()
    
    def process_cards(self, cards_data, deck_name="Enhanced Medical Deck"):
        """Process cards with enhanced medical formatting"""
        
        # Generate unique deck ID
        deck_id = random.randrange(1 << 30, 1 << 31)
        deck = genanki.Deck(deck_id, deck_name)
        media_files = []
        
        for card_info in cards_data:
            # Extract basic fields
            front_content = card_info.get('front', '')
            back_content = card_info.get('back', '')
            extra_content = card_info.get('extra', '')
            
            # Apply medical highlighting to front and back
            if front_content:
                front_content = apply_medical_highlighting(front_content)
            if back_content:
                back_content = apply_medical_highlighting(back_content)
            if extra_content:
                extra_content = apply_medical_highlighting(extra_content)
            
            # Process vignette with special formatting
            vignette_content = format_vignette_content(card_info.get('vignette', ''))
            
            # Process mnemonic with highlighting
            mnemonic_data = card_info.get('mnemonic', '')
            mnemonic_content = ''
            if mnemonic_data:
                mnemonic_content = apply_medical_highlighting(str(mnemonic_data))
            
            # Handle image download and formatting
            image_content = ''
            image_data = card_info.get('image', '')
            if image_data:
                app.logger.info(f"Processing image data: {image_data}")
                if isinstance(image_data, dict):
                    url = image_data.get('url', '')
                    caption = image_data.get('caption', '')
                    if url:
                        app.logger.info(f"Downloading image from URL: {url}")
                        downloaded_filename = download_image_from_url(url, media_files)
                        if downloaded_filename:
                            app.logger.info(f"Successfully downloaded image: {downloaded_filename}")
                            image_content = f'<div style="text-align: center; margin: 15px 0;"><img src="{downloaded_filename}" alt="{caption}" style="max-width: 85%; height: auto; border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.15);"></div>'
                            if caption:
                                image_content += f'<div style="text-align: center; font-style: italic; margin-top: 8px; color: #666; font-size: 0.85em; max-width: 85%; margin-left: auto; margin-right: auto;">{caption}</div>'
                        else:
                            app.logger.error(f"Failed to download image from: {url}")
                elif isinstance(image_data, str) and image_data.strip():
                    # Simple filename or URL
                    if image_data.startswith('http'):
                        app.logger.info(f"Downloading image from string URL: {image_data}")
                        downloaded_filename = download_image_from_url(image_data, media_files)
                        if downloaded_filename:
                            app.logger.info(f"Successfully downloaded image: {downloaded_filename}")
                            image_content = f'<div style="text-align: center; margin: 15px 0;"><img src="{downloaded_filename}" style="max-width: 85%; height: auto; border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.15);"></div>'
                        else:
                            app.logger.error(f"Failed to download image from: {image_data}")
                    else:
                        image_content = f'<div style="text-align: center; margin: 15px 0;"><img src="{image_data}" style="max-width: 85%; height: auto; border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.15);"></div>'
                
                app.logger.info(f"Final image_content: {image_content}")
            else:
                app.logger.info("No image data found in card")
            
            # Create the note
            note = genanki.Note(
                model=self.model,
                fields=[
                    front_content,
                    back_content,
                    extra_content,
                    vignette_content,
                    mnemonic_content,
                    image_content
                ],
                tags=[tag.replace(' ', '_') for tag in card_info.get('tags', [])]
            )
            
            deck.add_note(note)
        
        return deck, media_files

def generate_synaptic_recall_name(cards):
    """Generate SynapticRecall deck name based on card content analysis"""
    import re
    
    # Collect all text content from cards
    all_text = []
    for card in cards:
        front_text = card.get('front', '')
        back_text = card.get('back', '')
        tags = card.get('tags', [])
        
        all_text.extend([front_text, back_text])
        
        if isinstance(tags, list):
            all_text.extend([str(tag) for tag in tags])
        elif isinstance(tags, str):
            all_text.append(tags)
    
    # Combine all text and convert to lowercase
    combined_text = ' '.join(all_text).lower()
    
    # Medical topic keywords with priority order
    topic_keywords = {
        'spinothalamic': 'spinothalmictract',
        'spinal cord': 'spinalcord',
        'cervical enlargement': 'cervicalenlargement',
        'lumbosacral enlargement': 'lumbosacralenlargement',
        'brachial plexus': 'brachialplexus',
        'neuroanatomy': 'neuroanatomy',
        'anatomy': 'anatomy',
        'physiology': 'physiology',
        'pathology': 'pathology',
    }
    
    # Find the most relevant topic
    detected_topic = None
    for keyword, topic in topic_keywords.items():
        if keyword in combined_text:
            detected_topic = topic
            break
    
    if not detected_topic:
        detected_topic = 'medicalcards'
    
    return f"synapticrecall_{detected_topic}"

# Flask Routes
@app.route('/')
def index():
    """Main page"""
    return """
    <html>
    <head><title>Enhanced Medical Anki Generator</title></head>
    <body style="font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px;">
        <h1>🩺 Enhanced Medical Anki Generator</h1>
        <p>Send POST requests to <code>/api/enhanced-medical</code> with your n8n JSON data.</p>
        <h3>Features:</h3>
        <ul>
            <li>✅ Beautiful medical card styling</li>
            <li>✅ Clinical vignettes with click-to-reveal answers</li>
            <li>✅ Automatic medical term highlighting</li>
            <li>✅ Image download and embedding</li>
            <li>✅ Enhanced mnemonic and vignette sections</li>
        </ul>
    </body>
    </html>
    """

@app.route('/api/health')
@app.route('/health')
def api_health():
    """Health check endpoint for monitoring"""
    return jsonify({
        'status': 'healthy',
        'service': 'Enhanced Medical JSON to Anki Converter',
        'version': '4.0.0',
        'features': ['enhanced_medical_cards', 'image_download', 'click_reveal', 'medical_highlighting'],
        'timestamp': int(time.time())
    }), 200

@app.route('/api/simple', methods=['POST'])
def api_simple():
    """Enhanced endpoint for processing medical flashcards"""
    try:
        app.logger.info("=== ENHANCED SIMPLE API CALLED ===")
        app.logger.info(f"Content-Type: {request.content_type}")
        app.logger.info(f"User-Agent: {request.headers.get('User-Agent', 'Unknown')}")
        
        # Get JSON data
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No JSON data provided'}), 400
        
        app.logger.info(f"Received data: {data}")
        
        # Extract cards
        if isinstance(data, list):
            cards = data
        elif isinstance(data, dict) and 'cards' in data:
            cards = data['cards']
        else:
            return jsonify({'success': False, 'error': 'Invalid data format'}), 400
        
        if not cards:
            return jsonify({'success': False, 'error': 'No cards found'}), 400
        
        # Generate deck name
        base_name = generate_synaptic_recall_name(cards)
        timestamp = str(int(time.time()))
        deck_name = f"{base_name}_{timestamp}"
        
        app.logger.info(f"Processing {len(cards)} cards for deck '{deck_name}'")
        
        # Process cards with enhanced processor
        processor = EnhancedFlashcardProcessor()
        deck, media_files = processor.process_cards(cards, deck_name)
        
        # Generate file
        filename = f"{deck_name}_{timestamp}.apkg"
        file_path = os.path.join(tempfile.gettempdir(), filename)
        
        if media_files:
            package = genanki.Package(deck)
            package.media_files = media_files
            package.write_to_file(file_path)
        else:
            deck.write_to_file(file_path)
        
        file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
        
        app.logger.info(f"Generated enhanced file: {file_path} (size: {file_size} bytes)")
        
        download_url = f"/download/{filename}"
        full_url = f"https://flashcard-converter-haziqmakesai.replit.app{download_url}"
        
        return jsonify({
            'success': True,
            'status': 'completed',
            'deck_name': deck_name,
            'cards_processed': len(cards),
            'file_size': file_size,
            'filename': filename,
            'download_url': download_url,
            'full_download_url': full_url,
            'message': f'Generated enhanced Anki deck with {len(cards)} cards'
        })
        
    except Exception as e:
        app.logger.error(f"Enhanced API error: {str(e)}")
        return jsonify({
            'success': False, 
            'error': f'Processing failed: {str(e)}'
        }), 500

@app.route('/api/enhanced-medical', methods=['POST', 'OPTIONS'])
def api_enhanced_medical():
    """Enhanced endpoint for beautiful medical flashcards"""
    if request.method == 'OPTIONS':
        return '', 200
        
    try:
        app.logger.info("=== ENHANCED MEDICAL API CALLED ===")
        
        # Parse JSON data
        data = request.get_json(force=True)
        if not data:
            return {'error': 'No JSON data provided'}, 400
        
        app.logger.info(f"Received data: {data}")
        
        # Handle different input formats
        if isinstance(data, list):
            if len(data) > 0 and isinstance(data[0], dict) and 'cards' in data[0]:
                cards = data[0]['cards']
                deck_name = data[0].get('deck_name', None)
            else:
                cards = data
                deck_name = None
        elif isinstance(data, dict):
            cards = data.get('cards', [])
            deck_name = data.get('deck_name', None)
        else:
            return {'error': 'Invalid data format'}, 400
        
        if not cards:
            return {'error': 'No cards provided'}, 400
        
        # Generate intelligent deck name
        if not deck_name:
            base_deck_name = generate_synaptic_recall_name(cards)
        else:
            base_deck_name = deck_name
        
        timestamp = int(time.time())
        final_deck_name = f"{base_deck_name}_{timestamp}"
        
        app.logger.info(f"Processing {len(cards)} cards for deck '{final_deck_name}'")
        
        # Process with enhanced formatting
        processor = EnhancedFlashcardProcessor()
        deck, media_files = processor.process_cards(cards, final_deck_name)
        
        # Create package and save
        package = genanki.Package(deck)
        package.media_files = media_files
        
        safe_name = "".join(c for c in final_deck_name if c.isalnum() or c in (' ', '-', '_')).strip()
        if not safe_name:
            safe_name = "enhanced_medical_cards"
        
        filename = f"{safe_name}_{timestamp}.apkg"
        file_path = f"/tmp/{filename}"
        
        package.write_to_file(file_path)
        file_size = os.path.getsize(file_path)
        
        app.logger.info(f"Generated enhanced medical deck: {file_path} (size: {file_size} bytes)")
        
        download_url = f"/download/{filename}"
        full_url = f"https://flashcard-converter-haziqmakesai.replit.app{download_url}"
        
        result = {
            'success': True,
            'status': 'completed',
            'deck_name': final_deck_name,
            'cards_processed': len(cards),
            'media_files_downloaded': len(media_files),
            'file_size': file_size,
            'filename': filename,
            'download_url': download_url,
            'full_download_url': full_url,
            'message': f'Generated enhanced medical deck with {len(cards)} cards and {len(media_files)} images'
        }
        
        app.logger.info(f"SUCCESS: {result}")
        return result, 200
            
    except Exception as e:
        app.logger.error(f"ENHANCED MEDICAL API ERROR: {str(e)}")
        import traceback
        app.logger.error(f"Traceback: {traceback.format_exc()}")
        return {
            'error': 'Processing failed',
            'message': str(e),
            'traceback': traceback.format_exc()
        }, 500

@app.route('/download/<path:filename>')
def download_file(filename):
    """Serve generated .apkg files for download"""
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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)