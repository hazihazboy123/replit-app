#!/usr/bin/env python3
"""
Test script to validate perfect medical Anki card generation
Based on the comprehensive PDF guide recommendations
"""

import json
import requests
import tempfile
import os

# Test data with comprehensive medical card features
test_data = {
    "deck_name": "Perfect Medical Cards Test",
    "cards": [
        {
            "question": "What is the mechanism of action of Aspirin?",
            "answer": "Irreversibly inhibits COX-1 and COX-2 enzymes by acetylating serine residues",
            "mnemonic": "ASA = Acetylates Serine Always",
            "vignette": "A 65-year-old patient with chest pain is given aspirin 325mg in the emergency department",
            "clinical_correlation": "Low-dose aspirin (81mg) is used for cardiovascular protection due to its antiplatelet effects",
            "notes": "Important for cardiology, pain management, and USMLE Step 1",
            "source": "First Aid 2024, Page 487",
            "tags": ["Pharmacology", "NSAIDs", "Cardiovascular"]
        },
        {
            "cloze_text": "{{c1::Myocardial infarction}} is caused by {{c2::coronary artery occlusion}} leading to {{c3::myocardial necrosis}}",
            "mnemonic": "MI = Muscle Ischemia",
            "vignette": "45-year-old male presents with crushing chest pain radiating to left arm",
            "clinical_correlation": "ST-elevation indicates transmural infarction requiring immediate PCI",
            "notes": "Key concept for USMLE Step 1 and cardiology rotations",
            "source": "Pathoma Chapter 7",
            "tags": ["Cardiology", "Pathophysiology", "Emergency Medicine"]
        },
        {
            "front": "Define hepatomegaly",
            "back": "Enlargement of the liver beyond normal size (>12cm in MCL)",
            "mnemonic": "Hepato = liver, megaly = large",
            "vignette": "Patient presents with RUQ fullness and palpable liver edge 4cm below costal margin",
            "clinical_correlation": "Associated with heart failure, fatty liver, malignancy, or storage diseases",
            "notes": "Physical exam finding with multiple differential diagnoses",
            "source": "Bates Physical Examination",
            "tags": ["Physical Exam", "Hepatology", "Internal Medicine"]
        },
        {
            "type": "cloze",
            "front": "The {{c1::sympathetic}} nervous system releases {{c2::norepinephrine}} at most {{c3::postganglionic}} terminals",
            "mnemonic": "Sympathetic = Speed up with NE",
            "vignette": "Fight-or-flight response during stress increases heart rate and blood pressure",
            "clinical_correlation": "Beta-blockers work by antagonizing norepinephrine at cardiac receptors",
            "notes": "Fundamental concept in autonomic pharmacology",
            "source": "Katzung Pharmacology 15th Edition",
            "tags": ["Pharmacology", "Autonomic", "Physiology"]
        }
    ]
}

def test_perfect_cards():
    """Test the perfect medical card generation"""
    print("Testing perfect medical Anki card generation...")
    
    # Test the API endpoint
    url = "http://localhost:5000/api/generate-json"
    
    try:
        response = requests.post(
            url,
            json=test_data,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✓ Success: {result.get('message', 'Cards generated')}")
            print(f"✓ Cards processed: {result.get('cards_processed', 'Unknown')}")
            
            if 'download_url' in result:
                print(f"✓ Download URL: {result['download_url']}")
                
                # Test download
                download_response = requests.get(f"http://localhost:5000{result['download_url']}")
                if download_response.status_code == 200:
                    print(f"✓ Download successful: {len(download_response.content)} bytes")
                    
                    # Save to temp file for verification
                    with tempfile.NamedTemporaryFile(suffix='.apkg', delete=False) as f:
                        f.write(download_response.content)
                        print(f"✓ Saved test file: {f.name}")
                        
                        # Verify file integrity
                        if os.path.getsize(f.name) > 1000:  # Basic size check
                            print("✓ File appears to be valid Anki package")
                        else:
                            print("✗ File seems too small")
                    
                else:
                    print(f"✗ Download failed: {download_response.status_code}")
            else:
                print("✗ No download URL provided")
                
        else:
            print(f"✗ API Error: {response.status_code}")
            try:
                error_data = response.json()
                print(f"Error details: {error_data}")
            except:
                print(f"Error text: {response.text}")
                
    except requests.exceptions.RequestException as e:
        print(f"✗ Request failed: {e}")
    except Exception as e:
        print(f"✗ Unexpected error: {e}")

def test_validation_endpoint():
    """Test the validation endpoint"""
    print("\nTesting validation endpoint...")
    
    url = "http://localhost:5000/api/validate"
    
    try:
        response = requests.post(
            url,
            json=test_data,
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        
        print(f"Validation Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✓ Validation successful: {result.get('message', 'Valid')}")
            print(f"✓ Valid cards found: {result.get('valid_cards', 'Unknown')}")
        else:
            print(f"✗ Validation failed: {response.status_code}")
            
    except Exception as e:
        print(f"✗ Validation error: {e}")

if __name__ == "__main__":
    test_perfect_cards()
    test_validation_endpoint()
    print("\nTest completed!")