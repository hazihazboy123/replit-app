"""
API routes for n8n integration and programmatic access
"""
import os
import json
import tempfile
import logging
from flask import Blueprint, request, jsonify, send_file
import genanki

# Create API blueprint
api = Blueprint('api', __name__, url_prefix='/api')

@api.route('/generate', methods=['POST'])
def generate_anki_deck():
    """
    API endpoint for n8n integration to generate Anki decks from JSON data
    Accepts JSON payload directly and returns binary .apkg file
    """
    try:
        # Get JSON data from request body
        if request.is_json:
            json_data = request.get_json()
        else:
            return jsonify({
                'error': 'Content-Type must be application/json',
                'message': 'Please send JSON data with proper Content-Type header'
            }), 400
        
        if not json_data:
            return jsonify({
                'error': 'No JSON data provided',
                'message': 'Request body must contain valid JSON data'
            }), 400
        
        # Import here to avoid circular imports
        from app import FlashcardProcessor
        
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
        logging.error(f"API error generating deck: {str(e)}")
        return jsonify({
            'error': 'Internal server error',
            'message': 'An error occurred while processing your request'
        }), 500

@api.route('/validate', methods=['POST'])
def validate_json_structure():
    """
    API endpoint to validate JSON structure without generating deck
    Useful for n8n workflows to check data before processing
    """
    try:
        # Get JSON data from request body
        if request.is_json:
            json_data = request.get_json()
        else:
            return jsonify({
                'error': 'Content-Type must be application/json',
                'message': 'Please send JSON data with proper Content-Type header'
            }), 400
        
        if not json_data:
            return jsonify({
                'error': 'No JSON data provided',
                'message': 'Request body must contain valid JSON data'
            }), 400
        
        # Import here to avoid circular imports
        from app import FlashcardProcessor
        
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
        logging.error(f"API error validating JSON: {str(e)}")
        return jsonify({
            'valid': False,
            'error': 'Internal server error',
            'message': 'An error occurred while validating your request'
        }), 500

@api.route('/schema', methods=['GET'])
def get_json_schema():
    """
    API endpoint to get the expected JSON schema for medical flashcards
    Useful for n8n workflows and documentation
    """
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
        },
        "examples": [
            {
                "deck_name": "Medical Terminology",
                "cards": [
                    {
                        "question": "What is the mechanism of action of <span class='highlight-red'>Aspirin</span>?",
                        "answer": "Irreversibly inhibits COX-1 and COX-2 enzymes",
                        "notes": "Important for cardiology and pain management",
                        "tags": "Pharmacology::NSAIDs::Aspirin"
                    },
                    {
                        "cloze_text": "{{c1::Myocardial infarction}} is caused by {{c2::coronary artery occlusion}}",
                        "notes": "Key concept for USMLE Step 1",
                        "tags": "Cardiology::Pathophysiology"
                    }
                ]
            }
        ]
    }
    
    return jsonify(schema), 200

@api.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint for monitoring
    """
    return jsonify({
        'status': 'healthy',
        'service': 'Medical JSON to Anki Converter',
        'version': '1.0.0'
    }), 200