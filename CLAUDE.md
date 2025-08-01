# CLAUDE.md - SynapticRecall Medical Flashcard Converter

## 🧠 Project Overview

SynapticRecall Medical Flashcard Converter is a critical component of the larger SynapticRecall SaaS platform. It serves as a specialized microservice that converts JSON-formatted medical flashcard data into Anki-compatible .apkg files, specifically designed for medical students and healthcare professionals.

### Architecture Context

```
┌─────────────────┐     ┌─────────────────┐     ┌──────────────────┐
│   SynapticRecall│     │                 │     │                  │
│   Frontend      │────▶│  n8n Automation │────▶│  Flask API       │
│   (PDF Upload)  │     │  (Processing)   │     │  (This Service)  │
└─────────────────┘     └─────────────────┘     └──────────────────┘
                                                          │
                                                          ▼
                                                  ┌──────────────────┐
                                                  │   .apkg File     │
                                                  │   (Download)     │
                                                  └──────────────────┘
```

## 🎯 Core Functionality

### Primary Purpose
Convert complex, LLM-generated JSON medical flashcard data (with potential formatting issues) into perfectly formatted Anki decks with AnKing-compatible styling.

### Key Features
1. **Flexible JSON Parsing**: Handles triple-layer wrapped JSON from n8n automation
2. **Medical-Specific Formatting**: Clinical vignettes, mnemonics, high-yield content
3. **AnKing Compatibility**: Full compatibility with AnKing Master v8 note type
4. **Robust Error Handling**: Gracefully handles malformed JSON from LLMs
5. **Image Processing**: Downloads and embeds medical diagrams
6. **Permanent Storage**: Generated files never expire

## 🔧 Technical Implementation

### Core Technologies
- **Backend**: Python 3.9+ with Flask 2.0
- **Anki Generation**: genanki library
- **HTML Processing**: BeautifulSoup4
- **Package Management**: UV (modern Python package manager)
- **WSGI Server**: Gunicorn for production

### File Structure
```
/
├── app.py                    # Main Flask application
├── flexible_parser.py        # Robust JSON parsing system
├── main.py                   # Entry point
├── templates/               
│   ├── base.html            # Base template
│   └── index.html           # UI interface
├── static/js/main.js        # Frontend JavaScript
├── pyproject.toml           # Dependencies (UV)
└── downloads/               # Generated .apkg storage
```

## 🌐 API Endpoints

### Primary Endpoints

#### 1. `/api/flexible-convert` (NEW - Recommended)
**Purpose**: Handle n8n automation output with maximum flexibility

**Request Format**:
```json
[
  {
    "output": "```json\n{\"cards\": [...]}\n```"
  }
]
```

**Features**:
- Triple-layer JSON parsing
- Markdown code block removal
- Multiple fallback strategies
- Detailed error reporting

#### 2. `/api/enhanced-medical` (Production)
**Purpose**: Standard medical flashcard conversion

**Request Format**:
```json
{
  "cards": [
    {
      "front": "Question HTML",
      "back": "Answer HTML",
      "tags": ["medical", "cardiology"],
      "vignette": {
        "clinical_case": "HTML content",
        "explanation": "HTML content"
      }
    }
  ]
}
```

#### 3. `/api/simple` (Legacy)
**Purpose**: Backward compatibility endpoint

### Health & Utility Endpoints
- `GET /api/health` - System health check
- `GET /download/<filename>` - Permanent download links
- `POST /api/cleanup` - Administrative cleanup (protected)

## 🔄 n8n Integration Details

### Expected Input Format
The n8n automation sends data in a specific triple-wrapped format:

1. **Outer Array**: Contains multiple batch objects
2. **Output Field**: Each object has an "output" string field
3. **Markdown Wrapper**: JSON is wrapped in \`\`\`json code blocks
4. **Inner JSON**: Actual card data with complex HTML

### Parsing Strategy
```python
# Simplified parsing flow
for item in input_array:
    json_str = item['output'].replace('```json\n', '').replace('\n```', '')
    cards_data = json.loads(json_str)
    all_cards.extend(cards_data['cards'])
