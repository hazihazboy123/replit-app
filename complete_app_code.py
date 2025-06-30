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
                    
                    <div id="cardPreview" class="card-preview rounded-lg p-6 min-h-[200px] border-2 border-dashed border-gray-300">
                        <div class="text-center text-gray-500 mt-8">
                            <i class="fas fa-cards-blank text-4xl mb-4 opacity-50"></i>
                            <p class="text-lg">Fill out the form to see your flashcard preview</p>
                        </div>
                    </div>
                </div>

                <!-- Cards List -->
                <div class="bg-white rounded-xl shadow-lg p-6">
                    <h2 class="text-2xl font-semibold mb-6 flex items-center text-gray-800">
                        <i class="fas fa-layer-group mr-3 text-purple-600"></i>
                        Your Flashcards (<span id="cardCount">0</span>)
                    </h2>
                    
                    <div id="cardsList" class="space-y-4 max-h-96 overflow-y-auto">
                        <div class="text-center text-gray-500 py-8">
                            <i class="fas fa-plus-circle text-3xl mb-3 opacity-50"></i>
                            <p>No flashcards yet. Create your first medical flashcard above!</p>
                        </div>
                    </div>
                    
                    <div id="generateSection" class="mt-6 hidden">
                        <div class="border-t pt-6">
                            <input type="text" id="deckName" placeholder="Enter deck name (e.g., Cardiology Review)" class="w-full p-3 border border-gray-300 rounded-lg mb-4 focus:ring-2 focus:ring-blue-500 focus:border-blue-500">
                            <button id="generateDeck" class="w-full bg-gradient-to-r from-green-600 to-blue-600 text-white py-4 px-6 rounded-lg hover:from-green-700 hover:to-blue-700 transition duration-200 font-medium text-lg shadow-lg">
                                <i class="fas fa-download mr-2"></i>Generate Anki Deck
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- API Documentation -->
        <div class="mt-12 bg-white rounded-xl shadow-lg p-6">
            <h2 class="text-2xl font-semibold mb-6 flex items-center text-gray-800">
                <i class="fas fa-code mr-3 text-indigo-600"></i>
                API Documentation
            </h2>
            
            <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                <!-- Enhanced Medical API -->
                <div class="bg-gray-50 rounded-lg p-4">
                    <h3 class="font-semibold text-lg mb-3 text-indigo-600">Enhanced Medical API</h3>
                    <code class="text-sm bg-gray-800 text-green-400 p-2 rounded block mb-3">POST /api/enhanced-medical</code>
                    <p class="text-sm text-gray-600 mb-3">Advanced medical flashcard generation with intelligent parsing</p>
                    <div class="text-xs bg-white p-3 rounded border">
                        <strong>JSON Format:</strong><br>
                        {<br>
                        &nbsp;&nbsp;"raw_content": "Front: Question\\nBack: Answer\\nExplanation: Details"<br>
                        }
                    </div>
                </div>

                <!-- n8n Webhook -->
                <div class="bg-gray-50 rounded-lg p-4">
                    <h3 class="font-semibold text-lg mb-3 text-purple-600">n8n Webhook</h3>
                    <code class="text-sm bg-gray-800 text-green-400 p-2 rounded block mb-3">POST /api/webhook/n8n</code>
                    <p class="text-sm text-gray-600 mb-3">Optimized for n8n automation workflows</p>
                    <div class="text-xs bg-white p-3 rounded border">
                        <strong>JSON Format:</strong><br>
                        {<br>
                        &nbsp;&nbsp;"raw_content": "{{ $json.output }}"<br>
                        }
                    </div>
                </div>

                <!-- Raw HTML API -->
                <div class="bg-gray-50 rounded-lg p-4">
                    <h3 class="font-semibold text-lg mb-3 text-red-600">Raw HTML API</h3>
                    <code class="text-sm bg-gray-800 text-green-400 p-2 rounded block mb-3">POST /api/raw-html</code>
                    <p class="text-sm text-gray-600 mb-3">Preserves HTML formatting and styling</p>
                    <div class="text-xs bg-white p-3 rounded border">
                        <strong>JSON Format:</strong><br>
                        {<br>
                        &nbsp;&nbsp;"raw_html": "&lt;p style='color:red'&gt;Question&lt;/p&gt;"<br>
                        }
                    </div>
                </div>

                <!-- Test Endpoint -->
                <div class="bg-gray-50 rounded-lg p-4">
                    <h3 class="font-semibold text-lg mb-3 text-green-600">Test Endpoint</h3>
                    <code class="text-sm bg-gray-800 text-green-400 p-2 rounded block mb-3">POST /api/test</code>
                    <p class="text-sm text-gray-600 mb-3">Debug and test your n8n connections</p>
                    <div class="text-xs bg-white p-3 rounded border">
                        <strong>Returns:</strong> Detailed request information for debugging
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        let flashcards = [];
        
        // Update preview as user types
        function updatePreview() {
            const vignette = document.getElementById('vignette').value;
            const question = document.getElementById('question').value;
            const answer = document.getElementById('answer').value;
            const explanation = document.getElementById('explanation').value;
            const mnemonic = document.getElementById('mnemonic').value;
            const tags = document.getElementById('tags').value;
            
            const preview = document.getElementById('cardPreview');
            
            if (!question && !answer) {
                preview.innerHTML = `
                    <div class="text-center text-gray-500 mt-8">
                        <i class="fas fa-cards-blank text-4xl mb-4 opacity-50"></i>
                        <p class="text-lg">Fill out the form to see your flashcard preview</p>
                    </div>
                `;
                return;
            }
            
            preview.innerHTML = `
                <div class="space-y-4">
                    ${vignette ? `<div class="bg-blue-50 border-l-4 border-blue-400 p-3 rounded"><strong>Clinical Vignette:</strong> ${vignette}</div>` : ''}
                    ${question ? `<div class="bg-gray-50 p-3 rounded"><strong>Question:</strong> ${question}</div>` : ''}
                    ${answer ? `<div class="bg-green-50 border-l-4 border-green-400 p-3 rounded"><strong>Answer:</strong> ${answer}</div>` : ''}
                    ${explanation ? `<div class="bg-yellow-50 border-l-4 border-yellow-400 p-3 rounded"><strong>Explanation:</strong> ${explanation}</div>` : ''}
                    ${mnemonic ? `<div class="bg-purple-50 border-l-4 border-purple-400 p-3 rounded"><strong>Mnemonic:</strong> ${mnemonic}</div>` : ''}
                    ${tags ? `<div class="text-sm text-gray-600"><strong>Tags:</strong> ${tags}</div>` : ''}
                </div>
            `;
        }
        
        // Add event listeners for real-time preview
        ['vignette', 'question', 'answer', 'explanation', 'mnemonic', 'tags'].forEach(id => {
            document.getElementById(id).addEventListener('input', updatePreview);
        });
        
        // Handle form submission
        document.getElementById('flashcardForm').addEventListener('submit', function(e) {
            e.preventDefault();
            
            const flashcard = {
                clinical_vignette: document.getElementById('vignette').value,
                front: document.getElementById('question').value,
                back: document.getElementById('answer').value,
                explanation: document.getElementById('explanation').value,
                mnemonic: document.getElementById('mnemonic').value,
                tags: document.getElementById('tags').value.split(',').map(t => t.trim()).filter(t => t)
            };
            
            flashcards.push(flashcard);
            updateCardsList();
            
            // Clear form
            this.reset();
            updatePreview();
            
            // Show success message
            showNotification('Flashcard added successfully!', 'success');
        });
        
        function updateCardsList() {
            const cardsList = document.getElementById('cardsList');
            const cardCount = document.getElementById('cardCount');
            const generateSection = document.getElementById('generateSection');
            
            cardCount.textContent = flashcards.length;
            
            if (flashcards.length === 0) {
                cardsList.innerHTML = `
                    <div class="text-center text-gray-500 py-8">
                        <i class="fas fa-plus-circle text-3xl mb-3 opacity-50"></i>
                        <p>No flashcards yet. Create your first medical flashcard above!</p>
                    </div>
                `;
                generateSection.classList.add('hidden');
                return;
            }
            
            generateSection.classList.remove('hidden');
            
            cardsList.innerHTML = flashcards.map((card, index) => `
                <div class="border rounded-lg p-4 bg-gray-50">
                    <div class="flex justify-between items-start mb-2">
                        <h4 class="font-medium text-gray-800">Card ${index + 1}</h4>
                        <button onclick="removeCard(${index})" class="text-red-500 hover:text-red-700">
                            <i class="fas fa-trash text-sm"></i>
                        </button>
                    </div>
                    <p class="text-sm text-gray-600 mb-1"><strong>Q:</strong> ${card.front}</p>
                    <p class="text-sm text-gray-600"><strong>A:</strong> ${card.back}</p>
                    ${card.tags.length > 0 ? `<div class="mt-2 text-xs text-blue-600">Tags: ${card.tags.join(', ')}</div>` : ''}
                </div>
            `).join('');
        }
        
        function removeCard(index) {
            flashcards.splice(index, 1);
            updateCardsList();
            showNotification('Flashcard removed', 'info');
        }
        
        // Generate deck
        document.getElementById('generateDeck').addEventListener('click', async function() {
            const deckName = document.getElementById('deckName').value || 'Medical Flashcards';
            
            if (flashcards.length === 0) {
                showNotification('Please add at least one flashcard', 'error');
                return;
            }
            
            try {
                this.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>Generating...';
                this.disabled = true;
                
                const response = await fetch('/api/enhanced-medical', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ cards: flashcards, deck_name: deckName })
                });
                
                const result = await response.json();
                
                if (result.success) {
                    // Create download link
                    const link = document.createElement('a');
                    link.href = result.download_url;
                    link.download = result.filename;
                    link.click();
                    
                    showNotification(`Deck "${result.deck_name}" generated successfully!`, 'success');
                    
                    // Reset
                    flashcards = [];
                    updateCardsList();
                    document.getElementById('deckName').value = '';
                } else {
                    showNotification('Error generating deck: ' + result.message, 'error');
                }
            } catch (error) {
                showNotification('Error: ' + error.message, 'error');
            } finally {
                this.innerHTML = '<i class="fas fa-download mr-2"></i>Generate Anki Deck';
                this.disabled = false;
            }
        });
        
        function showNotification(message, type) {
            const notification = document.createElement('div');
            notification.className = `fixed top-4 right-4 p-4 rounded-lg shadow-lg z-50 ${
                type === 'success' ? 'bg-green-500' : 
                type === 'error' ? 'bg-red-500' : 'bg-blue-500'
            } text-white`;
            notification.innerHTML = `
                <div class="flex items-center">
                    <i class="fas fa-${type === 'success' ? 'check' : type === 'error' ? 'exclamation' : 'info'} mr-2"></i>
                    ${message}
                </div>
            `;
            
            document.body.appendChild(notification);
            
            setTimeout(() => {
                notification.remove();
            }, 3000);
        }
    </script>
