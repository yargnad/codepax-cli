# Project Gutenberg Clean Text Metadata

**A community-curated dataset of content boundaries for Project Gutenberg texts**

## What is this?

This repository contains **machine-generated + human-verified metadata** for Project Gutenberg texts, identifying:

- 📍 Where the actual author's work begins and ends
- 🚫 Sections to exclude (translator notes, editor comments, footnotes)
- 📊 Statistics about text composition
- 🤖 Model and method used for curation

## Why does this exist?

**Problem:** Project Gutenberg texts include valuable metadata, but also:
- Headers and footers (license text)
- Translator's notes and footnotes
- Editor's introductions and appendices
- Tables of contents and indexes

**Solution:** This dataset provides **precise character/line positions** for clean text extraction, enabling:
- NLP research on pure author text
- AI training on philosophical/literary works
- Academic analysis without manual cleanup
- Persona generation and text analysis tools

## Format

Each `.metadata.json` file corresponds to one Project Gutenberg `.txt` file.

### Example: Exclusion-Based Metadata (v3)

```json
{
  "filename": "Meditations by Marcus Aurelius.txt",
  "author": "Marcus Aurelius",
  "version": "3.0-exclusions",
  "total_chars": 425600,
  "exclusions": [
    {
      "start_line": 1,
      "end_line": 45,
      "start_char": 0,
      "end_char": 1024,
      "reason": "Project Gutenberg header"
    },
    {
      "start_line": 450,
      "end_line": 465,
      "start_char": 23400,
      "end_char": 24100,
      "reason": "Translator's footnote"
    }
  ],
  "stats": {
    "total_chars": 425600,
    "excluded_chars": 45200,
    "author_chars": 380400,
    "author_percentage": 89.4
  },
  "curated_by": "auto_curator v3.0",
  "model": "qwen3:8b",
  "timestamp": "2026-01-11T01:00:00Z"
}
```

## Usage

### Python

```python
from curator_utils import get_author_text

# Extract clean author text
text = get_author_text("Meditations by Marcus Aurelius.txt")

# Text automatically excludes headers, footers, and translator notes
print(len(text))  # 380,400 characters of pure author text
```

### Manual

```python
import json

with open(".metadata_v3/Meditations by Marcus Aurelius.metadata.json") as f:
    metadata = json.load(f)

with open("Meditations by Marcus Aurelius.txt") as f:
    raw = f.read()

# Build clean text by excluding marked ranges
clean_parts = []
pos = 0

for exclusion in sorted(metadata['exclusions'], key=lambda x: x['start_char']):
    clean_parts.append(raw[pos:exclusion['start_char']])
    pos = exclusion['end_char']

clean_parts.append(raw[pos:])
author_text = ''.join(clean_parts)
```

## Methodology

### v3.0 (Current) - Exclusion-Based

**Strategy:** Identify what to EXCLUDE, keep everything else

**Auto-Detection:**
1. **Structural patterns:**
   - Project Gutenberg headers/footers
   - Dense footnote blocks (`[1] [2] [3]...`)
   - "NOTES" or "FOOTNOTES" sections

2. **AI detection (qwen3:8b):**
   - Translator's notes
   - Editor's comments
   - Introductions by others

3. **Merging:** Overlapping exclusions are merged automatically

**Benefits:**
- ✅ Handles complex texts (interleaved notes)
- ✅ Safer failure mode (missing one footnote is minor)
- ✅ Easy to manually add/remove exclusions

### v2.0 (Legacy) - Boundary-Based

Identifies explicit start/end positions. See `.metadata/` folder.

## Contributing

### Adding Metadata

Run the curator on your Project Gutenberg files:

```bash
py auto_curator_v3.py
```

### Manual Corrections

If automated detection missed something:

```bash
py add_exclusion.py
```

Or edit the `.metadata.json` file directly:

```json
{
  "exclusions": [
    {
      "start_line": 500,
      "end_line": 520,
      "start_char": 28000,
      "end_char": 29500,
      "reason": "Appendix added in later edition"
    }
  ]
}
```

### Sharing

1. Verify the metadata is accurate
2. Submit a pull request with the `.metadata.json` file
3. Include the Project Gutenberg book ID for reference

## License

### Metadata Files

**CC0 1.0 Universal (Public Domain)**

The metadata files in this repository are released into the public domain under CC0 1.0.

You can:
- ✅ Use commercially
- ✅ Modify
- ✅ Distribute
- ✅ Use in research
- ✅ No attribution required (but appreciated!)

### Original Texts

The Project Gutenberg texts themselves remain under their original licenses (typically public domain in the US). See individual book pages on [gutenberg.org](https://www.gutenberg.org) for details.

### Code

MIT License - See `LICENSE` file

## Citation

If you use this dataset in research, please cite:

```bibtex
@misc{pg_clean_metadata_2026,
  title={Project Gutenberg Clean Text Metadata},
  author={Community Contributors},
  year={2026},
  publisher={GitHub},
  url={https://github.com/yourusername/pg-clean-metadata}
}
```

## Use Cases

- 🤖 **AI Training:** Clean datasets for LLM fine-tuning
- 📚 **Digital Humanities:** Text analysis without manual cleanup
- 🧠 **Persona Generation:** Extract pure author voice
- 📊 **NLP Research:** Accurate corpus statistics
- 🔍 **Text Mining:** Focus on actual content

## Statistics

- **Texts Processed:** 174+
- **Authors Covered:** Philosophy, Literature, Science
- **Avg. Author %:** 85-95% (after exclusions)
- **Models Used:** qwen3:8b, mistral-nemo:12b

## Changelog

### v3.0 (2026-01-11)
- 🎯 Switched to exclusion-based approach
- ✨ Auto-detects translator notes and footnotes
- 📊 Added statistics (author percentage, char counts)
- 🤖 AI-powered meta-text detection

### v2.0 (2026-01-10)
- 💾 Metadata files instead of modified copies
- 🔄 Manual exclusion support
- 📍 Boundary-based extraction

### v1.0 (2026-01-09)
- 🚀 Initial release
- ✂️ Basic start/end detection

## Contact

Questions? Issues? Want to contribute?

- 📧 Open an issue on GitHub
- 💬 Join the discussion

---

**Built with ❤️ for the Project Gutenberg community**
