# Flexible JSON Parser for Medical Flashcard Converter

## Overview

The Flexible JSON Parser is a robust parsing system designed to handle various JSON formats from n8n automation workflows and Large Language Models (LLMs). It specifically addresses the challenge of parsing triple-layer JSON structures and recovering from common JSON malformations.

## Key Features

### 1. **Triple-Layer JSON Parsing**
Handles n8n's complex output format:
```json
[
  {
    "output": "```json\n{\"cards\": [...]}```"
  }
]
```

### 2. **Multiple Parsing Strategies**
- Standard JSON parsing
- n8n triple-layer format detection
- Markdown code block extraction
- Common issue cleanup (trailing commas, quotes)
- JSON repair for malformed structures

### 3. **Robust Error Recovery**
- Progressive fallback strategies
- Detailed error logging
- Helpful error messages with hints

### 4. **Production-Ready Features**
- Request logging for debugging
- Performance metrics
- Backward compatibility
- Clear error feedback

## API Endpoints

### `/api/flexible-convert` (NEW)
The main endpoint for flexible JSON parsing.

**Method:** POST  
**Content-Type:** text/plain or application/json

**Request Body Examples:**

1. **n8n Format (Triple-Layer)**
```json
[
  {
    "output": "```json\n{\n  \"cards\": [\n    {\n      \"front\": \"Question?\",\n      \"back\": \"Answer\"\n    }\n  ]\n}\n```"
  }
]
```

2. **Direct JSON**
```json
{
  "cards": [
    {
      "front": "What is hypertension?",
      "back": "High blood pressure",
      "tags": ["cardiology"]
    }
  ]
}
```

3. **LLM Output with Extra Text**
```
Here's your flashcard data:
```json
{
  "cards": [
    {
      "front": "Question",
      "back": "Answer"
    }
  ]
}
```

**Response:**
```json
{
  "success": true,
  "status": "completed",
  "deck_name": "Medical_Deck_20240115_143022",
  "cards_processed": 8,
  "media_files_downloaded": 0,
  "file_size": 2048,
  "filename": "Medical_Deck_20240115_143022_1705333822.apkg",
  "download_url": "/download/Medical_Deck_20240115_143022_1705333822.apkg",
  "full_download_url": "http://localhost:5000/download/Medical_Deck_20240115_143022_1705333822.apkg",
  "parsing_strategy": "n8n_triple_layer",
  "message": "Successfully generated deck with 8 cards"
}
```

### Legacy Endpoints (Still Supported)

- `/api/enhanced-medical` - Original endpoint with standard JSON parsing
- `/api/simple` - Alias for enhanced-medical endpoint

## Parsing Strategies

The parser attempts multiple strategies in order:

1. **Standard Parsing** - Direct JSON.parse()
2. **n8n Detection** - Looks for "output" field with markdown
3. **Cleanup Parsing** - Removes common issues like trailing commas
4. **Extraction** - Extracts JSON from surrounding text
5. **Repair** - Attempts to fix malformed JSON

## Card Format

Each card supports the following fields:

### Required Fields
- `front` - Question or prompt (HTML supported)
- `back` - Answer (HTML supported)

### Optional Fields
- `explanation` - Detailed explanation (HTML)
- `clinical_vignette` - Clinical case scenario (HTML)
- `mnemonic` - Memory aid (HTML)
- `notes` - Additional notes (HTML, displayed last)
- `images` - Array of image URLs or objects with url/caption
- `tags` - Array of tags or comma-separated string
- `difficulty` - Difficulty level (easy/medium/hard)
- `type` - Card type (basic/cloze)

## Example Usage

### Using cURL

```bash
# Send n8n format data
curl -X POST http://localhost:5000/api/flexible-convert \
  -H "Content-Type: text/plain" \
  -d '[{"output": "```json\n{\"cards\": [{\"front\": \"Q\", \"back\": \"A\"}]}\n```"}]'

# Send direct JSON
curl -X POST http://localhost:5000/api/flexible-convert \
  -H "Content-Type: application/json" \
  -d '{"cards": [{"front": "Question?", "back": "Answer"}]}'
```

### Using Python

```python
import requests

# n8n format
n8n_data = '''[
  {
    "output": "```json\\n{\\"cards\\": [{\\"front\\": \\"Q\\", \\"back\\": \\"A\\"}]}\\n```"
  }
]'''

response = requests.post(
    "http://localhost:5000/api/flexible-convert",
    data=n8n_data,
    headers={"Content-Type": "text/plain"}
)

if response.status_code == 200:
    result = response.json()
    print(f"Download URL: {result['full_download_url']}")
```

## Error Handling

The API provides detailed error messages with hints:

```json
{
  "error": "Failed to parse input data",
  "message": "Failed to parse JSON. Errors: Standard parsing: ...",
  "hints": [
    "Ensure data is valid JSON or wrapped in supported format",
    "For n8n: Check that output contains markdown-wrapped JSON",
    "Remove any trailing commas in JSON",
    "Ensure all strings are properly quoted"
  ],
  "data_preview": "First 500 characters of input..."
}
```

## Testing

Run the test script to verify the parser:

```bash
# Test the parser directly
python test_flexible_parser.py

# Test the API (requires Flask app running)
python app.py  # In one terminal
python test_flexible_parser.py  # In another terminal
```

## Performance

- Parsing typically completes in <100ms for standard inputs
- Large batches (100+ cards) are handled efficiently
- Failed parsing strategies are logged for debugging
- Successful strategy is returned in the response

## Logging

The parser logs detailed information:
- Raw input preview (first 500 chars)
- Parsing attempts and strategies used
- Success/failure with timing information
- Error details for debugging

Set logging level in your Flask app:
```python
logging.basicConfig(level=logging.DEBUG)
```

## Common Issues and Solutions

### Issue: n8n data not parsing
**Solution:** Ensure the output field contains markdown code blocks with \`\`\`json

### Issue: Trailing commas causing errors
**Solution:** The parser automatically removes trailing commas

### Issue: LLM adds extra text
**Solution:** The parser extracts JSON from surrounding text

### Issue: Quotes not properly escaped
**Solution:** The repair strategy attempts to fix quote issues

## Integration with n8n

In your n8n workflow:

1. Use the HTTP Request node
2. Set URL to `http://your-server/api/flexible-convert`
3. Method: POST
4. Body Content Type: Raw
5. Body: Your JSON data (will be automatically wrapped by n8n)

The parser handles n8n's automatic wrapping of data.

## Version History

- **v11.0.0** - Added flexible JSON parsing with n8n support
- **v10.5.1** - Enhanced medical flashcard features
- **v9.2.0** - Improved spacing and formatting