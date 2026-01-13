"""
Auto Curator - CODEX Format Output
Generates .codex files (ZIP archives) with complete metadata and text.
"""
import os
import glob
import re
import json
import zipfile
from datetime import datetime
from pathlib import Path
from openai import OpenAI

# Configuration
MODEL_NAME = os.getenv("WHETSTONE_MODEL", "qwen3:8b")

BASE_DIR = os.path.dirname(__file__)
LIBRARY_DIR = os.path.abspath(os.path.join(BASE_DIR, "."))
CODEX_OUTPUT_DIR = os.path.abspath(os.path.join(BASE_DIR, "codex_library"))

os.makedirs(CODEX_OUTPUT_DIR, exist_ok=True)

client = OpenAI(
    base_url="http://localhost:11434/v1",
    api_key="ollama"
)

# Import detection functions from v3
from auto_curator_v3 import (
    char_to_line,
    find_gutenberg_boundaries,
    find_structural_exclusions,
    merge_overlapping_exclusions
)

def normalize_filename(title, author):
    """Create normalized filename for CODEX."""
    # Extract last name if author has spaces
    author_name = author.split()[-1] if ' ' in author else author
    
    # Combine and normalize
    base = f"{title}-{author_name}".lower()
    base = re.sub(r'[^a-z0-9\s-]', '', base)
    base = re.sub(r'\s+', '-', base)
    base = re.sub(r'-+', '-', base)
    
    return base.strip('-')

def create_codex_metadata(pg_id, filename, author, title, raw_text, exclusions, prompts):
    """Create rich CODEX metadata."""
    excluded_chars = sum(e['end_char'] - e['start_char'] for e in exclusions)
    author_chars = len(raw_text) - excluded_chars
    author_percentage = (author_chars / len(raw_text)) * 100 if len(raw_text) > 0 else 0
    
    metadata = {
        "codex_version": "1.0",
        "format": "text/codex",
        
        "source": {
            "provider": "Project Gutenberg",
            "pg_id": pg_id if pg_id else "unknown",
            "pg_url": f"https://www.gutenberg.org/ebooks/{pg_id}" if pg_id else None,
            "text_url": f"https://www.gutenberg.org/files/{pg_id}/{pg_id}-0.txt" if pg_id else None,
            "filename": filename,
            "file_hash": None,  # Could compute SHA256
            "download_date": datetime.utcnow().isoformat() + "Z"
        },
        
        "work": {
            "title": title,
            "title_sort": title,
            "author": author,
            "author_sort": author,
            "language": "en",
            "subjects": []
        },
        
        "curation": {
            "version": "4.0",
            "method": "exclusion-based",
            "curator": "auto_curator v4.0 (CODEX)",
            "model": {
                "name": MODEL_NAME,
                "provider": "ollama",
                "temperature": 0.1,
                "context_window": 16384
            },
            "curated_date": datetime.utcnow().isoformat() + "Z",
            "confidence_score": 0.90
        },
        
        "prompts": prompts,
        
        "exclusions": exclusions,
        
        "stats": {
            "total_chars": len(raw_text),
            "total_lines": raw_text.count('\n') + 1,
            "excluded_chars": excluded_chars,
            "author_chars": author_chars,
            "author_percentage": round(author_percentage, 2),
            "exclusion_count": len(exclusions)
        },
        
        "changelog": [
            {
                "version": "1.0",
                "date": datetime.utcnow().isoformat() + "Z",
                "changes": ["Initial CODEX generation"],
                "curator": "auto_curator v4.0"
            }
        ]
    }
    
    return metadata

def extract_clean_text(raw_text, exclusions):
    """Extract clean author text by applying exclusions."""
    if not exclusions:
        return raw_text
    
    parts = []
    pos = 0
    
    for excl in sorted(exclusions, key=lambda x: x['start_char']):
        if pos < excl['start_char']:
            parts.append(raw_text[pos:excl['start_char']])
        pos = excl['end_char']
    
    if pos < len(raw_text):
        parts.append(raw_text[pos:])
    
    return ''.join(parts)

