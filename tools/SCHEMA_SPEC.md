# PG Clean Metadata Schema v1.0

## Overview

This schema defines a **rich, extensible format** for Project Gutenberg text metadata, designed for:
- 🤖 **AI reproducibility** (includes prompts, models, parameters)
- 📦 **Cartridge bundling** (package text + metadata together)
- 🔌 **Extensibility** (custom fields without breaking compatibility)
- 🌐 **Linked data** (connections to Wikidata, Internet Archive, etc.)
- 📊 **Complete provenance** (who, what, when, how)

---

## Schema Version

**Current:** `1.0`  
**Release Date:** 2026-01-11  
**Compatibility:** Backward-compatible with all v1.x

---

## Required Fields

### `source` (object)
Information about the original text source.

```json
{
  "provider": "Project Gutenberg",
  "pg_id": "19978",
  "pg_url": "https://www.gutenberg.org/ebooks/19978",
  "text_url": "https://www.gutenberg.org/files/19978/19978-0.txt",
  "file_hash": "sha256:...",
  "download_date": "2026-01-11T01:00:00Z"
}
```

### `work` (object)
Bibliographic information about the work.

```json
{
  "title": "Meditations",
  "author": "Marcus Aurelius",
  "translator": "George Long",
  "language": "en",
  "subjects": ["Ethics", "Philosophy, Ancient"]
}
```

### `curation` (object)
How this metadata was created.

```json
{
  "version": "4.0",
  "curator": "auto_curator v4.0",
  "model": {
    "name": "qwen3:8b",
    "temperature": 0.1
  },
  "curated_date": "2026-01-11T01:00:00Z"
}
```

### `exclusions` (array)
Ranges of text to exclude.

```json
[
  {
    "id": "excl-001",
    "type": "header",
    "start_char": 0,
    "end_char": 1024,
    "reason": "Project Gutenberg header",
    "detection_method": "structural_pattern"
  }
]
```

---

## Optional Fields

### `prompts` (object)
**Purpose:** AI reproducibility - exact prompts used to generate metadata.

```json
{
  "system_message": "You are a text analysis tool...",
  "exclusion_detection": {
    "template": "Task: Find ALL sections...",
    "variables": {
      "author": "Marcus Aurelius"
    }
  }
}
```

**Why include this?**
- ✅ Others can reproduce your results
- ✅ Compare different prompting strategies
- ✅ Train new models on prompt/output pairs
- ✅ Debug AI mistakes

### `stats` (object)
**Purpose:** Quick overview of text composition.

```json
{
  "total_chars": 426000,
  "excluded_chars": 45600,
  "author_chars": 380400,
  "author_percentage": 89.4,
  "exclusion_types": {
    "footnotes": 1,
    "translator_note": 1
  }
}
```

### `cartridge` (object)
**Purpose:** Bundled distribution metadata.

```json
{
  "id": "pg-19978-meditations-v1",
  "includes": ["metadata.json", "text_original.txt", "text_clean.txt"],
  "download_url": "https://github.com/pg-clean/cartridges/releases/..."
}
```

**What's a cartridge?**
- ZIP file containing:
  - Original PG text
  - Clean extracted text
  - This metadata file
  - README with usage instructions
- **One download = everything you need**

### `extensions` (object)
**Purpose:** Custom fields that don't break the schema.

```json
{
  "custom_tags": ["stoicism", "philosophy"],
  "reading_level": {"flesch_kincaid": 10.5},
  "sentiment_analysis": {"tone": "contemplative"},
  "community_notes": [
    {"user": "scholar_1", "note": "Excellent translation"}
  ]
}
```

**Extensibility Rules:**
1. All custom fields go in `extensions`
2. Use namespacing: `extensions.your_project.your_field`
3. Standard parsers ignore unknown fields
4. Custom tools can read their own extensions

### `linked_data` (object)
**Purpose:** Connect to external databases.

```json
{
  "wikidata": "Q4077973",
  "internet_archive": "meditationsofma00marc",
  "related_works": [
    {"pg_id": "4900", "title": "Epictetus - Enchiridion"}
  ]
}
```

### `changelog` (array)
**Purpose:** Track metadata evolution over time.

```json
[
  {
    "version": "1.0",
    "date": "2026-01-11T01:00:00Z",
    "changes": ["Initial generation"],
    "curator": "auto_curator v4.0"
  },
  {
    "version": "1.1",
    "date": "2026-01-11T06:00:00Z",
    "changes": ["Community verification"],
    "curator": "community_contributor_42"
  }
]
```

---

## Exclusion Types

### Standard Types

