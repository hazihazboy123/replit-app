import os
import json
import html
import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks, Path
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field, validator
import uvicorn
import genanki
import random

# Create directories
os.makedirs("temp", exist_ok=True)
os.makedirs("static", exist_ok=True)
os.makedirs("templates", exist_ok=True)

app = FastAPI(title="Medical Flashcard Generator")

# ASGI application for gunicorn compatibility
asgi_app = app

# Mount static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Pydantic models
class FlashcardData(BaseModel):
    front: str = Field(..., min_length=1)
    back: str = Field(..., min_length=1)
    explanation: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    category: str = "General"
    images: List[str] = Field(default_factory=list)
    mnemonic: Optional[str] = None
    clinical_vignette: Optional[str] = None
    
    @validator('front', 'back', 'explanation', 'mnemonic', 'clinical_vignette', pre=True)
    def clean_html(cls, v):
        if isinstance(v, str):
            return html.unescape(v).strip()
        return v

class N8nWebhookPayload(BaseModel):
    workflow_id: Optional[str] = None
    execution_id: Optional[str] = None
    data: Dict[str, Any] = Field(default_factory=dict)
    cards: Optional[List[FlashcardData]] = None
    
    @validator('cards', pre=True, always=True)
    def extract_cards(cls, v, values):
        if v:
            return v
        
        # Extract from data field
        data = values.get('data', {})
        cards = []
        
        # Handle different n8n data structures
        if isinstance(data, list):
            for item in data:
                try:
                    cards.append(FlashcardData(**item))
                except:
                    pass
        elif isinstance(data, dict):
            if 'items' in data:
                for item in data['items']:
                    try:
                        cards.append(FlashcardData(**item))
                    except:
                        pass
            elif 'front' in data and 'back' in data:
                try:
                    cards.append(FlashcardData(**data))
                except:
                    pass
        
        return cards