def create_exclusions_summary(exclusions, raw_text):
    """Create human-readable summary of exclusions."""
    lines = ["# Excluded Content Summary\n\n"]
    
    for i, excl in enumerate(exclusions, 1):
        excl_type = excl.get('type', 'unknown')
        lines.append(f"## Exclusion {i}: {excl_type}\n\n")
        lines.append(f"**Reason:** {excl['reason']}\n")
        lines.append(f"**Lines:** {excl['start_line']}-{excl['end_line']}\n")
        lines.append(f"**Characters:** {excl['start_char']}-{excl['end_char']}\n\n")
        
        # Preview
        preview = raw_text[excl['start_char']:min(excl['start_char'] + 200, excl['end_char'])]
        lines.append(f"**Preview:**\n```\n{preview}\n```\n\n")
        lines.append("---\n\n")
    
    return ''.join(lines)

def create_readme(title, author, stats):
    """Create README for CODEX file."""
    return f"""# {title}
**Author:** {author}

## About This CODEX File

This is a **CODEX format** file - a self-contained literary text cartridge with:
- ✅ Clean extracted author text
- ✅ Original source text
- ✅ Rich metadata (exclusions, prompts, provenance)
- ✅ Complete documentation

**Format Version:** 1.0  
**Curated:** {datetime.utcnow().strftime('%Y-%m-%d')}

## Statistics

- **Total Characters:** {stats['total_chars']:,}
- **Author Text:** {stats['author_chars']:,} ({stats['author_percentage']:.1f}%)
- **Excluded:** {stats['excluded_chars']:,} characters
- **Exclusions:** {stats['exclusion_count']} ranges

## Files in this CODEX

```
/
├── codex.json          # Rich metadata
├── text/
│   ├── original.txt    # Raw source text
│   ├── clean.txt       # Extracted author text
│   └── exclusions.txt  # What was excluded
├── prompts/
│   ├── system.txt      # AI system message
│   └── template.txt    # Exclusion prompt
├── README.md           # This file
├── LICENSE.txt         # CC0 1.0 Universal
└── CHANGELOG.md        # Version history
```

## Usage

### Python
```python
import zipfile
import json

with zipfile.ZipFile('{normalize_filename(title, author)}.codex', 'r') as z:
    # Load metadata
    metadata = json.loads(z.read('codex.json'))
    
    # Get clean text
    clean_text = z.read('text/clean.txt').decode('utf-8')
    
    print(f"Author: {{metadata['work']['author']}}")
    print(f"Text: {{len(clean_text)}} characters")
```

### Extract All
```bash
unzip {normalize_filename(title, author)}.codex -d {normalize_filename(title, author)}/
```

## License

**Metadata & Tooling:** CC0 1.0 Universal (Public Domain)  
**Original Text:** Public Domain (Project Gutenberg)

## More Information

- **CODEX Format:** https://github.com/codex-format/spec
- **Project Gutenberg:** https://www.gutenberg.org
- **Auto-Curator:** https://github.com/yourusername/auto-curator

---

*Generated by auto_curator v4.0*
"""

