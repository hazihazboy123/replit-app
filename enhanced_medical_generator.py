import genanki
import random
import json
import os
import requests
from typing import List, Dict, Optional
import re
import base64
from pathlib import Path
import tempfile
import shutil

class AnkiMedicalCardGenerator:
    def __init__(self):
        # Generate unique IDs for model and deck
        self.model_id = random.randrange(1 << 30, 1 << 31)
        self.deck_id = random.randrange(1 << 30, 1 << 31)
        
        # Enhanced CSS with proper formatting
        self.css = """
.card {
    font-family: Arial, sans-serif;
    font-size: 20px;
    text-align: center;
    color: black;
    background-color: white;
    padding: 20px;
    max-width: 100%;
    margin: 0 auto;
    box-sizing: border-box;
}

/* Question styling */
.question {
    font-size: 24px;
    margin-bottom: 20px;
    color: #333;
}

/* Clinical Vignette Box */
.clinical-vignette {
    background-color: #2c3e50;
    color: white !important;
    padding: 20px;
    border-radius: 10px;
    margin: 10px auto;
    max-width: 90%;
    text-align: left;
    font-size: 18px;
    line-height: 1.6;
}

.clinical-vignette h3 {
    color: white !important;
    margin-bottom: 15px;
    text-align: center;
    font-size: 22px;
}

/* Memory Aid Box */
.memory-aid {
    background-color: #27ae60;
    color: white;
    padding: 20px;
    border-radius: 10px;
    margin: 10px auto;
    max-width: 90%;
    text-align: left;
    font-size: 18px;
    line-height: 1.6;
}

.memory-aid h3 {
    color: white;
    margin-bottom: 15px;
    text-align: center;
    font-size: 22px;
}

/* Highlighted text - now just red without background */
.highlight {
    color: #e74c3c;
    font-weight: bold;
}

/* Cloze deletions */
.cloze {
    font-weight: bold;
    color: blue;
}

/* Images */
img {
    max-width: 100%;
    height: auto;
    margin: 10px auto;
    display: block;
    border-radius: 5px;
}

/* Answer section */
.answer {
    margin-top: 20px;
    font-size: 20px;
    color: #2c3e50;
}

/* Media container */
.media-container {
    margin: 15px auto;
    text-align: center;
}

/* Ensure proper spacing */
.content-section {
    margin: 15px 0;
}

/* Fix for small screens */
@media (max-width: 600px) {
    .card {
        font-size: 16px;
        padding: 10px;
    }
    
    .question {
        font-size: 20px;
    }
    
    .clinical-vignette,
    .memory-aid {
        font-size: 16px;
        padding: 15px;
    }
}
"""
        
        # Create the model with fixed templates
        self.model = genanki.Model(
            self.model_id,
            'Medical Enhanced Cloze',
            fields=[
                {'name': 'Text'},
                {'name': 'Extra'},
                {'name': 'MyMedia'},
                {'name': 'Tags'}
            ],
            templates=[
                {
                    'name': 'Cloze',
                    'qfmt': """
<div class="card">
    <div class="question">
        {{cloze:Text}}
    </div>
    <div class="media-container">
        {{MyMedia}}
    </div>
</div>
""",
                    'afmt': """
<div class="card">
    <div class="question">
        {{cloze:Text}}
    </div>
    <div class="media-container">
        {{MyMedia}}
    </div>
    <div class="answer">
        {{Extra}}
    </div>
</div>
""",
                },
            ],
            css=self.css,
            model_type=genanki.Model.CLOZE
        )
        
        # Create deck
        self.deck = genanki.Deck(self.deck_id, 'Medical Flashcards')
        self.media_files = []
        self.temp_dir = tempfile.mkdtemp()

    def download_image(self, url: str, card_id: str) -> Optional[str]:
        """Download image from URL and save locally for Anki"""
        try:
            # Clean up the URL
            url = url.strip()
            
            # Generate a unique filename
            extension = '.jpg'  # Default extension
            if '.' in url:
                possible_ext = url.split('.')[-1].lower()
                if possible_ext in ['jpg', 'jpeg', 'png', 'gif', 'webp']:
                    extension = f'.{possible_ext}'
            
            filename = f"medical_image_{card_id}_{random.randint(1000, 9999)}{extension}"
            filepath = os.path.join(self.temp_dir, filename)
            
            # Download the image
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            # Save the image
            with open(filepath, 'wb') as f:
                f.write(response.content)
            
            self.media_files.append(filepath)
            return filename
            
        except Exception as e:
            print(f"Error downloading image from {url}: {str(e)}")
            return None

    def process_content_with_highlighting(self, content: str) -> str:
        """Convert orange highlights to red text without background"""
        # Replace various highlighting patterns
        patterns = [
            (r'<mark[^>]*>(.*?)</mark>', r'<span class="highlight">\1</span>'),
            (r'<span[^>]*style="[^"]*background-color:\s*orange[^"]*"[^>]*>(.*?)</span>', 
             r'<span class="highlight">\1</span>'),
            (r'==(.*?)==', r'<span class="highlight">\1</span>'),  # Markdown style
        ]
        
        for pattern, replacement in patterns:
            content = re.sub(pattern, replacement, content, flags=re.IGNORECASE | re.DOTALL)
        
        return content

    def fix_cloze_format(self, text: str) -> str:
        """Fix cloze deletions from single braces to double braces"""
        # First, protect already correct double braces
        text = text.replace('{{c', '§§c')
        text = text.replace('}}', '§§')
        
        # Now fix single braces that are cloze deletions
        # Match patterns like {c1::content} or {c1::content::hint}
        cloze_pattern = r'\{(c\d+::[^}]+)\}'
        text = re.sub(cloze_pattern, r'{{\1}}', text)
        
        # Restore the protected double braces
        text = text.replace('§§c', '{{c')
        text = text.replace('§§', '}}')
        
        return text

    def create_medical_card(self, card_data: Dict) -> genanki.Note:
        """Create a medical flashcard with enhanced formatting"""
        try:
            # Extract fields
            question = card_data.get('question', '')
            answer = card_data.get('answer', '')
            clinical_vignette = card_data.get('clinical_vignette', '')
            memory_aid = card_data.get('memory_aid', '')
            tags = card_data.get('tags', [])
            image_url = card_data.get('image_url', '')
            
            # Fix cloze formatting in question
            question = self.fix_cloze_format(question)
            
            # Process highlighting in all content
            question = self.process_content_with_highlighting(question)
            clinical_vignette = self.process_content_with_highlighting(clinical_vignette)
            memory_aid = self.process_content_with_highlighting(memory_aid)
            
            # Build the main text field
            text_content = f'<div class="content-section">{question}</div>'
            
            # Add clinical vignette if present
            if clinical_vignette and clinical_vignette.strip():
                vignette_html = f'''
<div class="clinical-vignette">
    <h3>🩺 Clinical Vignette</h3>
    {clinical_vignette}
</div>'''
                text_content += vignette_html
            
            # Build extra field (shown on answer side)
            extra_content = f'<div class="answer-text">{answer}</div>'
            
            # Add memory aid if present
            if memory_aid and memory_aid.strip():
                memory_html = f'''
<div class="memory-aid">
    <h3>🧠 Memory Aid</h3>
    {memory_aid}
</div>'''
                extra_content += memory_html
            
            # Handle image
            media_content = ''
            if image_url and image_url.strip():
                # Generate unique ID for this card
                card_id = str(random.randint(10000, 99999))
                
                # Download the image
                image_filename = self.download_image(image_url, card_id)
                
                if image_filename:
                    media_content = f'<img src="{image_filename}" alt="Medical diagram">'
                else:
                    # Fallback if download fails
                    print(f"Failed to download image, using placeholder for: {image_url}")
                    media_content = '<div style="color: red;">⚠️ Image failed to load</div>'
            
            # Ensure tags is a list
            if isinstance(tags, str):
                tags = [tags]
            elif not isinstance(tags, list):
                tags = []
            
            # Add some default tags
            tags.extend(['Medical', 'Enhanced'])
            
            # Create the note
            note = genanki.Note(
                model=self.model,
                fields=[
                    text_content,
                    extra_content,
                    media_content,
                    ' '.join(tags)
                ],
                tags=tags
            )
            
            return note
            
        except Exception as e:
            print(f"Error creating card: {str(e)}")
            print(f"Card data: {card_data}")
            raise

    def generate_deck(self, cards_data: List[Dict], output_path: str = 'medical_flashcards.apkg'):
        """Generate the complete Anki deck"""
        try:
            # Add cards to deck
            for i, card_data in enumerate(cards_data):
                print(f"Processing card {i+1}/{len(cards_data)}")
                note = self.create_medical_card(card_data)
                self.deck.add_note(note)
            
            # Create the package with media files
            if self.media_files:
                genanki.Package(self.deck, media_files=self.media_files).write_to_file(output_path)
            else:
                genanki.Package(self.deck).write_to_file(output_path)
            
            print(f"Successfully created {output_path} with {len(cards_data)} cards")
            
            # Cleanup
            self.cleanup()
            
        except Exception as e:
            print(f"Error generating deck: {str(e)}")
            self.cleanup()
            raise
    
    def cleanup(self):
        """Clean up temporary files"""
        try:
            if os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
        except Exception as e:
            print(f"Error during cleanup: {str(e)}")

