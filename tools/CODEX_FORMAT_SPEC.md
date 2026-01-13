# CODEX Format Specification v1.0

**A Universal Standard for Curated Literary Text Cartridges**

---

## Name

**CODEX** - *Curated Open Document Exchange*

- **C**urated: Metadata-enhanced, cleaned text
- **O**pen: CC0/Public Domain, community-driven
- **D**ocument: Any textual work
- **E**xchange: Portable, shareable format
- **X**: eXtensible (custom fields supported)

**Historical Connection:** A *codex* was the ancient Roman book format that replaced scrolls - fitting for preserving classical texts in digital form.

---

## File Extension

**`.codex`**

### Rationale
- ✅ Memorable and pronounceable
- ✅ Evokes classical literature
- ✅ Not tied to any specific project
- ✅ Short (5 letters)
- ✅ No conflicts with existing formats

### Examples
```
meditations-marcus-aurelius.codex
nicomachean-ethics-aristotle.codex
republic-plato.codex
```

---

## What is a CODEX File?

A **CODEX file** is a **self-contained cartridge** containing:

1. **Clean extracted text** (ready to use)
2. **Original source text** (for verification)
3. **Rich metadata** (provenance, exclusions, prompts)
4. **Documentation** (README, license)

**Format:** ZIP archive with `.codex` extension

---

## Package Structure

```
meditations-marcus-aurelius.codex
├── codex.json              # Rich metadata (schema v1.0)
├── text/
│   ├── original.txt        # Raw source (Project Gutenberg)
│   ├── clean.txt           # Extracted author text
│   └── exclusions.txt      # What was excluded (for review)
├── prompts/
│   ├── system.txt          # AI system message
│   └── exclusion.txt       # Exclusion detection prompt
├── README.md               # Usage instructions
├── LICENSE.txt             # CC0 1.0 Universal
└── CHANGELOG.md            # Version history
```

---

## Core Metadata File: `codex.json`

**Based on:** PG Clean Metadata Schema v1.0  
**Extension:** `.codex` files MUST include a `codex.json` file

### Minimal Example

```json
{
  "codex_version": "1.0",
  "format": "text/codex",
  
  "source": {
    "provider": "Project Gutenberg",
    "id": "19978",
    "url": "https://www.gutenberg.org/ebooks/19978"
  },
  
  "work": {
    "title": "Meditations",
    "author": "Marcus Aurelius"
  },
  
  "curation": {
    "method": "exclusion-based",
    "curator": "auto_curator v4.0",
    "date": "2026-01-11T01:00:00Z"
  },
  
  "exclusions": [
    {
      "type": "header",
      "start_char": 0,
      "end_char": 1024,
      "reason": "Project Gutenberg header"
    }
  ]
}
```

### Full Schema

See [SCHEMA_SPEC.md](./SCHEMA_SPEC.md) for complete specification.

---

## Use Cases

### 1. **Digital Humanities**
```python
import codex

# Load a CODEX file
book = codex.load("meditations-marcus-aurelius.codex")

# Get clean text
text = book.text()

# Get metadata
author = book.metadata['work']['author']
```

### 2. **The Whetstone (Persona Generation)**
```python
from whetstone import PersonaGenerator

# Load CODEX file
codex = load_codex("meditations-marcus-aurelius.codex")

# Generate persona from clean text
persona = PersonaGenerator.from_codex(codex)
persona.chat("What is the nature of virtue?")
```

### 3. **NLP Research**
```python
from codex import CodexCorpus

# Build corpus from multiple CODEX files
corpus = CodexCorpus.from_directory("./philosophy_codexes/")

# All texts are pre-cleaned and metadata-rich
for codex in corpus:
    print(f"{codex.author}: {len(codex.text())} chars")
```

### 4. **Educational Platforms**
```python
# Students download one file - everything included
codex = download_codex("republic-plato.codex")

# Display clean text
display(codex.text())

# Show what was excluded (learning opportunity)
display(codex.exclusions())
```

---

## Consumers of CODEX Format

### Current
- ✅ **The Whetstone** - Persona generation from classical texts
- ✅ **PG Clean Tools** - Original creator/curator

### Potential
- 📚 **Project Gutenberg** - Enhanced distribution format
- 🎓 **LibriVox** - Audiobook preparation (exclude footnotes)
- 🤖 **Hugging Face** - Dataset hosting and discovery
- 📖 **Calibre** - eBook management with metadata
- 🔬 **Text Analysis Tools** - Pre-cleaned corpora

---

## Distribution Channels

### 1. **GitHub Repository**
```
https://github.com/codex-format/library
└── philosophy/
    ├── meditations-marcus-aurelius.codex
    ├── republic-plato.codex
    └── ...
```

### 2. **Hugging Face Datasets**
```python
from datasets import load_dataset

dataset = load_dataset("codex-format/philosophy-classics")
# Each entry is a parsed CODEX file
```

### 3. **Direct Download API**
```
GET https://codex.library/download/pg-19978
→ Returns meditations-marcus-aurelius.codex
```

---

## Creating CODEX Files

### Automated (auto_curator)

