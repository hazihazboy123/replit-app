# Cloze Card Format for N8N

## Problem Solved

N8N doesn't handle double curly braces `{{}}` well, so you can now use single curly braces `{}` for cloze cards.

## N8N Input Format

```json
{
  "cards": [
    {
      "type": "cloze",
      "front": "The {c1::heart} pumps {c2::blood} through the {c3::circulatory system}",
      "notes": "Basic cardiovascular physiology"
    }
  ]
}
```

## Automatic Conversion

The system automatically converts:
- `{c1::heart}` → `{{c1::heart}}`
- `{c2::blood}` → `{{c2::blood}}`  
- `{c3::circulatory system}` → `{{c3::circulatory system}}`

## Examples

### Simple Cloze
**N8N Input:**
```
"The {c1::mitochondria} is the {c2::powerhouse} of the cell"
```

**Anki Output:**
```
"The {{c1::mitochondria}} is the {{c2::powerhouse}} of the cell"
```

### Medical Cloze
**N8N Input:**
```
"Myocardial infarction is caused by {c1::coronary artery occlusion} leading to {c2::cardiac muscle death}"
```

**Anki Output:**
```
"Myocardial infarction is caused by {{c1::coronary artery occlusion}} leading to {{c2::cardiac muscle death}}"
```

## Key Benefits

✅ N8N-friendly single brace format
✅ Automatic conversion to proper Anki format
✅ Works with any number of cloze deletions (c1, c2, c3, etc.)
✅ No manual formatting needed