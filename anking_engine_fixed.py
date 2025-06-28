import genanki
import requests
import uuid
import os
import random
import tempfile
from typing import List, Dict

# Import the CSS from the original file
from anking_engine import ANKING_CSS, ANKING_JS

def get_anking_model():
    """Create the complete AnKing model with all fields and templates - FIXED VERSION"""
    
    # Consistent model IDs for proper Anki tracking
    ANKING_MODEL_ID = 1607392319
    ANKING_DECK_ID = 2059400110

    # Define all AnKing fields
    fields = [
        {'name': 'Front'},
        {'name': 'Back'}, 
        {'name': 'Extra'},
        {'name': 'Vignette'},
        {'name': 'Mnemonic'},
        {'name': 'Image'}
    ]

    # COMPLETELY FIXED AnKing templates 
    templates = [
        {
            'name': 'Card 1',
            'qfmt': '''
                <div class="card-content">
                    <div id="text">{{Front}}</div>
                </div>
                
                {{#Tags}}
                <div id="tags-container">{{clickable::Tags}}</div>
                {{/Tags}}
            ''',
            'afmt': '''
                {{FrontSide}}
                <hr id="answer">
                {{#Back}}
                <div class="answer-text">{{Back}}</div>
                {{/Back}}

                {{#Extra}}
                <div id="extra">{{Extra}}</div>
                {{/Extra}}

                {{#Vignette}}
                <div id="vignette-section">
                    <h3>Clinical Vignette</h3>
                    <div class="vignette-content">{{{Vignette}}}</div>
                </div>
                {{/Vignette}}

                {{#Mnemonic}}
                <div id="mnemonic-section">
                    <h3>Mnemonic</h3>
                    <div class="mnemonic-content">{{Mnemonic}}</div>
                </div>
                {{/Mnemonic}}

                {{#Image}}
                <div id="image-section">
                    {{{Image}}}
                </div>
                {{/Image}}
            ''',
        }
    ]

    # Create working Anki Model
    my_model = genanki.Model(
        ANKING_MODEL_ID,
        'AnKing Medical Flashcards',
        fields=fields,
        templates=templates,
        css=ANKING_CSS
    )
    return my_model, ANKING_DECK_ID

def create_anki_deck(cards_data, output_filename="AnKing_Medical_Deck.apkg", deck_name="AnKing Medical Deck"):
    """Create AnKing-style deck from card data - FIXED VERSION"""
    
    my_model, deck_id = get_anking_model()
    
    # Create the deck with the provided name
    my_deck = genanki.Deck(
        deck_id,
        deck_name
    )
    
    # Prepare media files list for genanki Package
    media_files = []

    for card_info in cards_data:
        card_type = card_info.get('type', 'basic')
        front_content = card_info.get('front', card_info.get('question', ''))
        back_content = card_info.get('back', card_info.get('answer', ''))
        extra_content = card_info.get('extra', card_info.get('additional_notes', card_info.get('notes', '')))
        
        # Convert single curly braces to double curly braces for cloze cards
        if card_type == 'cloze' and front_content:
            front_content = convert_single_to_double_braces(front_content)
        
        # Handle vignette content with proper formatting
        vignette_data = card_info.get('vignette', '')
        vignette_content = ''
        if vignette_data:
            if isinstance(vignette_data, dict):
                clinical_case = vignette_data.get('clinical_case', '')
                explanation_text = vignette_data.get('explanation', '')
                
                # Format clinical case with proper choice layout
                if clinical_case:
                    import re
                    
                    # Split the clinical case to separate patient presentation from choices
                    case_parts = clinical_case.split('?', 1)
                    if len(case_parts) == 2:
                        patient_case = case_parts[0].strip() + '?'
                        choices_section = case_parts[1].strip()
                        
                        # Format the choices with proper line breaks (A, B, C, D, E)
                        formatted_choices = choices_section
                        formatted_choices = re.sub(r'\s*([A-E]\.?\)?\s*)', r'<br>\1 ', formatted_choices)
                        formatted_choices = formatted_choices.lstrip('<br>')
                        
                        # Add proper formatting for "Correct Answer:"
                        formatted_choices = formatted_choices.replace('Correct Answer:', '<br><br><strong>Correct Answer:</strong>')
                        
                        # Build the complete vignette
                        complete_case = f'{patient_case}<br><br>{formatted_choices}'
                        
                        # Add the explanation if provided
                        if explanation_text:
                            complete_case += f'<br><br><strong>Explanation:</strong><br>{explanation_text}'
                        
                        vignette_content = f'<div style="color: #1976d2; line-height: 1.25;">{complete_case}</div>'
                    else:
                        # Fallback for cases without question mark
                        vignette_content = f'<div style="color: #1976d2; line-height: 1.25;">{clinical_case}'
                        if explanation_text:
                            vignette_content += f'<br><br><strong>Explanation:</strong><br>{explanation_text}'
                        vignette_content += '</div>'
            else:
                vignette_content = str(vignette_data)
        
        # Handle mnemonic content
        mnemonic_content = card_info.get('mnemonic', '')
        
        # Handle image content
        image_content = ''
        if 'image' in card_info and card_info['image']:
            image_data = card_info['image']
            if isinstance(image_data, dict) and 'url' in image_data:
                # Download and embed the image
                image_filename = download_image_from_url(image_data['url'], media_files)
                if image_filename:
                    caption = image_data.get('caption', '')
                    if caption:
                        image_content = f'<img src="{image_filename}" alt="{caption}" style="max-width: 100%; height: auto;"><br><small>{caption}</small>'
                    else:
                        image_content = f'<img src="{image_filename}" style="max-width: 100%; height: auto;">'
            elif isinstance(image_data, str):
                # Simple filename format
                image_content = f'<img src="{image_data}" style="max-width: 100%; height: auto;">'
        
        # Create the note with all fields
        note = genanki.Note(
            model=my_model,
            fields=[
                front_content,           # Front
                back_content,            # Back  
                extra_content,           # Extra
                vignette_content,        # Vignette
                mnemonic_content,        # Mnemonic
                image_content            # Image
            ],
            tags=[tag.replace(' ', '_') for tag in card_info.get('tags', [])]
        )
        
        my_deck.add_note(note)
    
    # Generate the package with media files
    my_package = genanki.Package(my_deck)
    if media_files:
        my_package.media_files = media_files
    
    my_package.write_to_file(output_filename)
    return my_deck

def download_image_from_url(url, media_files_list):
    """Download image from URL and return local filename for Anki embedding"""
    try:
        response = requests.get(url, stream=True, timeout=10)
        response.raise_for_status()
        
        # Generate unique filename
        file_extension = '.png'  # Default to PNG
        if 'content-type' in response.headers:
            content_type = response.headers['content-type'].lower()
            if 'jpeg' in content_type or 'jpg' in content_type:
                file_extension = '.jpg'
            elif 'gif' in content_type:
                file_extension = '.gif'
            elif 'svg' in content_type:
                file_extension = '.svg'
        
        filename = f"image_{str(uuid.uuid4())[:8]}{file_extension}"
        filepath = os.path.join(tempfile.gettempdir(), filename)
        
        # Save the image
        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        # Add to media files list for genanki
        media_files_list.append(filepath)
        
        return filename
    except Exception as e:
        print(f"Error downloading image from {url}: {e}")
        return None