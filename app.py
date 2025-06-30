import os
import json
import html
import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional
from flask import Flask, request, send_file, jsonify, render_template_string
from flask_cors import CORS
import genanki
import random
import tempfile

# Create directories
os.makedirs("temp", exist_ok=True)
os.makedirs("static", exist_ok=True)
os.makedirs("templates", exist_ok=True)

# Create Flask app for compatibility with existing gunicorn setup
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

# Enhanced Medical Anki Generator
class MedicalAnkiGenerator:
    def __init__(self):
        self.medical_model = self._create_medical_model()
    
    def _create_medical_model(self):
        return genanki.Model(
            1607392319,
            'Medical Flashcard Model v6.0',
            fields=[
                {'name': 'Clinical_Vignette'},
                {'name': 'Question'},
                {'name': 'Answer'},
                {'name': 'Explanation'},
                {'name': 'Tags'},
                {'name': 'Images'},
                {'name': 'Mnemonics'}
            ],
            templates=[
                {
                    'name': 'Medical Card',
                    'qfmt': '''
                        <div class="card">
                            {{#Clinical_Vignette}}
                            <div class="clinical-vignette">{{{Clinical_Vignette}}}</div>
                            {{/Clinical_Vignette}}
                            <div class="question">{{{Question}}}</div>
                            {{#Images}}<div class="image-container">{{{Images}}}</div>{{/Images}}
                        </div>
                    ''',
                    'afmt': '''
                        {{FrontSide}}
                        <hr id="answer">
                        <div class="answer">{{{Answer}}}</div>
                        {{#Explanation}}<div class="explanation">{{{Explanation}}}</div>{{/Explanation}}
                        {{#Mnemonics}}<div class="mnemonic">{{{Mnemonics}}}</div>{{/Mnemonics}}
                        <div class="tags">{{Tags}}</div>
                    '''
                }
            ],
            css='''
                .card {
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, "Helvetica Neue", Arial, sans-serif;
                    font-size: 18px;
                    line-height: 1.6;
                    color: #333;
                    background-color: #fff;
                    padding: 20px;
                    max-width: 800px;
                    margin: 0 auto;
                }
                
                .clinical-vignette {
                    background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
                    border-left: 4px solid #007bff;
                    padding: 20px;
                    margin-bottom: 20px;
                    border-radius: 8px;
                    box-shadow: 0 2px 8px rgba(0,123,255,0.1);
                }
                
                .question {
                    font-weight: bold;
                    font-size: 20px;
                    margin-bottom: 15px;
                    color: #2c3e50;
                    background: #f8f9fa;
                    padding: 15px;
                    border-radius: 8px;
                    border-left: 4px solid #17a2b8;
                }
                
                .answer {
                    background: linear-gradient(135deg, #e8f5e8 0%, #d4edda 100%);
                    padding: 20px;
                    border-radius: 8px;
                    margin-bottom: 15px;
                    border-left: 4px solid #28a745;
                    box-shadow: 0 2px 8px rgba(40,167,69,0.1);
                }
                
                .explanation {
                    background: linear-gradient(135deg, #fff3cd 0%, #ffeaa7 100%);
                    border: 1px solid #ffc107;
                    padding: 20px;
                    border-radius: 8px;
                    margin-bottom: 15px;
                    box-shadow: 0 2px 8px rgba(255,193,7,0.1);
                }
                
                .mnemonic {
                    background: linear-gradient(135deg, #e1f5fe 0%, #b3e5fc 100%);
                    border-left: 4px solid #29b6f6;
                    padding: 20px;
                    font-style: italic;
                    border-radius: 8px;
                    margin-bottom: 15px;
                    box-shadow: 0 2px 8px rgba(41,182,246,0.1);
                }
                
                .image-container {
                    text-align: center;
                    margin: 20px 0;
                }
                
                .image-container img {
                    max-width: 100% !important;
                    height: auto !important;
                    border-radius: 8px;
                    box-shadow: 0 4px 16px rgba(0,0,0,0.15);
                }
                
                .tags {
                    font-size: 14px;
                    color: #666;
                    margin-top: 20px;
                    padding: 10px;
                    background: #f8f9fa;
                    border-radius: 8px;
                }
                
                /* Night mode support */
                .nightMode .card {
                    background-color: #2c2c2c;
                    color: #e0e0e0;
                }
                
                .nightMode .clinical-vignette {
                    background: linear-gradient(135deg, #3a3a3a 0%, #4a4a4a 100%);
                    border-left-color: #5dade2;
                }
                
                .nightMode .question {
                    background: #3a3a3a;
                    border-left-color: #17a2b8;
                    color: #e0e0e0;
                }
                
                .nightMode .answer {
                    background: linear-gradient(135deg, #2e4a2e 0%, #3a5a3a 100%);
                    border-left-color: #28a745;
                }
                
                .nightMode .explanation {
                    background: linear-gradient(135deg, #4a3d1f 0%, #5a4a2f 100%);
                    border-color: #ffc107;
                }
                
                .nightMode .mnemonic {
                    background: linear-gradient(135deg, #1f3a4a 0%, #2f4a5a 100%);
                    border-left-color: #29b6f6;
                }
                
                .nightMode .tags {
                    background: #3a3a3a;
                    color: #b0b0b0;
                }
            '''
        )
    
    def generate_deck(self, deck_name: str, cards_data: List[Dict]) -> str:
        # Create deck with unique ID
        deck_id = abs(hash(deck_name + str(datetime.now()))) % (10**9)
        deck = genanki.Deck(deck_id, deck_name)
        
        # Process cards
        for card_data in cards_data:
            # Handle raw HTML data - preserve HTML formatting
            clinical_vignette = str(card_data.get('clinical_vignette', '')).strip()
            front = str(card_data.get('front', '')).strip()
            back = str(card_data.get('back', '')).strip()
            explanation = str(card_data.get('explanation', '')).strip()
            mnemonic = str(card_data.get('mnemonic', '')).strip()
            
            # Also handle raw_html field for complete HTML content
            raw_html = str(card_data.get('raw_html', '')).strip()
            if raw_html:
                # If raw HTML is provided, use it as the primary content
                front = raw_html if not front else front
            
            # Handle tags
            tags = card_data.get('tags', [])
            if isinstance(tags, str):
                tags = [tag.strip() for tag in tags.split(',') if tag.strip()]
            
            # Format images - preserve existing image HTML
            images_html = ""
            images = card_data.get('images', [])
            if images:
                if isinstance(images, str):
                    images_html = images  # Already formatted HTML
                else:
                    images_html = "".join([f'<img src="{img}" alt="Medical Image">' for img in images])
            
            # Create note with preserved HTML formatting
            note = genanki.Note(
                model=self.medical_model,
                fields=[
                    clinical_vignette,
                    front,
                    back,
                    explanation,
                    ", ".join(tags) if tags else "",
                    images_html,
                    mnemonic
                ],
                tags=[tag.replace(' ', '_').replace(':', '_') for tag in tags] if tags else []
            )
            deck.add_note(note)
        
        # Generate filename and save
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{deck_name.replace(' ', '_')}_{timestamp}.apkg"
        filepath = os.path.join("temp", filename)
        
        package = genanki.Package(deck)
        package.write_to_file(filepath)
        
        return filename

