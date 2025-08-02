# n8n HTTP Request Node Setup - EXACT Configuration

## ✅ Simple Setup for Flashcard Converter

### 1. HTTP Request Node Configuration

**Method:** `POST`

**URL:** 
```
https://your-domain.com/api/flexible-convert
```
Or for local testing:
```
http://localhost:5000/api/flexible-convert
```

### 2. Body Configuration

**Body Content Type:** `Raw`

**Content Type:** `text/plain`

**Body:**
```
{{ $json.output }}
```

That's it! Just drag the output field from your previous node into the Body field.

### 3. Headers (Optional)

You don't need any custom headers! The API handles everything automatically.

If you want to add tracking headers (optional):
```
X-User-ID: {{ $json.user_id }}
X-Session-ID: {{ $json.session_id }}
```

### 4. What You'll Get Back

```json
{
  "success": true,
  "status": "completed",
  "deck_name": "Testingxie Medical Flashcards",
  "cards_processed": 8,
  "media_files_downloaded": 1,
  "file_size": 45632,
  "filename": "Testingxie_Medical_Flashcards_1735828800.apkg",
  "download_url": "/download/Testingxie_Medical_Flashcards_1735828800.apkg",
  "full_download_url": "https://your-domain.com/download/Testingxie_Medical_Flashcards_1735828800.apkg",
  "storage_type": "supabase",
  "message": "Successfully generated deck \"Testingxie Medical Flashcards\" with 8 cards"
}
```

## 🎯 Key Points

1. **Body = {{ $json.output }}** - This gives you the markdown-wrapped JSON
2. **Content Type = text/plain** - Send as plain text, not JSON
3. **No complex headers needed** - Keep it simple
4. **You get a permanent download link** - Works forever with Supabase

## ⚠️ Common Mistakes to Avoid

1. **DON'T** use `JSON` as body type - use `Raw` with `text/plain`
2. **DON'T** try to parse or modify the output - just pass it directly
3. **DON'T** add unnecessary headers - the API doesn't need them
4. **DON'T** wrap the output in additional JSON - just use {{ $json.output }}

## 🧪 Testing

If you see this in your n8n node output:
```
```json
{
  "cards": [
    {
      "card_id": 1,
      ...
    }
  ]
}
```
```

Then you're ready! The API will handle the markdown wrapper automatically.

## 📝 Example n8n Workflow

1. **AI Agent Node** → Generates flashcards with markdown-wrapped JSON
2. **HTTP Request Node** → Sends {{ $json.output }} to the API
3. **Response** → Contains download URL for the .apkg file

That's all there is to it! The simpler approach means less can go wrong.