```bash
# Generate CODEX from Project Gutenberg
codex create --pg-id 19978 --output meditations.codex

# Or from URL
codex create --url "https://www.gutenberg.org/ebooks/19978"
```

### Manual

```bash
# 1. Create directory structure
mkdir meditations-codex
cd meditations-codex

# 2. Add files
# - codex.json (metadata)
# - text/original.txt
# - text/clean.txt
# - README.md
# - LICENSE.txt

# 3. Package
zip -r ../meditations-marcus-aurelius.codex .
```

---

## File Naming Convention

**Format:** `{title}-{author}.codex`

**Rules:**
- Lowercase
- Hyphens for spaces
- Remove special characters
- Author last name only (if applicable)

**Examples:**
```
meditations-marcus-aurelius.codex
republic-plato.codex
thus-spoke-zarathustra-nietzsche.codex
35-sonnets-pessoa.codex
```

---

## Versioning

### CODEX Format Version
- **Current:** `1.0`
- **Semver:** Major.Minor.Patch
- Field in `codex.json`: `"codex_version": "1.0"`

### Individual File Version
- Tracked in `CHANGELOG.md`
- Increments when metadata/exclusions updated
- Field in `codex.json`: `"changelog": [...]`

---

## Quality Levels

CODEX files can have different quality/verification levels:

### 🤖 **Auto-Generated** (Confidence: 0.8-0.9)
- Automatically curated
- No human verification
- Suitable for most uses

### ✅ **Community Verified** (Confidence: 0.95-0.98)
- Reviewed by 1+ humans
- Exclusions spot-checked
- High confidence

### 🏆 **Scholar Verified** (Confidence: 0.99-1.0)
- Expert review (PHD, translator, etc.)
- Gold standard accuracy
- Citation-worthy

**Indicated in metadata:**
```json
{
  "curation": {
    "verification_level": "scholar_verified",
    "verified_by": ["Dr. Jane Smith, Classics Professor"],
    "verification_date": "2026-01-11"
  }
}
```

---

## Compatibility

### Backward Compatibility
- v1.x files work with all v1.y readers
- New optional fields can be added in minor versions
- Required fields cannot change in v1.x

### Forward Compatibility
- v1.0 readers should gracefully ignore unknown fields
- Use `extensions` for custom fields
- Validate against schema before use

---

## Tools & Libraries

### Python
```bash
pip install codex-format
```

```python
import codex

# Load
book = codex.load("meditations.codex")

# Access
print(book.title)
print(book.author)
print(book.text())

# Create
new_codex = codex.create(
    source_text="...",
    title="New Work",
    author="Author Name",
    exclusions=[...]
)
new_codex.save("new-work.codex")
```

### JavaScript
```bash
npm install @codex-format/core
```

```javascript
const { Codex } = require('@codex-format/core');

const book = await Codex.load('meditations.codex');
console.log(book.metadata.work.title);
```

### CLI
```bash
# Install
npm install -g codex-cli

# Commands
codex info meditations.codex
codex extract meditations.codex --output clean.txt
codex validate meditations.codex
codex create --pg-id 19978
```

---

## Governance

### Format Specification
- **Maintainer:** CODEX Format Community
- **License:** CC0 1.0 (Public Domain)
- **Changes:** Via GitHub Issues/PRs
- **Versioning:** Semantic Versioning

### Reference Implementation
- **Repository:** https://github.com/codex-format/reference
- **Language:** Python 3.10+
- **License:** MIT

---

## Comparison to Other Formats

| Format | Purpose | Metadata | Bundles Text | Extensible |
|--------|---------|----------|--------------|------------|
| **CODEX** | Curated text cartridge | ✅ Rich | ✅ Yes | ✅ Yes |
| EPUB | eBook reader | ⚠️ Basic | ✅ Yes | ⚠️ Limited |
| TEI XML | Academic encoding | ✅ Rich | ✅ Yes | ✅ Yes |
| Plain .txt | Raw text | ❌ No | N/A | ❌ No |
| PDF | Document display | ⚠️ Basic | ✅ Yes | ❌ No |

**CODEX fills the gap** between raw text files and heavyweight scholarly formats.

---

## Contributing

### To the Specification
1. Open an issue: https://github.com/codex-format/spec/issues
2. Propose changes
3. Community discussion
4. Vote on inclusion

### To the Library
1. Create CODEX files for public domain texts
2. Verify existing CODEX files
3. Submit via PR to library repo

---

## Roadmap

### v1.1 (Q2 2026)
- [ ] Add audio narration metadata
- [ ] Pre-generated embeddings (optional)
- [ ] Linked entity annotations

### v2.0 (Q4 2026)
- [ ] Multi-language support (parallel texts)
- [ ] Inline annotations
- [ ] Versioned text (editorial changes tracked)

---

## Contact

- **Spec Issues:** https://github.com/codex-format/spec/issues
- **Library:** https://codex.library
- **Discord:** https://discord.gg/codex-format
- **Email:** hello@codex-format.org

---

**CODEX: A universal standard for literary text exchange**

*Built by the community, for the community* 🌟
