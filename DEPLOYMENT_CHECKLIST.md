# SynapticRecall Deployment Checklist

## Pre-Deployment

- [ ] All test files removed
- [ ] Git repository initialized
- [ ] .gitignore configured
- [ ] Core files present:
  - [x] app.py (v11.0.0 with Supabase)
  - [x] flexible_parser.py
  - [x] supabase_utils.py
  - [x] requirements.txt
  - [x] templates/
  - [x] static/

## GitHub Setup

```bash
# 1. Add all files
git add .

# 2. Commit
git commit -m "Add flexible n8n parser with Supabase integration"

# 3. Push to GitHub
git push -u origin main
```

## Replit Setup

1. **Import from GitHub**:
   - Go to Replit
   - Create new Repl → Import from GitHub
   - Use: `https://github.com/hazihazboy123/replit-app`

2. **Environment Variables** (in Replit Secrets):
   ```
   SUPABASE_URL=https://tsebqscuuafnekssagyl.supabase.co
   SUPABASE_ANON_KEY=your-anon-key-here
   SUPABASE_BUCKET=synapticrecall-links
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the App**:
   ```bash
   python main.py
   ```

## Testing

1. **Health Check**:
   ```
   GET https://your-app.repl.co/api/health
   GET https://your-app.repl.co/api/health/supabase
   ```

2. **Test Conversion**:
   ```bash
   curl -X POST https://your-app.repl.co/api/flexible-convert \
     -H "Content-Type: text/plain" \
     -d '[{"output":"```json\n{\"cards\":[{\"card_id\":1,\"type\":\"basic\",\"front\":\"<div>Test</div>\",\"back\":\"<div>Answer</div>\",\"tags\":[\"Test\"]}]}\n```"}]'
   ```

## n8n Configuration

1. **HTTP Request Node**:
   - Method: POST
   - URL: `https://your-app.repl.co/api/flexible-convert`
   - Headers: `Content-Type: text/plain`
   - Body: Raw JSON string

2. **Expected Response**:
   - Check for `download_url` in response
   - Use `storage_type` to verify Supabase is working

## Monitoring

- [ ] Check Replit logs for errors
- [ ] Verify Supabase bucket has files
- [ ] Test download links work
- [ ] Monitor disk usage in downloads/

## Post-Deployment

- [ ] Test with real n8n workflow
- [ ] Verify APKG files open in Anki
- [ ] Check rich formatting preserved
- [ ] Test with 50+ card batches

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Parse errors | Check n8n output format matches expected structure |
| No Supabase URL | Verify environment variables are set |
| Download fails | Check file exists in downloads/ or Supabase |
| Memory issues | Restart Replit instance |

## How the System Works

```
User PDF → n8n Processing → LLM Generation
    ↓
Triple-wrapped JSON → Flask API
    ↓
Flexible Parser → Extract Cards
    ↓
Generate APKG → Upload to Supabase
    ↓
Return Download URL → User Downloads
```

## Key Features Working

✅ Triple-layer n8n JSON parsing
✅ Malformed JSON recovery
✅ Rich HTML preservation
✅ JavaScript onclick handlers
✅ Clinical vignettes with gradients
✅ Smart deck naming from tags
✅ Supabase permanent storage
✅ Local storage fallback
✅ Comprehensive error messages