# Initialize generator
anki_generator = MedicalAnkiGenerator()

# HTML template for the enhanced UI
HTML_TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Enhanced Medical Flashcard Generator</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        .gradient-bg { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
        .card-preview { background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%); }
        .animate-pulse-slow { animation: pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite; }
    </style>
</head>
<body class="min-h-screen bg-gray-50">
    <div class="max-w-7xl mx-auto px-4 py-8">
        <!-- Header -->
        <header class="mb-8 text-center">
            <div class="gradient-bg rounded-2xl p-8 text-white">
                <h1 class="text-4xl font-bold mb-4">
                    <i class="fas fa-stethoscope mr-3"></i>
                    Enhanced Medical Flashcard Generator
                </h1>
                <p class="text-xl opacity-90">Create beautiful Anki flashcards with advanced medical formatting</p>
                <div class="mt-4 text-sm opacity-75">
                    <span class="bg-white bg-opacity-20 px-3 py-1 rounded-full mr-2">Version 6.0</span>
                    <span class="bg-white bg-opacity-20 px-3 py-1 rounded-full mr-2">n8n Compatible</span>
                    <span class="bg-white bg-opacity-20 px-3 py-1 rounded-full">Medical Focused</span>
                </div>
            </div>
        </header>

        <!-- Main Content -->
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
            <!-- Input Section -->
            <div class="bg-white rounded-xl shadow-lg p-6">
                <h2 class="text-2xl font-semibold mb-6 flex items-center text-gray-800">
                    <i class="fas fa-edit mr-3 text-blue-600"></i>
                    Create Medical Flashcard
                </h2>
                
                <form id="flashcardForm" class="space-y-6">
                    <div>
                        <label class="block text-sm font-medium text-gray-700 mb-2">
                            <i class="fas fa-hospital mr-1 text-blue-500"></i>
                            Clinical Vignette (Optional)
                        </label>
                        <textarea id="vignette" rows="3" class="w-full p-4 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition" placeholder="A 65-year-old male presents with acute chest pain radiating to the left arm..."></textarea>
                    </div>
                    
                    <div>
                        <label class="block text-sm font-medium text-gray-700 mb-2">
                            <i class="fas fa-question-circle mr-1 text-green-500"></i>
                            Question <span class="text-red-500">*</span>
                        </label>
                        <textarea id="question" rows="2" required class="w-full p-4 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition" placeholder="What is the most likely diagnosis?"></textarea>
                    </div>
                    
                    <div>
                        <label class="block text-sm font-medium text-gray-700 mb-2">
                            <i class="fas fa-check-circle mr-1 text-green-500"></i>
                            Answer <span class="text-red-500">*</span>
                        </label>
                        <textarea id="answer" rows="2" required class="w-full p-4 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition" placeholder="ST-elevation myocardial infarction (STEMI)"></textarea>
                    </div>
                    
                    <div>
                        <label class="block text-sm font-medium text-gray-700 mb-2">
                            <i class="fas fa-lightbulb mr-1 text-yellow-500"></i>
                            Explanation
                        </label>
                        <textarea id="explanation" rows="3" class="w-full p-4 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition" placeholder="The combination of chest pain, ECG changes, and elevated troponins indicates..."></textarea>
                    </div>
                    
                    <div>
                        <label class="block text-sm font-medium text-gray-700 mb-2">
                            <i class="fas fa-brain mr-1 text-purple-500"></i>
                            Mnemonic
                        </label>
                        <input type="text" id="mnemonic" class="w-full p-4 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition" placeholder="STEMI = ST-elevation Teaches Emergency Medicine Importance">
                    </div>
                    
                    <div>
                        <label class="block text-sm font-medium text-gray-700 mb-2">
                            <i class="fas fa-tag mr-1 text-indigo-500"></i>
                            Tags (comma-separated)
                        </label>
                        <input type="text" id="tags" class="w-full p-4 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition" placeholder="cardiology, emergency, ECG, STEMI">
                    </div>
                    
                    <button type="submit" class="w-full bg-gradient-to-r from-blue-600 to-purple-600 text-white py-4 px-6 rounded-lg hover:from-blue-700 hover:to-purple-700 transition duration-200 font-medium text-lg shadow-lg">
                        <i class="fas fa-plus mr-2"></i>Add Medical Flashcard
                    </button>
                </form>
            </div>

            <!-- Preview and Cards Section -->
            <div class="space-y-8">
                <!-- Preview -->
                <div class="bg-white rounded-xl shadow-lg p-6">
                    <h2 class="text-2xl font-semibold mb-6 flex items-center text-gray-800">
                        <i class="fas fa-eye mr-3 text-green-600"></i>
                        Live Preview
                    </h2>
                    
                    <div id="previewCard" class="card-preview rounded-lg p-6 min-h-[200px]">
                        <div class="text-center text-gray-500 py-12 animate-pulse-slow">
                            <i class="fas fa-clipboard-list text-5xl mb-4"></i>
                            <p class="text-lg">Your medical flashcard preview will appear here</p>
                        </div>
                    </div>
                </div>

                <!-- Added Cards -->
                <div class="bg-white rounded-xl shadow-lg p-6">
                    <div class="flex justify-between items-center mb-6">
                        <h2 class="text-2xl font-semibold flex items-center text-gray-800">
                            <i class="fas fa-layer-group mr-3 text-purple-600"></i>
                            Cards (<span id="cardCount">0</span>)
                        </h2>
                        <button onclick="clearAllCards()" class="text-red-600 hover:text-red-700 font-medium">
                            <i class="fas fa-trash mr-1"></i>Clear All
                        </button>
                    </div>
                    
                    <div id="cardsList" class="space-y-3 max-h-64 overflow-y-auto">
                        <p class="text-gray-400 text-center py-8">No cards added yet</p>
                    </div>
                    
                    <button onclick="generateDeck()" id="generateBtn" disabled class="w-full mt-6 bg-gradient-to-r from-green-600 to-blue-600 text-white py-4 px-6 rounded-lg hover:from-green-700 hover:to-blue-700 transition duration-200 font-medium text-lg shadow-lg disabled:from-gray-300 disabled:to-gray-400 disabled:cursor-not-allowed">
                        <i class="fas fa-download mr-2"></i>Generate Anki Deck
                    </button>
                </div>
            </div>
        </div>

        <!-- API Documentation -->
        <div class="mt-12 bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 rounded-xl p-8">
            <h3 class="text-2xl font-semibold text-blue-900 mb-4">
                <i class="fas fa-code mr-2"></i>API Integration
            </h3>
            
            <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                    <h4 class="font-semibold text-blue-800 mb-2">n8n Webhook Endpoint</h4>
                    <code class="bg-blue-100 text-blue-900 px-4 py-2 rounded-lg block text-sm">POST /api/webhook/n8n</code>
                </div>
                
                <div>
                    <h4 class="font-semibold text-blue-800 mb-2">Enhanced Medical API</h4>
                    <code class="bg-blue-100 text-blue-900 px-4 py-2 rounded-lg block text-sm">POST /api/enhanced-medical</code>
                </div>
            </div>
            
            <details class="mt-6">
                <summary class="cursor-pointer text-blue-700 hover:text-blue-800 font-medium">
                    <i class="fas fa-chevron-right mr-1"></i>View Example Payload
                </summary>
                <pre class="mt-4 bg-blue-900 text-blue-100 p-4 rounded-lg text-sm overflow-x-auto"><code>{
  "cards": [
    {
      "front": "What is the mechanism of action of Aspirin?",
      "back": "Irreversibly inhibits COX-1 and COX-2 enzymes",
      "clinical_vignette": "A 65-year-old patient with chest pain",
      "explanation": "Aspirin prevents platelet aggregation",
      "mnemonic": "ASA = Anti-platelet Super Agent",
      "tags": ["cardiology", "pharmacology", "emergency"]
    }
  ]
}</code></pre>
            </details>
        </div>
    </div>

    <!-- Success Modal -->
    <div id="successModal" class="hidden fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div class="bg-white rounded-xl p-8 max-w-md w-full mx-4 shadow-2xl">
            <div class="text-center">
                <i class="fas fa-check-circle text-6xl text-green-600 mb-4"></i>
                <h3 class="text-2xl font-semibold mb-3">Deck Generated Successfully!</h3>
                <p class="text-gray-600 mb-6">Your enhanced medical Anki deck is ready for download.</p>
                <a id="downloadLink" href="#" class="inline-block bg-gradient-to-r from-green-600 to-blue-600 text-white py-3 px-8 rounded-lg hover:from-green-700 hover:to-blue-700 transition duration-200 font-medium shadow-lg">
                    <i class="fas fa-download mr-2"></i>Download Deck
                </a>
                <button onclick="closeModal()" class="block w-full mt-4 text-gray-600 hover:text-gray-800 py-2">
                    Close
                </button>
            </div>
        </div>
    </div>

    <script>
        let cards = [];

        // Form submission
        document.getElementById('flashcardForm').addEventListener('submit', function(e) {
            e.preventDefault();
            
            const card = {
                clinical_vignette: document.getElementById('vignette').value,
                front: document.getElementById('question').value,
                back: document.getElementById('answer').value,
                explanation: document.getElementById('explanation').value,
                mnemonic: document.getElementById('mnemonic').value,
                tags: document.getElementById('tags').value.split(',').map(tag => tag.trim()).filter(tag => tag)
            };
            
            cards.push(card);
            updateCardsList();
            updatePreview(card);
            
            // Reset form
            this.reset();
            document.getElementById('generateBtn').disabled = false;
        });

        // Update preview
        function updatePreview(card) {
            const previewDiv = document.getElementById('previewCard');
            
            let html = '<div class="space-y-4">';
            
            if (card.clinical_vignette) {
                html += `<div class="bg-blue-50 border-l-4 border-blue-400 p-4 rounded">${escapeHtml(card.clinical_vignette)}</div>`;
            }
            
            html += `
                <div class="font-semibold text-xl text-gray-800 bg-gray-50 p-4 rounded">${escapeHtml(card.front)}</div>
                <div class="border-t-2 pt-4">
                    <div class="bg-green-50 border-l-4 border-green-400 p-4 rounded text-green-800">${escapeHtml(card.back)}</div>
                </div>
            `;
            
            if (card.explanation) {
                html += `<div class="bg-yellow-50 border-l-4 border-yellow-400 p-4 rounded">${escapeHtml(card.explanation)}</div>`;
            }
            
            if (card.mnemonic) {
                html += `<div class="bg-purple-50 border-l-4 border-purple-400 p-4 rounded italic">${escapeHtml(card.mnemonic)}</div>`;
            }
            
            if (card.tags.length > 0) {
                html += '<div class="flex flex-wrap gap-2 mt-4">';
                card.tags.forEach(tag => {
                    html += `<span class="px-3 py-1 bg-indigo-100 text-indigo-700 text-sm rounded-full">${escapeHtml(tag)}</span>`;
                });
                html += '</div>';
            }
            
            html += '</div>';
            previewDiv.innerHTML = html;
        }

        // Update cards list
        function updateCardsList() {
            const listDiv = document.getElementById('cardsList');
            const countSpan = document.getElementById('cardCount');
            
            countSpan.textContent = cards.length;
            
            if (cards.length === 0) {
                listDiv.innerHTML = '<p class="text-gray-400 text-center py-8">No cards added yet</p>';
                return;
            }
            
            listDiv.innerHTML = cards.map((card, index) => `
                <div class="bg-gray-50 border border-gray-200 rounded-lg p-4 flex justify-between items-center hover:shadow-md transition">
                    <div class="flex-1">
                        <p class="font-medium text-sm text-gray-800">${escapeHtml(card.front.substring(0, 60))}${card.front.length > 60 ? '...' : ''}</p>
                        <p class="text-xs text-gray-500 mt-1">${card.tags.length} tags • ${card.clinical_vignette ? 'With vignette' : 'No vignette'}</p>
                    </div>
                    <button onclick="removeCard(${index})" class="text-red-500 hover:text-red-700 p-2 ml-4">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            `).join('');
        }

        // Remove card
        function removeCard(index) {
            cards.splice(index, 1);
            updateCardsList();
            if (cards.length === 0) {
                document.getElementById('generateBtn').disabled = true;
                document.getElementById('previewCard').innerHTML = `
                    <div class="text-center text-gray-500 py-12 animate-pulse-slow">
                        <i class="fas fa-clipboard-list text-5xl mb-4"></i>
                        <p class="text-lg">Your medical flashcard preview will appear here</p>
                    </div>
                `;
            }
        }

        // Clear all cards
        function clearAllCards() {
            if (confirm('Are you sure you want to clear all cards?')) {
                cards = [];
                updateCardsList();
                document.getElementById('generateBtn').disabled = true;
                document.getElementById('previewCard').innerHTML = `
                    <div class="text-center text-gray-500 py-12 animate-pulse-slow">
                        <i class="fas fa-clipboard-list text-5xl mb-4"></i>
                        <p class="text-lg">Your medical flashcard preview will appear here</p>
                    </div>
                `;
            }
        }

        // Generate deck
        async function generateDeck() {
            const btn = document.getElementById('generateBtn');
            btn.disabled = true;
            btn.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>Generating Enhanced Deck...';
            
            try {
                const response = await fetch('/api/enhanced-medical', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ cards: cards })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    document.getElementById('downloadLink').href = data.download_url;
                    document.getElementById('successModal').classList.remove('hidden');
                    
                    // Clear cards after successful generation
                    cards = [];
                    updateCardsList();
                    document.getElementById('previewCard').innerHTML = `
                        <div class="text-center text-gray-500 py-12 animate-pulse-slow">
                            <i class="fas fa-clipboard-list text-5xl mb-4"></i>
                            <p class="text-lg">Your medical flashcard preview will appear here</p>
                        </div>
                    `;
                } else {
                    alert('Error generating deck. Please try again.');
                }
            } catch (error) {
                console.error('Error:', error);
                alert('Error generating deck. Please try again.');
            } finally {
                btn.disabled = cards.length === 0;
                btn.innerHTML = '<i class="fas fa-download mr-2"></i>Generate Anki Deck';
            }
        }

        // Close modal
        function closeModal() {
            document.getElementById('successModal').classList.add('hidden');
        }

        // Escape HTML
        function escapeHtml(text) {
            const map = {
                '&': '&amp;',
                '<': '&lt;',
                '>': '&gt;',
                '"': '&quot;',
                "'": '&#039;'
            };
            return text.replace(/[&<>"']/g, m => map[m]);
        }
    </script>
</body>
</html>'''

# Routes
@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/enhanced-medical', methods=['POST', 'OPTIONS'])
def api_enhanced_medical():
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        data = request.get_json(force=True)
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        # Extract cards from various data formats
        cards = []
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict) and 'cards' in item:
                    cards.extend(item['cards'])
                elif isinstance(item, dict) and ('front' in item or 'raw_html' in item or 'raw_content' in item):
                    # Parse raw content if present
                    if 'raw_content' in item:
                        parsed_card = parse_raw_content(item['raw_content'])
                        cards.append(parsed_card)
                    else:
                        cards.append(item)
        elif isinstance(data, dict):
            if 'cards' in data:
                # Process each card in the array
                for card in data['cards']:
                    if 'raw_content' in card:
                        parsed_card = parse_raw_content(card['raw_content'])
                        cards.append(parsed_card)
                    else:
                        cards.append(card)
            elif 'raw_content' in data:
                # Parse single raw content
                parsed_card = parse_raw_content(data['raw_content'])
                cards = [parsed_card]
            elif 'front' in data or 'raw_html' in data:
                cards = [data]
        
        if not cards:
            return jsonify({'error': 'No valid cards found'}), 400
        
        # Generate deck
        deck_name = f"Enhanced_Medical_Deck_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        filename = anki_generator.generate_deck(deck_name, cards)
        
        # Get file info
        file_path = os.path.join("temp", filename)
        file_size = os.path.getsize(file_path)
        
        return jsonify({
            'success': True,
            'filename': filename,
            'deck_name': deck_name,
            'cards_processed': len(cards),
            'file_size': file_size,
            'download_url': f"/download/{filename}",
            'full_download_url': f"{request.host_url.rstrip('/')}/download/{filename}",
            'message': f'Successfully generated enhanced deck with {len(cards)} cards',
            'version': '6.0.0',
            'html_support': True
        }), 200
        
    except Exception as e:
        return jsonify({
            'error': 'Processing failed',
            'message': str(e)
        }), 500

def parse_raw_content(raw_content: str) -> Dict:
    """Parse raw text/code content and intelligently categorize into medical card fields"""
    
    # Initialize card fields
    card_fields = {
        'front': '',
        'back': '',
        'clinical_vignette': '',
        'explanation': '',
        'mnemonic': '',
        'tags': []
    }
    
    # Split content into lines for processing
    lines = raw_content.strip().split('\n')
    current_field = None
    current_content = []
    
    # Field mapping patterns
    field_patterns = {
        'front': ['front:', 'question:', 'q:', 'prompt:', 'ask:'],
        'back': ['back:', 'answer:', 'a:', 'response:', 'solution:'],
        'clinical_vignette': ['clinical vignette:', 'vignette:', 'case:', 'clinical case:', 'patient:', 'scenario:'],
        'explanation': ['explanation:', 'explain:', 'rationale:', 'reasoning:', 'why:', 'details:'],
        'mnemonic': ['mnemonic:', 'memory aid:', 'remember:', 'acronym:', 'mnemonic device:'],
        'tags': ['tags:', 'categories:', 'topics:', 'subjects:', 'keywords:']
    }
    
    def get_field_from_line(line: str):
        """Determine which field a line belongs to based on keywords"""
        line_lower = line.lower().strip()
        
        # Check for explicit field markers
        for field, patterns in field_patterns.items():
            for pattern in patterns:
                if line_lower.startswith(pattern):
                    return field
        
        # Check for HTML-style markers
        if '<div class="clinical-vignette"' in line_lower or 'clinical-vignette' in line_lower:
            return 'clinical_vignette'
        elif '<div class="question"' in line_lower or 'question' in line_lower:
            return 'front'
        elif '<div class="answer"' in line_lower or 'answer' in line_lower:
            return 'back'
        elif '<div class="explanation"' in line_lower or 'explanation' in line_lower:
            return 'explanation'
        elif '<div class="mnemonic"' in line_lower or 'mnemonic' in line_lower:
            return 'mnemonic'
        
        return None
    
    def clean_field_marker(line: str, field: str) -> str:
        """Remove field marker from the beginning of a line"""
        line_lower = line.lower().strip()
        for pattern in field_patterns.get(field, []):
            if line_lower.startswith(pattern):
                return line[len(pattern):].strip()
        return line.strip()
    
    # Process each line
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Check if this line indicates a new field
        detected_field = get_field_from_line(line)
        
        if detected_field:
            # Save previous field content
            if current_field and current_content:
                content = '\n'.join(current_content).strip()
                if current_field == 'tags':
                    # Parse tags from content
                    tags = [tag.strip() for tag in content.replace(',', ' ').split() if tag.strip()]
                    card_fields['tags'].extend(tags)
                else:
                    card_fields[current_field] = content
            
            # Start new field
            current_field = detected_field
            current_content = []
            
            # Add content after field marker (if any)
            cleaned_line = clean_field_marker(line, detected_field)
            if cleaned_line:
                current_content.append(cleaned_line)
                
        elif current_field:
            # Continue adding to current field
            current_content.append(line)
        else:
            # No field detected yet, assume it's front content
            if not current_field:
                current_field = 'front'
                current_content = []
            current_content.append(line)
    
    # Save final field content
    if current_field and current_content:
        content = '\n'.join(current_content).strip()
        if current_field == 'tags':
            tags = [tag.strip() for tag in content.replace(',', ' ').split() if tag.strip()]
            card_fields['tags'].extend(tags)
        else:
            card_fields[current_field] = content
    
    # If no front content was explicitly marked, use the first substantial content
    if not card_fields['front'] and not card_fields['clinical_vignette']:
        # Find the first non-empty field that could be a question
        for field in ['clinical_vignette', 'explanation']:
            if card_fields[field]:
                card_fields['front'] = card_fields[field][:200] + "..." if len(card_fields[field]) > 200 else card_fields[field]
                break
    
    return card_fields

@app.route('/api/raw-html', methods=['POST', 'OPTIONS'])
def api_raw_html():
    """Dedicated endpoint for raw HTML content processing"""
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        data = request.get_json(force=True)
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        # Handle raw HTML input
        cards = []
        
        # Support multiple formats for raw HTML
        if 'raw_html' in data:
            # Single raw HTML content
            cards.append({
                'front': data['raw_html'],
                'back': data.get('back', ''),
                'tags': data.get('tags', [])
            })
        elif 'raw_content' in data:
            # Parse raw text content intelligently
            parsed_card = parse_raw_content(data['raw_content'])
            cards.append(parsed_card)
        elif 'content' in data:
            # Parse general content
            parsed_card = parse_raw_content(data['content'])
            cards.append(parsed_card)
        elif 'cards' in data:
            # Multiple cards with raw HTML or content
            for card in data['cards']:
                if 'raw_html' in card:
                    cards.append(card)
                elif 'raw_content' in card:
                    parsed_card = parse_raw_content(card['raw_content'])
                    cards.append(parsed_card)
                elif 'content' in card:
                    parsed_card = parse_raw_content(card['content'])
                    cards.append(parsed_card)
                elif 'front' in card:
                    cards.append(card)
        
        if not cards:
            return jsonify({'error': 'No valid HTML content found'}), 400
        
        # Generate deck
        deck_name = f"Raw_HTML_Medical_Deck_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        filename = anki_generator.generate_deck(deck_name, cards)
        
        # Get file info
        file_path = os.path.join("temp", filename)
        file_size = os.path.getsize(file_path)
        
        return jsonify({
            'success': True,
            'filename': filename,
            'deck_name': deck_name,
            'cards_processed': len(cards),
            'file_size': file_size,
            'download_url': f"/download/{filename}",
            'full_download_url': f"{request.host_url.rstrip('/')}/download/{filename}",
            'message': f'Successfully processed raw content into {len(cards)} cards',
            'version': '6.0.0',
            'processing_type': 'intelligent_parsing'
        }), 200
        
    except Exception as e:
        return jsonify({
            'error': 'Content parsing failed',
            'message': str(e)
        }), 500

@app.route('/api/webhook/n8n', methods=['POST'])
def receive_n8n_webhook():
    try:
        data = request.get_json(force=True)
        
        # Extract cards from n8n payload
        cards = []
        if 'cards' in data:
            cards = data['cards']
        elif 'data' in data:
            if isinstance(data['data'], list):
                cards = data['data']
            elif isinstance(data['data'], dict) and 'cards' in data['data']:
                cards = data['data']['cards']
        
        if not cards:
            return jsonify({'error': 'No valid flashcard data found'}), 400
        
        # Generate deck name
        deck_name = f"n8n_Medical_Flashcards_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        if 'workflow_id' in data:
            deck_name = f"n8n_{data['workflow_id']}"
        
        # Generate Anki file
        filename = anki_generator.generate_deck(deck_name, cards)
        
        return jsonify({
            'success': True,
            'filename': filename,
            'deck_name': deck_name,
            'card_count': len(cards),
            'download_url': f"/download/{filename}",
            'message': 'Deck generated successfully from n8n webhook'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/download/<path:filename>')
def download_file(filename):
    try:
        file_path = os.path.join('temp', filename)
        if not os.path.exists(file_path):
            return f"File not found: {filename}", 404
        
        return send_file(
            file_path,
            as_attachment=True,
            download_name=filename,
            mimetype='application/octet-stream'
        )
    except Exception as e:
        return "Download failed", 500

@app.route('/api/health', methods=['GET'])
def api_health():
    return jsonify({
        'status': 'healthy',
        'service': 'Enhanced Medical Flashcard Generator',
        'version': '6.0.0',
        'framework': 'Flask + Enhanced UI',
        'features': [
            'enhanced_medical_cards',
            'n8n_webhook_support', 
            'beautiful_ui',
            'clinical_vignettes',
            'advanced_styling'
        ],
        'timestamp': datetime.now().isoformat()
    }), 200

# Legacy compatibility endpoints
@app.route('/api/simple', methods=['POST', 'OPTIONS'])
def api_simple():
    return api_enhanced_medical()

@app.route('/api/generate', methods=['POST'])
def api_generate():
    return api_enhanced_medical()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)