```

### Batch Processing
- n8n sends cards in batches of 8
- System handles unlimited batches
- Maintains order and relationships

## 🎨 Card Structure & Styling

### Supported Card Types

#### 1. Basic Cards
```json
{
  "type": "basic",
  "front": "<div style=\"font-size: 1.7em;\">Question</div>",
  "back": "<div style=\"font-size: 1.7em;\">Answer</div>",
  "tags": ["medical"],
  "image": "url_to_image"
}
```

#### 2. Cloze Deletion Cards
```json
{
  "type": "cloze",
  "text": "The {{c1::heart}} pumps {{c2::blood}}",
  "tags": ["anatomy"]
}
```

#### 3. Clinical Vignette Cards
Complex cards with interactive reveal functionality:
- Patient presentation
- Lab values with visual formatting
- Interactive "Think First... Then Reveal" buttons
- Detailed explanations with high-yield pearls

### HTML Features Preserved
- **Inline Styles**: All CSS preserved exactly
- **JavaScript**: onclick handlers for reveal functionality
- **Animations**: CSS animations (gradient-shift, pulse-glow)
- **Unicode**: Full emoji and symbol support
- **Complex Layouts**: Tables, nested divs, flexbox

### AnKing Compatibility
- Arial Greek font for medical exam consistency
- Red highlighting for key concepts
- Blue styling for clinical vignettes
- Gold styling for mnemonics
- Hierarchical tagging with "::" separators

## 🛡️ Error Handling & Recovery

### Flexible Parser Strategies
1. **Clean JSON**: Direct parsing
2. **Wrapped JSON**: Extract from markdown blocks
3. **String Repair**: Fix common JSON errors
4. **Fallback Parsing**: Multiple recovery attempts
5. **Detailed Logging**: Track parsing strategies

### Common Issues Handled
- Trailing commas in JSON
- Unescaped quotes in HTML
- Unicode characters
- Large payloads (100+ cards)
- Malformed wrapper structures

### Error Response Format
```json
{
  "error": "Error type",
  "message": "Detailed description",
  "hint": "Suggestion for fixing",
  "status": 400
}
```

## 🚀 Performance Optimizations

### Parsing Performance
- <100ms for typical 8-card batches
- Stream processing for large datasets
- Efficient memory usage
- Caching for repeated operations

### Image Handling
- Parallel image downloads
- 70% sizing optimization
- Error recovery for failed downloads
- Support for multiple formats

## 📊 Monitoring & Logging

### Logging Strategy
```python
app.logger.info(f"Parsing attempt {attempt}: {strategy}")
app.logger.error(f"Parse failed: {error}")
app.logger.info(f"Generated deck: {deck_name} with {card_count} cards")
```

### Key Metrics
- Parse success rate
- Average processing time
- Card generation count
- Error frequency by type

## 🔐 Security Considerations

### Input Validation
- Size limits on payloads
- HTML sanitization (preserving medical formatting)
- Safe file naming for downloads
- Protected administrative endpoints

### Best Practices
- Never expose internal errors
- Validate all user input
- Sanitize file paths
- Rate limiting considerations

## 🧪 Testing Guidelines

### Test Cases
1. **Standard n8n format** - Triple-wrapped JSON
2. **Malformed JSON** - Missing quotes, trailing commas
3. **Large batches** - 100+ cards
4. **Complex HTML** - Nested styles, JavaScript
5. **Image handling** - Various URL formats

### Sample Test
```bash
# Test flexible parser
curl -X POST http://localhost:5000/api/flexible-convert \
  -H "Content-Type: text/plain" \
  -d @n8n_example.json
```

## 🔄 Version History

### v11.0.0 (Current)
- Added flexible parser for n8n integration
- Enhanced error handling
- Improved logging system
- Maintained backward compatibility

### v10.5.1
- Font size preservation
- Bug fixes

### Previous Versions
- See git history for detailed changes

## 📈 Future Enhancements

### Planned Features
1. **Batch Progress Tracking**: Real-time conversion status
2. **Format Validation**: Pre-flight checks for n8n data
3. **Custom Styling Options**: User-defined card templates
4. **Analytics Dashboard**: Usage statistics and error trends

### Potential Optimizations
1. **Async Processing**: Handle larger batches
2. **Redis Caching**: Improve performance
3. **WebSocket Updates**: Real-time progress
4. **Multi-format Export**: Support other flashcard apps

## 🤝 Integration Notes

### For n8n Developers
- Always send data in the expected wrapper format
- Batch size of 8 cards is optimal
- Include all required fields for each card type
- Test with the health endpoint first

### For Frontend Developers
- Poll download endpoint for file availability
- Handle both success and error responses
- Display parsing strategy feedback to users
- Implement retry logic for failed conversions

## 🐛 Troubleshooting

### Common Issues

1. **"Failed to parse JSON"**
   - Check for proper wrapper format
   - Verify no syntax errors in HTML
   - Ensure proper escaping of quotes

2. **"Image download failed"**
   - Verify image URLs are accessible
   - Check for CORS issues
   - Ensure proper URL encoding

3. **"Deck generation failed"**
   - Validate card structure
   - Check for required fields
   - Verify HTML is well-formed

### Debug Mode
Enable detailed logging:
```python
app.logger.setLevel(logging.DEBUG)
```

## 📚 Additional Resources

### Dependencies Documentation
- [Flask](https://flask.palletsprojects.com/)
- [genanki](https://github.com/kerrickstaley/genanki)
- [BeautifulSoup4](https://www.crummy.com/software/BeautifulSoup/)
- [UV Package Manager](https://github.com/astral-sh/uv)

### Medical Flashcard Standards
- [AnKing Medical](https://www.ankingmed.com/)
- [Anki Manual](https://docs.ankiweb.net/)

### Related Projects
- SynapticRecall Frontend
- n8n Automation Workflows
- Medical Content Generation Pipeline

---

## 📞 Support & Contact

For issues or questions regarding this service:
1. Check the error logs first
2. Verify input format matches examples
3. Test with the provided sample data
4. Create an issue in the repository

This service is a critical component of the SynapticRecall platform. Handle with care and always test changes thoroughly before deployment.