# N8N Integration Function
def process_n8n_input(input_data: str) -> Dict:
    """Process input from n8n and generate Anki deck"""
    try:
        # Parse the input
        if isinstance(input_data, str):
            data = json.loads(input_data)
        else:
            data = input_data
        
        # Extract cards array
        cards = data.get('cards', [])
        if not cards:
            raise ValueError("No cards found in input data")
        
        # Initialize generator
        generator = AnkiMedicalCardGenerator()
        
        # Generate the deck
        output_filename = data.get('output_filename', 'medical_flashcards.apkg')
        generator.generate_deck(cards, output_filename)
        
        # Return success response
        return {
            'success': True,
            'message': f'Successfully generated {len(cards)} cards',
            'filename': output_filename,
            'card_count': len(cards)
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'message': 'Failed to generate Anki deck'
        }

# Example usage
if __name__ == "__main__":
    # Example card data
    example_cards = [
        {
            "question": "Which {{c1::spinal nerves}} contribute to the {{c2::brachial plexus}}?",
            "answer": "The brachial plexus is formed by nerve roots C5-T1",
            "clinical_vignette": "A 25-year-old male presents after a motorcycle accident with inability to abduct his arm and numbness over the lateral shoulder. Physical exam reveals weakness of shoulder abduction and external rotation.",
            "memory_aid": "Reach To Drink Cold Beer: Roots (C5-T1), Trunks, Divisions, Cords, Branches - emphasizes the brachial plexus structure originating from C5-T1 nerve roots",
            "tags": ["anatomy", "neurology", "brachial-plexus"],
            "image_url": "https://example.com/brachial-plexus-diagram.jpg"
        }
    ]
    
    # Test the generator
    generator = AnkiMedicalCardGenerator()
    generator.generate_deck(example_cards, "test_medical_deck.apkg")