</body>
</html>'''

def parse_raw_content(raw_content: str) -> Dict:
    """Parse raw text/code content and intelligently categorize into medical card fields"""
    if not raw_content or not raw_content.strip():
        return {}
    
    lines = raw_content.strip().split('\n')
    parsed_data = {
        'front': '',
        'back': '',
        'clinical_vignette': '',
        'explanation': '',
        'mnemonic': '',
        'tags': []
    }
    
    current_field = None
    
    def get_field_from_line(line: str):
        """Determine which field a line belongs to based on keywords"""
        line_lower = line.lower().strip()
        
        # Front/Question field markers
        if any(marker in line_lower for marker in [
            'front:', 'question:', 'q:', 'prompt:', 'ask:'
        ]):
            return 'front'
        
        # Back/Answer field markers
        elif any(marker in line_lower for marker in [
            'back:', 'answer:', 'a:', 'response:', 'solution:'
        ]):
            return 'back'
        
        # Clinical vignette field markers
        elif any(marker in line_lower for marker in [
            'clinical vignette:', 'vignette:', 'case:', 'clinical case:', 'patient:', 'scenario:'
        ]):
            return 'clinical_vignette'
        
        # Explanation field markers
        elif any(marker in line_lower for marker in [
            'explanation:', 'explain:', 'rationale:', 'reasoning:', 'why:', 'details:'
        ]):
            return 'explanation'
        
        # Mnemonic field markers
        elif any(marker in line_lower for marker in [
            'mnemonic:', 'memory aid:', 'remember:', 'acronym:', 'mnemonic device:'
        ]):
            return 'mnemonic'
        
        # Tags field markers
        elif any(marker in line_lower for marker in [
            'tags:', 'categories:', 'topics:', 'subjects:', 'keywords:'
        ]):
            return 'tags'
        
        return None
    
    def clean_field_marker(line: str, field: str) -> str:
        """Remove field marker from the beginning of a line"""
        line_lower = line.lower()
        markers = {
            'front': ['front:', 'question:', 'q:', 'prompt:', 'ask:'],
            'back': ['back:', 'answer:', 'a:', 'response:', 'solution:'],
            'clinical_vignette': ['clinical vignette:', 'vignette:', 'case:', 'clinical case:', 'patient:', 'scenario:'],
            'explanation': ['explanation:', 'explain:', 'rationale:', 'reasoning:', 'why:', 'details:'],
            'mnemonic': ['mnemonic:', 'memory aid:', 'remember:', 'acronym:', 'mnemonic device:'],
            'tags': ['tags:', 'categories:', 'topics:', 'subjects:', 'keywords:']
        }
        
        for marker in markers.get(field, []):
            if line_lower.startswith(marker):
                return line[len(marker):].strip()
        
        return line.strip()
    
    # Process each line
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Check if this line starts a new field
        field = get_field_from_line(line)
        if field:
            current_field = field
            content = clean_field_marker(line, field)
            if content:
                if field == 'tags':
                    # Handle tags specially
                    tag_content = content.replace(',', ' ').split()
                    parsed_data['tags'].extend([tag.strip() for tag in tag_content if tag.strip()])
                else:
                    parsed_data[field] = content
        elif current_field:
            # Continue adding to current field
            if current_field == 'tags':
                tag_content = line.replace(',', ' ').split()
                parsed_data['tags'].extend([tag.strip() for tag in tag_content if tag.strip()])
            else:
                if parsed_data[current_field]:
                    parsed_data[current_field] += ' ' + line
                else:
                    parsed_data[current_field] = line
        else:
            # No field marker found, try to intelligently assign
            # If we don't have a front yet, assume it's the question
            if not parsed_data['front']:
                parsed_data['front'] = line
                current_field = 'front'
            # If we have front but no back, assume it's the answer
            elif not parsed_data['back']:
                parsed_data['back'] = line
                current_field = 'back'
            # Otherwise, add to explanation
            else:
                if parsed_data['explanation']:
                    parsed_data['explanation'] += ' ' + line
                else:
                    parsed_data['explanation'] = line
                current_field = 'explanation'
    
    # Clean up empty fields and ensure we have at least front/back
    result = {}
    for key, value in parsed_data.items():
        if key == 'tags':
            if value:
                result[key] = value
        elif value and value.strip():
            result[key] = value.strip()
    
    return result

@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/enhanced-medical', methods=['POST'])
def api_enhanced_medical():
    try:
        data = request.get_json()
        
        # Handle raw_content parsing
        if 'raw_content' in data:
            parsed_card = parse_raw_content(data['raw_content'])
            cards = [parsed_card]
        elif 'cards' in data:
            cards = data['cards']
            # Process any cards that have raw_content
            processed_cards = []
            for card in cards:
                if 'raw_content' in card:
                    parsed_card = parse_raw_content(card['raw_content'])
                    # Merge with any existing fields
                    for key, value in card.items():
                        if key != 'raw_content' and value:
                            parsed_card[key] = value
                    processed_cards.append(parsed_card)
                else:
                    processed_cards.append(card)
            cards = processed_cards
        else:
            return jsonify({'error': 'No cards or raw_content provided'}), 400
        
        if not cards:
            return jsonify({'error': 'No valid cards found'}), 400
        
        # Generate deck
        deck_name = data.get('deck_name', f"Enhanced_Medical_Cards_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        filename = anki_generator.generate_deck(deck_name, cards)
        
        return jsonify({
            'success': True,
            'filename': filename,
            'deck_name': deck_name,
            'card_count': len(cards),
            'download_url': f"/download/{filename}",
            'message': 'Enhanced medical flashcards generated successfully'
        })
        
    except Exception as e:
        return jsonify({
            'error': 'Enhanced medical processing failed',
            'message': str(e)
        }), 500

@app.route('/api/raw-html', methods=['POST'])
def api_raw_html():
    """Dedicated endpoint for raw HTML content processing"""
    try:
        data = request.get_json()
        
        # Handle raw HTML with preserved formatting
        card_data = {}
        
        if 'raw_html' in data:
            card_data['raw_html'] = data['raw_html']
        
        # Handle other fields
        for field in ['front', 'back', 'clinical_vignette', 'explanation', 'mnemonic', 'tags']:
            if field in data:
                card_data[field] = data[field]
        
        # Ensure we have some content
        if not any(card_data.get(field) for field in ['raw_html', 'front', 'back']):
            return jsonify({'error': 'No content provided'}), 400
        
        # Generate deck
        deck_name = data.get('deck_name', f"Raw_HTML_Cards_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        filename = anki_generator.generate_deck(deck_name, [card_data])
        
        return jsonify({
            'success': True,
            'filename': filename,
            'deck_name': deck_name,
            'card_count': 1,
            'download_url': f"/download/{filename}",
            'message': 'Raw HTML flashcard generated successfully with preserved formatting'
        })
        
    except Exception as e:
        return jsonify({
            'error': 'Content parsing failed',
            'message': str(e)
        }), 500

@app.route('/api/webhook/n8n', methods=['POST'])
def receive_n8n_webhook():
    try:
        # Get raw request data for debugging
        raw_data = request.get_data(as_text=True)
        print(f"N8N Raw Data: {raw_data[:500]}...")
        
        # Try to parse JSON
        try:
            data = request.get_json(force=True)
        except Exception as json_error:
            print(f"JSON Parse Error: {json_error}")
            # If JSON parsing fails, try to treat raw data as content
            if raw_data and raw_data.strip():
                # Treat raw data as content to be parsed
                print(f"Treating raw data as content: {raw_data[:200]}...")
                parsed_card = parse_raw_content(raw_data)
                cards = [parsed_card]
                
                # Generate deck
                deck_name = f"n8n_Raw_Content_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                filename = anki_generator.generate_deck(deck_name, cards)
                
                return jsonify({
                    'success': True,
                    'filename': filename,
                    'deck_name': deck_name,
                    'card_count': len(cards),
                    'download_url': f"/download/{filename}",
                    'full_download_url': f"{request.host_url.rstrip('/')}/download/{filename}",
                    'message': 'Deck generated successfully from raw n8n content',
                    'processing_type': 'n8n_raw_content'
                })
            else:
                return jsonify({
                    'error': 'Invalid JSON format and no raw content',
                    'details': str(json_error),
                    'raw_data_preview': raw_data[:200]
                }), 400
        
        print(f"N8N Parsed Data: {data}")
        
        # Extract cards from n8n payload with more flexible handling
        cards = []
        
        # Handle direct raw_content from n8n
        if 'raw_content' in data:
            parsed_card = parse_raw_content(data['raw_content'])
            cards = [parsed_card]
        elif 'content' in data:
            parsed_card = parse_raw_content(data['content'])
            cards = [parsed_card]
        elif 'cards' in data:
            for card in data['cards']:
                if 'raw_content' in card:
                    parsed_card = parse_raw_content(card['raw_content'])
                    cards.append(parsed_card)
                else:
                    cards.append(card)
        elif 'data' in data:
            if isinstance(data['data'], list):
                for item in data['data']:
                    if isinstance(item, dict):
                        if 'raw_content' in item:
                            parsed_card = parse_raw_content(item['raw_content'])
                            cards.append(parsed_card)
                        else:
                            cards.append(item)
            elif isinstance(data['data'], dict):
                if 'cards' in data['data']:
                    cards = data['data']['cards']
                elif 'raw_content' in data['data']:
                    parsed_card = parse_raw_content(data['data']['raw_content'])
                    cards = [parsed_card]
        elif isinstance(data, list):
            # Handle array of cards directly
            for item in data:
                if 'raw_content' in item:
                    parsed_card = parse_raw_content(item['raw_content'])
                    cards.append(parsed_card)
                else:
                    cards.append(item)
        
        print(f"Extracted Cards: {len(cards)}")
        
        if not cards:
            return jsonify({
                'error': 'No valid flashcard data found',
                'received_keys': list(data.keys()) if isinstance(data, dict) else 'data_is_not_dict',
                'data_type': type(data).__name__
            }), 400
        
        # Generate deck name
        deck_name = f"n8n_Medical_Flashcards_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        if 'workflow_id' in data and isinstance(data, dict):
            deck_name = f"n8n_{data['workflow_id']}"
        
        # Generate Anki file
        filename = anki_generator.generate_deck(deck_name, cards)
        
        return jsonify({
            'success': True,
            'filename': filename,
            'deck_name': deck_name,
            'card_count': len(cards),
            'download_url': f"/download/{filename}",
            'full_download_url': f"{request.host_url.rstrip('/')}/download/{filename}",
            'message': 'Deck generated successfully from n8n webhook',
            'processing_type': 'n8n_webhook'
        })
        
    except Exception as e:
        print(f"N8N Webhook Error: {str(e)}")
        return jsonify({
            'error': 'Processing failed',
            'message': str(e),
            'endpoint': 'n8n_webhook'
        }), 500

@app.route('/download/<filename>')
def download_file(filename):
    try:
        filepath = os.path.join("temp", filename)
        if os.path.exists(filepath):
            return send_file(
                filepath,
                as_attachment=True,
                download_name=filename,
                mimetype='application/octet-stream'
            )
        else:
            return "File not found", 404
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
            'intelligent_content_parsing',
            'raw_html_processing',
            'beautiful_ui',
            'clinical_vignettes',
            'advanced_styling'
        ],
        'endpoints': {
            'enhanced_medical': '/api/enhanced-medical',
            'n8n_webhook': '/api/webhook/n8n',
            'raw_html': '/api/raw-html',
            'simple': '/api/simple',
            'test': '/api/test'
        },
        'timestamp': datetime.now().isoformat()
    }), 200

@app.route('/api/test', methods=['POST', 'GET'])
def api_test():
    """Simple test endpoint for n8n debugging"""
    if request.method == 'GET':
        return jsonify({
            'message': 'Test endpoint is working',
            'timestamp': datetime.now().isoformat(),
            'method': 'GET'
        })
    
    try:
        # Get both raw and parsed data
        raw_data = request.get_data(as_text=True)
        headers = dict(request.headers)
        
        try:
            json_data = request.get_json(force=True)
        except:
            json_data = None
        
        return jsonify({
            'success': True,
            'message': 'Test endpoint received your data successfully',
            'raw_data_length': len(raw_data),
            'raw_data_preview': raw_data[:200] if raw_data else None,
            'headers': headers,
            'json_data': json_data,
            'content_type': request.content_type,
            'method': request.method,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'error': 'Test endpoint error',
            'message': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/api/simple', methods=['POST'])
def api_simple():
    """Backward compatibility endpoint"""
    try:
        data = request.get_json()
        
        # Handle multiple input formats for backward compatibility
        cards = []
        
        if 'cards' in data:
            cards = data['cards']
        elif 'raw_content' in data:
            parsed_card = parse_raw_content(data['raw_content'])
            cards = [parsed_card]
        elif isinstance(data, list):
            cards = data
        else:
            # Try to use the data as a single card
            cards = [data]
        
        if not cards:
            return jsonify({'error': 'No valid cards provided'}), 400
        
        # Generate deck
        deck_name = data.get('deck_name', f"Simple_Cards_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        filename = anki_generator.generate_deck(deck_name, cards)
        
        return jsonify({
            'success': True,
            'filename': filename,
            'deck_name': deck_name,
            'card_count': len(cards),
            'download_url': f"/download/{filename}",
            'message': 'Cards generated successfully'
        })
        
    except Exception as e:
        return jsonify({
            'error': 'Simple processing failed',
            'message': str(e)
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)