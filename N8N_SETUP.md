# n8n HTTP Request Setup for SynapticRecall

## Overview

This guide shows you exactly how to configure the HTTP Request node in n8n to send flashcard data to the SynapticRecall API and receive the download link.

## HTTP Request Node Configuration

### 1. Basic Settings

```
Method: POST
URL: https://your-replit-url.repl.co/api/flexible-convert
Authentication: None (unless you add API keys)
```

### 2. Headers

```json
{
  "Content-Type": "text/plain",
  "X-Session-ID": "{{ $workflow.id }}",
  "X-User-ID": "{{ $json.user_id }}"
}
```

**Note**: X-Session-ID and X-User-ID are optional but help with Supabase organization.

### 3. Body Configuration

**Body Content Type**: JSON
**JSON Parameters**: Send JSON

### 4. Input Data Format

The HTTP Request node should receive data in this exact format from your LLM nodes:

```json
[
  {
    "output": "```json\n{\n  \"cards\": [\n    {\n      \"card_id\": 1,\n      \"type\": \"basic\",\n      \"front\": \"<div style=\\\"font-size: 1.7em; text-align: center;\\\">Question HTML</div>\",\n      \"back\": \"<div style=\\\"font-size: 1.7em; text-align: center;\\\">Answer HTML</div>\",\n      \"tags\": [\"Synaptic Recall AI\", \"Lecture-Name\"],\n      \"image\": \"\",\n      \"notes\": \"\",\n      \"mnemonic\": \"\",\n      \"vignette\": {\n        \"clinical_case\": \"<div>Clinical vignette HTML</div>\",\n        \"explanation\": \"<div>Explanation with button HTML</div>\"\n      }\n    }\n  ]\n}\n```"
  }
]
```

### 5. Complete Node JSON (for import)

You can import this directly into n8n:

```json
{
  "nodes": [
    {
      "parameters": {
        "method": "POST",
        "url": "https://your-replit-url.repl.co/api/flexible-convert",
        "sendHeaders": true,
        "headerParameters": {
          "parameters": [
            {
              "name": "Content-Type",
              "value": "text/plain"
            },
            {
              "name": "X-Session-ID",
              "value": "={{ $workflow.id }}"
            },
            {
              "name": "X-User-ID",
              "value": "={{ $json.user_id || 'anonymous' }}"
            }
          ]
        },
        "sendBody": true,
        "bodyParameters": {
          "parameters": [
            {
              "name": "",
              "value": "={{ JSON.stringify($json) }}"
            }
          ]
        },
        "options": {}
      },
      "name": "Convert to APKG",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 3,
      "position": [1000, 300]
    }
  ]
}
```

## Response Format

The API will return a JSON response with the download link:

```json
{
  "success": true,
  "status": "completed",
  "deck_name": "Lecture-124-T-Slieman-PhD-Immunology",
  "cards_processed": 16,
  "media_files_downloaded": 8,
  "file_size": 245632,
  "filename": "Lecture-124-T-Slieman-PhD-Immunology_1735235689.apkg",
  "download_url": "https://tsebqscuuafnekssagyl.supabase.co/storage/v1/object/public/synapticrecall-links/2025/08/sessions/workflow-123/Lecture-124-T-Slieman-PhD-Immunology_1735235689.apkg",
  "full_download_url": "https://tsebqscuuafnekssagyl.supabase.co/storage/v1/object/public/synapticrecall-links/2025/08/sessions/workflow-123/Lecture-124-T-Slieman-PhD-Immunology_1735235689.apkg",
  "storage_type": "supabase",
  "permanent_link": true,
  "parsing_strategy": "n8n_triple_layer",
  "message": "Successfully generated deck \"Lecture-124-T-Slieman-PhD-Immunology\" with 16 cards"
}
```

## Key Points

1. **Triple-Layer Format**: The API expects the n8n format with markdown-wrapped JSON
2. **Batch Support**: Send multiple output objects (each with up to 8 cards)
3. **Smart Naming**: Deck names are extracted from tags automatically
4. **Permanent Links**: When using Supabase, links never expire

## Error Handling

If parsing fails, you'll get a helpful error response:

```json
{
  "error": "Failed to parse input data",
  "message": "Specific error details",
  "hints": [
    "Ensure data is valid JSON or wrapped in supported format",
    "For n8n: Check that output contains markdown-wrapped JSON",
    "Remove any trailing commas in JSON",
    "Ensure all strings are properly quoted"
  ],
  "data_preview": "First 500 chars of input..."
}
```

## Testing the Setup

1. Use a test card first:
```json
[
  {
    "output": "```json\n{\n  \"cards\": [\n    {\n      \"card_id\": 1,\n      \"type\": \"basic\",\n      \"front\": \"<div>Test Question</div>\",\n      \"back\": \"<div>Test Answer</div>\",\n      \"tags\": [\"Test\"]\n    }\n  ]\n}\n```"
  }
]
```

2. Check the response for the download URL
3. Download the APKG file and verify in Anki

## Troubleshooting

- **Empty response**: Check that the URL is correct and Replit app is running
- **Parse errors**: Verify the JSON escaping in the output field
- **No download URL**: Check logs in Replit console for errors
- **Supabase fallback**: If you see "storage_type": "local", Supabase might be misconfigured