| Type | Description | Example |
|------|-------------|---------|
| `header` | PG header text | License, title page |
| `footer` | PG footer text | License, donation info |
| `translator_note` | Translator's comments | "Translator's note: The Greek word..." |
| `editor_note` | Editor's comments | "Editor's introduction by..." |
| `footnotes` | Footnote blocks | `[1] [2] [3]...` |
| `introduction` | Non-author intro | "Introduction by Scholar X" |
| `appendix` | Appendices | Glossary, bibliography |
| `toc` | Table of contents | Usually auto-generated |

### Detection Methods

| Method | Description |
|--------|-------------|
| `structural_pattern` | Regex/rule-based | 
| `ai_detected` | AI model found it |
| `manual` | Human added/verified |
| `hybrid` | AI + human verification |

---

## Confidence Scores

Each exclusion has a `confidence` score (0.0-1.0):

- **1.0**: Absolutely certain (e.g., PG header)
- **0.95-0.99**: Very confident (AI + structural)
- **0.80-0.94**: Confident (AI only)
- **0.50-0.79**: Uncertain (needs verification)
- **< 0.50**: Low confidence (flagged for review)

---

## Versioning Strategy

### Schema Version

`1.0` → `1.1` → `2.0`

- **Patch** (1.0 → 1.1): Add optional fields, backward-compatible
- **Minor** (1.x → 1.y): Add required fields with defaults
- **Major** (1.x → 2.x): Breaking changes

### Metadata Version

Each file has its own version in `changelog`:

```json
"changelog": [
  {"version": "1.0", "changes": ["Initial"]},
  {"version": "1.1", "changes": ["Added tags"]},
  {"version": "2.0", "changes": ["Verified by community"]}
]
```

---

## Usage Examples

### Python

```python
import json

# Load metadata
with open("19978.metadata.json") as f:
    meta = json.load(f)

# Get exclusions
for excl in meta['exclusions']:
    print(f"{excl['type']}: {excl['reason']}")

# Check confidence
low_conf = [e for e in meta['exclusions'] if e['confidence'] < 0.8]
if low_conf:
    print("These exclusions need verification:")
    for e in low_conf:
        print(f"  - {e['reason']} (conf: {e['confidence']})")

# Add custom extension
if 'extensions' not in meta:
    meta['extensions'] = {}

meta['extensions']['my_project'] = {
    "analyzed_date": "2026-01-11",
    "sentiment": "positive"
}
```

### JavaScript

```javascript
const meta = require('./19978.metadata.json');

// Extract clean text using exclusions
function getCleanText(rawText, metadata) {
  let parts = [];
  let pos = 0;
  
  for (const excl of metadata.exclusions.sort((a, b) => a.start_char - b.start_char)) {
    parts.push(rawText.substring(pos, excl.start_char));
    pos = excl.end_char;
  }
  
  parts.push(rawText.substring(pos));
  return parts.join('');
}
```

---

## Validation

### JSON Schema

A formal JSON Schema is provided at:
```
https://pg-clean-metadata.org/schema/v1.0.json
```

Tools can validate metadata files:

```bash
npm install -g ajv-cli
ajv validate -s schema.json -d 19978.metadata.json
```

### Required Field Checker

```python
REQUIRED_FIELDS = [
    'source.pg_id',
    'source.text_url',
    'work.title',
    'work.author',
    'curation.version',
    'exclusions'
]

def validate_metadata(meta):
    for field in REQUIRED_FIELDS:
        parts = field.split('.')
        obj = meta
        for part in parts:
            if part not in obj:
                raise ValueError(f"Missing required field: {field}")
            obj = obj[part]
```

---

## Contribution Guidelines

### Adding New Metadata

1. **Use latest schema version**
2. **Include all required fields**
3. **Add prompts for AI-generated data**
4. **Set confidence scores honestly**
5. **Add to changelog**

### Updating Existing Metadata

1. **Increment version in changelog**
2. **Document what changed**
3. **Preserve previous entries**
4. **Don't remove old exclusions** (mark as deprecated if needed)

### Custom Extensions

```json
{
  "extensions": {
    "your_project_name": {
      "field1": "value",
      "field2": 123
    }
  }
}
```

**Namespace your extensions** to avoid conflicts!

---

## License

**Schema:** CC0 1.0 (Public Domain)  
**Metadata Files:** CC0 1.0 (Public Domain)  
**Original Texts:** Varies (see PG)

---

## Contact

- **Issues:** https://github.com/pg-clean-metadata/issues
- **Discussions:** https://github.com/pg-clean-metadata/discussions
- **Email:** contact@pg-clean-metadata.org

---

**Built for the community, by the community** 🌟