# Anki generation service
class AnkiGenerator:
    def __init__(self):
        self.medical_model = self._create_medical_model()
    
    def _create_medical_model(self):
        return genanki.Model(
            1607392319,
            'Medical Flashcard Model',
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
                            <div class="clinical-vignette">{{Clinical_Vignette}}</div>
                            {{/Clinical_Vignette}}
                            <div class="question">{{Question}}</div>
                            {{#Images}}<div class="image-container">{{Images}}</div>{{/Images}}
                        </div>
                    ''',
                    'afmt': '''
                        {{FrontSide}}
                        <hr id="answer">
                        <div class="answer">{{Answer}}</div>
                        {{#Explanation}}<div class="explanation">{{Explanation}}</div>{{/Explanation}}
                        {{#Mnemonics}}<div class="mnemonic">{{Mnemonics}}</div>{{/Mnemonics}}
                        <div class="tags">{{Tags}}</div>
                    '''
                }
            ],
            css='''
                .card {
                    font-family: "Helvetica Neue", Arial, sans-serif;
                    font-size: 18px;
                    line-height: 1.6;
                    color: #333;
                    background-color: #fff;
                    padding: 20px;
                    max-width: 800px;
                    margin: 0 auto;
                }
                
                .clinical-vignette {
                    background-color: #f8f9fa;
                    border-left: 4px solid #007bff;
                    padding: 15px;
                    margin-bottom: 20px;
                    border-radius: 4px;
                }
                
                .question {
                    font-weight: bold;
                    font-size: 20px;
                    margin-bottom: 15px;
                    color: #2c3e50;
                }
                
                .answer {
                    background-color: #e8f5e8;
                    padding: 15px;
                    border-radius: 4px;
                    margin-bottom: 15px;
                }
                
                .explanation {
                    background-color: #fff3cd;
                    border: 1px solid #ffeaa7;
                    padding: 15px;
                    border-radius: 4px;
                    margin-bottom: 15px;
                }
                
                .mnemonic {
                    background-color: #e1f5fe;
                    border-left: 4px solid #29b6f6;
                    padding: 15px;
                    font-style: italic;
                    border-radius: 4px;
                    margin-bottom: 15px;
                }
                
                .image-container {
                    text-align: center;
                    margin: 15px 0;
                }
                
                .image-container img {
                    max-width: 100% !important;
                    height: auto !important;
                    border-radius: 4px;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                }
                
                .tags {
                    font-size: 14px;
                    color: #666;
                    margin-top: 15px;
                }
                
                /* Drug and dosage styling */
                .drug-name {
                    font-weight: bold;
                    color: #e74c3c;
                    background-color: #fdf2f2;
                    padding: 2px 6px;
                    border-radius: 3px;
                }
                
                .dosage {
                    font-weight: bold;
                    color: #27ae60;
                    background-color: #f0f8f0;
                    padding: 2px 6px;
                    border-radius: 3px;
                }
                
                /* Tables */
                table {
                    width: 100%;
                    border-collapse: collapse;
                    margin: 15px 0;
                }
                
                th, td {
                    border: 1px solid #ddd;
                    padding: 8px;
                    text-align: left;
                }
                
                th {
                    background-color: #f2f2f2;
                    font-weight: bold;
                }
                
                /* Mobile optimization */
                .mobile .card {
                    font-size: 16px;
                    padding: 15px;
                }
                
                .mobile img {
                    max-width: 300px !important;
                    max-height: 300px !important;
                }
                
                /* Night mode support */
                .nightMode .card {
                    background-color: #2c2c2c;
                    color: #e0e0e0;
                }
                
                .nightMode .clinical-vignette {
                    background-color: #3a3a3a;
                    border-left-color: #5dade2;
                }
                
                .nightMode .answer {
                    background-color: #2e4a2e;
                }
                
                .nightMode .explanation {
                    background-color: #4a3d1f;
                    border-color: #6b5821;
                }
            '''
        )
    
    async def generate_deck(self, deck_name: str, cards: List[FlashcardData]) -> str:
        # Create deck
        deck_id = abs(hash(deck_name + str(datetime.now()))) % (10**9)
        deck = genanki.Deck(deck_id, deck_name)
        
        # Add cards
        for card in cards:
            # Format images
            images_html = ""
            if card.images:
                images_html = "".join([f'<img src="{img}">' for img in card.images])
            
            # Create note
            note = genanki.Note(
                model=self.medical_model,
                fields=[
                    card.clinical_vignette or "",
                    card.front,
                    card.back,
                    card.explanation or "",
                    ", ".join(card.tags) if card.tags else "",
                    images_html,
                    card.mnemonic or ""
                ],
                tags=card.tags
            )
            deck.add_note(note)
        
        # Generate file
        filename = f"{deck_name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.apkg"
        filepath = os.path.join("temp", filename)
        
        package = genanki.Package(deck)
        package.write_to_file(filepath)
        
        return filename

# Initialize services
anki_generator = AnkiGenerator()

# API endpoints
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/api/webhook/n8n")
async def receive_n8n_webhook(payload: N8nWebhookPayload, background_tasks: BackgroundTasks):
    try:
        if not payload.cards:
            raise HTTPException(status_code=400, detail="No valid flashcard data found")
        
        # Generate deck name
        deck_name = f"Medical Flashcards - {datetime.now().strftime('%Y-%m-%d')}"
        if payload.workflow_id:
            deck_name = f"n8n_{payload.workflow_id}"
        
        # Generate Anki file
        filename = await anki_generator.generate_deck(deck_name, payload.cards)
        
        # Schedule cleanup after 24 hours
        background_tasks.add_task(cleanup_file, filename, 86400)
        
        return {
            "success": True,
            "filename": filename,
            "deck_name": deck_name,
            "card_count": len(payload.cards),
            "download_url": f"/api/download/{filename}"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/download/{filename}")
async def download_file(filename: str = Path(..., regex=r"^[a-zA-Z0-9_\-\.]+\.apkg$")):
    filepath = os.path.join("temp", filename)
    
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(
        path=filepath,
        filename=filename,
        media_type='application/octet-stream'
    )

@app.post("/api/generate")
async def generate_from_ui(cards_data: List[FlashcardData]):
    try:
        deck_name = f"Medical Flashcards - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        filename = await anki_generator.generate_deck(deck_name, cards_data)
        
        return {
            "success": True,
            "filename": filename,
            "download_url": f"/api/download/{filename}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Legacy Flask compatibility endpoints
@app.post("/api/enhanced-medical")
async def enhanced_medical_legacy(request: Request):
    try:
        data = await request.json()
        
        # Extract cards from various formats
        cards = []
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict) and 'cards' in item:
                    cards.extend(item['cards'])
                elif isinstance(item, dict) and 'front' in item and 'back' in item:
                    cards.append(item)
        elif isinstance(data, dict):
            if 'cards' in data:
                cards = data['cards']
            elif 'front' in data and 'back' in data:
                cards = [data]
        
        # Convert to FlashcardData objects
        flashcard_objects = []
        for card in cards:
            try:
                flashcard_data = FlashcardData(
                    front=card.get('front', ''),
                    back=card.get('back', ''),
                    explanation=card.get('explanation', ''),
                    mnemonic=card.get('mnemonic', ''),
                    clinical_vignette=card.get('vignette', ''),
                    tags=card.get('tags', []),
                    category=card.get('category', 'General')
                )
                flashcard_objects.append(flashcard_data)
            except Exception as e:
                continue
        
        if not flashcard_objects:
            raise HTTPException(status_code=400, detail="No valid cards found")
        
        deck_name = f"Medical_Deck_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        filename = await anki_generator.generate_deck(deck_name, flashcard_objects)
        
        return {
            "success": True,
            "filename": filename,
            "deck_name": deck_name,
            "cards_processed": len(flashcard_objects),
            "download_url": f"/api/download/{filename}",
            "full_download_url": f"{request.base_url}api/download/{filename}",
            "message": f"Successfully generated deck with {len(flashcard_objects)} cards"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "Medical Flashcard Generator",
        "version": "6.0.0",
        "framework": "FastAPI",
        "features": ["n8n_webhook", "ui_interface", "async_processing"],
        "timestamp": datetime.now().isoformat()
    }

async def cleanup_file(filename: str, delay: int):
    await asyncio.sleep(delay)
    filepath = os.path.join("temp", filename)
    if os.path.exists(filepath):
        os.remove(filepath)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)