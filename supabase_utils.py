"""
Supabase utilities for SynapticRecall Flashcard Converter
Handles deck uploads with intelligent naming based on lecture tags
"""
import os
import logging
from datetime import datetime
from typing import Optional, Dict, List
from supabase import create_client, Client

logger = logging.getLogger(__name__)

# Supabase configuration - matching your existing setup
SUPABASE_URL = "https://tsebqscuuafnekssagyl.supabase.co"
SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRzZWJxc2N1dWFmbmVrc3NhZ3lsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTA3ODgwNjksImV4cCI6MjA2NjM2NDA2OX0.u-Kh2l4gpOKsotE2G-6y1d9sk2IJitcv7-GZMK2rvm0"
SUPABASE_BUCKET = "synapticrecall-links"

# Initialize Supabase client
try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
    SUPABASE_ENABLED = True
    logger.info("✅ Supabase client initialized for deck storage")
except Exception as e:
    logger.error(f"❌ Failed to initialize Supabase: {e}")
    supabase = None
    SUPABASE_ENABLED = False

def extract_lecture_name_from_tags(tags: List[str]) -> str:
    """
    Extract the lecture name from tags by filtering out system tags
    
    Args:
        tags: List of tags from the LLM
        
    Returns:
        The lecture name extracted from tags
    """
    if not tags:
        return "Medical_Lecture"
    
    # System tags to filter out
    system_tags = ["synapticrecall", "synaptic_recall", "medical", "flashcard", "anki"]
    
    # Find the first tag that's not a system tag
    for tag in tags:
        tag_lower = tag.lower().strip()
        if not any(sys_tag in tag_lower for sys_tag in system_tags):
            # This is likely the lecture name
            # Clean it up for use as a filename
            clean_name = "".join(c for c in tag if c.isalnum() or c in (' ', '-', '_')).strip()
            if clean_name:
                return clean_name
    
    # If all tags are system tags, use the first non-synapticrecall tag
    for tag in tags:
        if "synapticrecall" not in tag.lower():
            clean_name = "".join(c for c in tag if c.isalnum() or c in (' ', '-', '_')).strip()
            if clean_name:
                return clean_name
    
    # Fallback
    return "Medical_Lecture"

def generate_smart_deck_name(cards_data: List[Dict], custom_name: Optional[str] = None) -> str:
    """
    Generate a smart deck name based on lecture tags or custom name
    
    Args:
        cards_data: List of card dictionaries
        custom_name: Optional custom deck name
        
    Returns:
        Smart deck name based on lecture content
    """
    if custom_name:
        return custom_name
    
    # Try to extract lecture name from the first few cards' tags
    all_tags = []
    for i, card in enumerate(cards_data[:5]):  # Check first 5 cards
        if isinstance(card, dict):
            tags = card.get('tags', [])
            if isinstance(tags, list):
                all_tags.extend(tags)
            elif isinstance(tags, str):
                # Handle comma-separated or :: separated tags
                if '::' in tags:
                    all_tags.extend(tags.split('::'))
                elif ',' in tags:
                    all_tags.extend(tags.split(','))
                else:
                    all_tags.append(tags)
    
    # Get unique tags
    unique_tags = list(set(tag.strip() for tag in all_tags if tag))
    
    # Extract lecture name from tags
    lecture_name = extract_lecture_name_from_tags(unique_tags)
    
    return lecture_name

def upload_deck_to_supabase(
    local_file_path: str,
    deck_name: str,
    session_id: Optional[str] = None,
    user_id: Optional[str] = None
) -> Optional[Dict]:
    """
    Upload .apkg file to Supabase with organized folder structure
    
    Args:
        local_file_path: Path to the generated .apkg file
        deck_name: Smart deck name (lecture name)
        session_id: Optional session ID from n8n
        user_id: Optional user ID
        
    Returns:
        Dict with permanent public URL and metadata
    """
    if not SUPABASE_ENABLED or not supabase:
        logger.warning("Supabase not available - using local storage")
        return None
    
    try:
        # Read the file
        with open(local_file_path, 'rb') as f:
            file_data = f.read()
        
        # Create organized path: YYYY/MM/sessions/[session_id]/lecture_name.apkg
        now = datetime.now()
        
        # Clean deck name for filename
        safe_deck_name = "".join(c for c in deck_name if c.isalnum() or c in (' ', '-', '_')).strip()
        if not safe_deck_name:
            safe_deck_name = "medical_deck"
        
        # Build path components
        year_month = f"{now.year}/{now.month:02d}"
        
        if session_id:
            # If we have session ID, use it for organization
            storage_path = f"{year_month}/sessions/{session_id}/{safe_deck_name}.apkg"
        else:
            # Fallback path without session ID
            timestamp = now.strftime("%Y%m%d_%H%M%S")
            storage_path = f"{year_month}/decks/{safe_deck_name}_{timestamp}.apkg"
        
        # Upload to Supabase
        logger.info(f"📤 Uploading deck to Supabase: {storage_path}")
        
        response = supabase.storage.from_(SUPABASE_BUCKET).upload(
            storage_path,
            file_data,
            file_options={
                "content-type": "application/octet-stream",
                "cache-control": "3600",
                "upsert": "true"
            }
        )
        
        # Generate permanent public URL (no expiration needed for public bucket)
        public_url = f"{SUPABASE_URL}/storage/v1/object/public/{SUPABASE_BUCKET}/{storage_path}"
        
        # Delete local file after successful upload
        try:
            os.remove(local_file_path)
            logger.info(f"🗑️ Deleted local file: {local_file_path}")
        except Exception as e:
            logger.warning(f"Could not delete local file: {e}")
        
        result = {
            "success": True,
            "download_url": public_url,
            "storage_path": storage_path,
            "deck_name": deck_name,
            "uploaded_at": now.isoformat(),
            "permanent": True,
            "message": f"Deck '{deck_name}' uploaded successfully"
        }
        
        logger.info(f"✅ Upload successful: {public_url}")
        return result
        
    except Exception as e:
        logger.error(f"❌ Supabase upload failed: {str(e)}")
        return None

def check_supabase_health() -> Dict:
    """Check if Supabase is properly configured and accessible"""
    if not SUPABASE_ENABLED:
        return {
            "status": "disabled",
            "message": "Supabase not configured"
        }
    
    try:
        # Try to list files in the bucket
        result = supabase.storage.from_(SUPABASE_BUCKET).list()
        return {
            "status": "healthy",
            "bucket": SUPABASE_BUCKET,
            "files_count": len(result) if result else 0,
            "message": "Supabase storage is operational"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Supabase health check failed: {str(e)}"
        }