# N8N Output Field Reference

## Required Fields

### `cards` (array) - REQUIRED
Container for all flashcard data

## Card Types

### Basic Cards
```json
{
  "type": "basic",
  "front": "Question text",
  "back": "Answer text"
}
```

### Cloze Cards  
```json
{
  "type": "cloze",
  "front": "The {c1::heart} pumps {c2::blood}"
}
```
**Note**: Use single curly braces `{c1::text}` - the system automatically converts to double braces `{{c1::text}}` for Anki compatibility.

## Optional Fields

### `notes` (string)
Additional study notes or context
```json
"notes": "Important for USMLE Step 1"
```

### `tags` (array of strings)
Hierarchical tags for organization
```json
"tags": ["Cardiology", "Physiology", "USMLE"]
```

### `vignette` (object)
Clinical scenarios with questions
```json
"vignette": {
  "clinical_case": "Patient presentation + question + A. B. C. D. E. + Correct Answer: X",
  "explanation": "Educational explanation of why the answer is correct"
}
```

### `image` (string or object)
Image support with automatic download

Simple format:
```json
"image": "filename.jpg"
```

URL with caption:
```json
"image": {
  "url": "https://example.com/image.jpg", 
  "caption": "Description of image"
}
```

Direct URL:
```json
"image": "https://example.com/image.jpg"
```

## Alternative Field Names

The system accepts these variations:
- `front` OR `question`
- `back` OR `answer`
- `notes` OR `additional_notes` OR `extra`

## Complete Example

```json
{
  "cards": [
    {
      "type": "basic",
      "front": "What causes myocardial infarction?",
      "back": "Coronary artery occlusion leading to cardiac muscle death",
      "notes": "Leading cause of death in developed countries",
      "tags": ["Cardiology", "Pathophysiology", "Emergency_Medicine"],
      "vignette": {
        "clinical_case": "A 55-year-old male with chest pain and diaphoresis presents to the ER. ECG shows ST elevation in leads II, III, aVF. What is the most likely diagnosis? A. Pulmonary embolism B. Myocardial infarction C. Panic attack D. Gastroesophageal reflux E. Aortic dissection Correct Answer: B. Myocardial infarction",
        "explanation": "ST elevation in leads II, III, aVF indicates an inferior wall myocardial infarction, typically caused by right coronary artery occlusion. The combination of chest pain, diaphoresis, and characteristic ECG changes confirms the diagnosis."
      },
      "image": {
        "url": "https://example.com/ecg_stemi.jpg",
        "caption": "12-lead ECG showing ST elevation in inferior leads"
      }
    }
  ]
}
```