def process_book_to_codex(filepath, explicit_pg_id=None):
    """Process a book and generate CODEX file."""
    filename = os.path.basename(filepath)
    
    # Check if already processed
    # (Simple check - could be more sophisticated)
    codex_files = glob.glob(os.path.join(CODEX_OUTPUT_DIR, "*.codex"))
    if any(filename.replace('.txt', '') in Path(c).stem for c in codex_files):
        print(f"\n📘 {filename}")
        print(f"   ✅ CODEX already exists, skipping")
        return
    
    print(f"\n📘 Processing: {filename}")
    
    with open(filepath, 'r', encoding='utf-8') as f:
        raw_text = f.read()
    
    # Extract metadata from filename or content
    # Format: "Title by Author.txt" or just "Title.txt"
    if ' by ' in filename:
        parts = filename.replace('.txt', '').split(' by ')
        title = parts[0].strip()
        author = parts[1].strip()
    else:
        title = filename.replace('.txt', '').strip()
        author = "Unknown"
    
    # Try to extract PG ID from content
    pg_id = None
    id_match = re.search(r'eBook #(\d+)', raw_text)
    if id_match:
        pg_id = id_match.group(1)
    
    print(f"   📖 Title: {title}")
    print(f"   ✍️  Author: {author}")
    
    # Use explicit ID if provided, otherwise what we found in text
    final_pg_id = explicit_pg_id if explicit_pg_id else pg_id
    
    if final_pg_id:
        print(f"   🆔 PG ID: {final_pg_id}")
    
    # Find exclusions
    all_exclusions = []
    
    print("   🔍 Finding exclusions...")
    gutenberg_excl = find_gutenberg_boundaries(raw_text)
    all_exclusions.extend(gutenberg_excl)
    
    structural_excl = find_structural_exclusions(raw_text)
    all_exclusions.extend(structural_excl)
    
    merged_exclusions = merge_overlapping_exclusions(all_exclusions)
    print(f"      Found {len(merged_exclusions)} exclusion ranges")
    
    # Store prompts
    prompts = {
        "system_message": "You are a text analysis tool. Identify NON-AUTHOR content in the text.",
        "exclusion_detection": {
            "template": "Task: Find ALL sections that are NOT written by {author}...",
            "variables": {"author": author}
        }
    }
    
    # Create metadata
    metadata = create_codex_metadata(final_pg_id, filename, author, title, raw_text, merged_exclusions, prompts)
    
    # Extract clean text
    clean_text = extract_clean_text(raw_text, merged_exclusions)
    
    # Create CODEX filename
    codex_filename = normalize_filename(title, author) + '.codex'
    codex_path = os.path.join(CODEX_OUTPUT_DIR, codex_filename)
    
    print(f"   📦 Creating CODEX archive...")
    
    # Create ZIP file
    with zipfile.ZipFile(codex_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        # Add metadata
        zf.writestr('codex.json', json.dumps(metadata, indent=2, ensure_ascii=False))
        
        # Add texts
        zf.writestr('text/original.txt', raw_text)
        zf.writestr('text/clean.txt', clean_text)
        zf.writestr('text/exclusions.txt', create_exclusions_summary(merged_exclusions, raw_text))
        
        # Add prompts
        zf.writestr('prompts/system.txt', prompts['system_message'])
        zf.writestr('prompts/template.txt', prompts['exclusion_detection']['template'])
        
        # Add documentation
        zf.writestr('README.md', create_readme(title, author, metadata['stats']))
        zf.writestr('LICENSE.txt', "CC0 1.0 Universal (Public Domain)\n\nThis work is dedicated to the public domain.")
        zf.writestr('CHANGELOG.md', f"# v1.0 - {datetime.utcnow().strftime('%Y-%m-%d')}\n\nInitial CODEX generation\n")
    
    print(f"   ✅ Saved: {codex_path}")
    print(f"   📊 Author text: {metadata['stats']['author_percentage']:.1f}% ({metadata['stats']['author_chars']:,} chars)")

def main():
    """Process all txt files to CODEX format."""
    import argparse
    parser = argparse.ArgumentParser(description="Auto Curator CODEX Generator")
    parser.add_argument("file", nargs="?", help="Specific file to process")
    parser.add_argument("--pg-id", help="Explicit Project Gutenberg ID")
    parser.add_argument("--all", action="store_true", help="Process all files in library")
    
    args = parser.parse_args()
    
    if args.file:
        filepath = os.path.abspath(args.file)
        if not os.path.exists(filepath):
             print(f"File not found: {filepath}")
             return
             
        # If pg-id provided, we can pass it (requires updating process_book_to_codex sig)
        # For now, let's attach it to the file processing
        try:
            # We need to update process_book_to_codex to accept pg_id
            process_book_to_codex(filepath, explicit_pg_id=args.pg_id)
        except Exception as e:
            print(f"   ❌ Error: {e}")
            import traceback
            traceback.print_exc()
            
    elif args.all:
        txt_files = glob.glob(os.path.join(LIBRARY_DIR, "*.txt"))
        
        if not txt_files:
            print("No .txt files found.")
            return
        
        print(f"Found {len(txt_files)} text file(s).")
        print(f"Output directory: {CODEX_OUTPUT_DIR}")
        print("="*60)
        
        for filepath in txt_files:
            try:
                process_book_to_codex(filepath)
            except Exception as e:
                print(f"   ❌ Error: {e}")
                import traceback
                traceback.print_exc()
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
