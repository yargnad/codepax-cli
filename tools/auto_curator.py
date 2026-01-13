import os
import glob
import re
import time
import json
from datetime import datetime
from openai import OpenAI

# Configuration
MODEL_NAME = os.getenv("WHETSTONE_MODEL", "qwen3:8b")

# Resolve library paths relative to this script for robustness
BASE_DIR = os.path.dirname(__file__)
LIBRARY_DIR = os.path.abspath(os.path.join(BASE_DIR, "."))
METADATA_DIR = os.path.abspath(os.path.join(BASE_DIR, ".metadata"))
SCAN_HEAD_SIZE = 15000  # Characters to scan at start for Intro
SCAN_TAIL_SIZE = 15000  # Characters to scan at end for Index/Footnotes

# Ensure metadata directory exists
os.makedirs(METADATA_DIR, exist_ok=True)

# Connect to Ollama server (OpenAI API compatible)
client = OpenAI(
    base_url="http://localhost:11434/v1",
    api_key="ollama"
)

# Structural Markers Dictionary
MARKER_PATTERNS = {
    "end_explicit": [
        r"^\s*THE END\s*$",
        r"^\s*FINIS\s*$",
        r"^\s*__\s*THE END\s*__\s*$",
        r"^\s*End of the Project Gutenberg EBook",
    ],
    "end_separator": [
        r"^\s*\*\s*\*\s*\*\s*\*\s*(\*)?\s*$", # * * * * *
        r"^\s*={5,}\s*$",
    ],
    "footnote_start": [
        r"^\s*NOTES:?\s*$",
        r"^\s*FOOTNOTES:?\s*$",
        r"^\s*\[1\]",
    ]
}

def detect_structural_end(text_chunk):
    """Scans for known 'End of Book' markers or 'Start of Notes' markers."""
    for pattern in MARKER_PATTERNS["end_explicit"]:
        matches = list(re.finditer(pattern, text_chunk, re.MULTILINE | re.IGNORECASE))
        if matches:
            return matches[0].end()

    for pattern in MARKER_PATTERNS["footnote_start"]:
        match = re.search(pattern, text_chunk, re.MULTILINE | re.IGNORECASE)
        if match:
            print(f"   ⚠️ Structural Hint: Found Footnote/Notes section at index {match.start()}. Suggesting cut.")
            return match.start()

    footnote_lines = list(re.finditer(r"^\s*\[\d+\]", text_chunk, re.MULTILINE))
    if len(footnote_lines) > 5:
        first_note = footnote_lines[0]
        print(f"   ⚠️ Structural Hint: Detected high density of footnotes starting at {first_note.start()}.")
        return first_note.start()

    return None

def get_true_start_phrase(text_chunk, author):
    """Asks the model to identify the first sentence of the actual work."""
    system_msg = "You are a precise text extraction tool. Return ONLY the extracted phrase. Do not provide explanations or summaries."
    
    prompt = f"""
    Task: Identify the EXACT phrase (10-20 words) where the actual work by {author} begins.
    CRITICAL IGNORE LIST (Do NOT select these):
    - Publisher's Introductions or Notes
    - Forewords NOT written by {author}
    - Translator's Notes or Prefaces
    - Biographies or Bibliographies
    - Tables of Contents
    - Copyright notices or Dedications (unless part of the poem/story)

    SELECTION RULES:
    1. Look for the very first sentence of the author's actual text.
    2. If there is an Author's Preface or Author's Introduction, select the start of THAT.
    3. If the work is poems, find the first line of the first poem (or its title).
    
    Example Input:
    *** START OF THE PROJECT GUTENBERG EBOOK ***
    Title: Example Work
    
    INTRODUCTION (by Editor)
    This is an intro by the editor.
    
    AUTHOR'S PREFACE
    I wrote this book because...
    
    CHAPTER I
    It was the best of times...
    
    Example Output:
    I wrote this book because...
    
    Analyze the text below and return ONLY the start phrase:
    {text_chunk}
    """
    
    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {'role': 'system', 'content': system_msg},
                {'role': 'user', 'content': prompt}
            ],
            temperature=0.1,
            extra_body={"options": {"num_ctx": 16384}}
        )
        content = response.choices[0].message.content.strip()
        content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip()
    except Exception as e:
        print(f"❌ AI Error: {e}")
        return None, None

    quotes = re.findall(r'"([^"]+)"', content)
    if quotes:
        return max(quotes, key=len).strip(), content
        
    lines = [ln.strip() for ln in content.splitlines() if ln.strip()]
    for ln in lines:
        lower_ln = ln.lower()
        if (lower_ln.startswith("sure") or 
            lower_ln.startswith("here is") or 
            lower_ln.startswith("the phrase") or
            lower_ln.endswith(":")):
            continue
        return ln.strip('"'""'''), content

    return "", content

def get_true_end_phrase(text_chunk, author):
    """Asks the model to identify the very last sentence of the actual work."""
    system_msg = "You are a precise text extraction tool. Return ONLY the extracted phrase. Do not provide explanations or summaries."

    prompt = f"""
    Task: Identify the EXACT phrase (10-20 words) where the actual work by {author} ends.
    
    CRITICAL IGNORE LIST (Do NOT select these):
    - "End of Project Gutenberg" markers
    - License texts or legal disclaimers
    - Appendices, Bibliographies, or Indexes
    - Editor's Postscripts
    
    **FOOTNOTES/ENDNOTES - VISUAL RECOGNITION:**
    Footnotes often appear as DENSE BLOCKS of bracketed numbers at the end:
    
    [741] See note 98, page 69.
    [742] In the Companion to the Almanac...
    [743] It may be necessary to remind...
    
    If you see MANY consecutive lines starting with [number], you have gone TOO FAR.
    The author's work ends BEFORE this section begins.
    
    SELECTION RULES:
    1. Find the very last sentence of the author's narrative, poem, or argument.
    2. If you see dense [123] patterns, STOP and look backwards for the actual ending.
    
    Example Input:
    ...and so they lived happily ever after.
    
    THE END
    
    NOTES
    [1] Some footnote.
    [2] Another note.
    
    *** END OF THE PROJECT GUTENBERG EBOOK ***
    
    Example Output:
    and so they lived happily ever after.
    
    Analyze the text below and return ONLY the end phrase:
    {text_chunk}
    """
    
    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {'role': 'system', 'content': system_msg},
                {'role': 'user', 'content': prompt}
            ],
            temperature=0.1,
            extra_body={"options": {"num_ctx": 16384}}
        )
        content = response.choices[0].message.content.strip()
        content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip()
    except Exception as e:
        print(f"❌ AI Error (End detection): {e}")
        return None, None

    quotes = re.findall(r'"([^"]+)"', content)
    if quotes:
        return max(quotes, key=len).strip(), content
        
    lines = [ln.strip() for ln in content.splitlines() if ln.strip()]
    for ln in lines:
        lower_ln = ln.lower()
        if (lower_ln.startswith("sure") or 
            lower_ln.startswith("here is") or 
            lower_ln.startswith("the phrase") or
            lower_ln.endswith(":")):
            continue
        return ln.strip('"'""'''), content

    return "", content

def fuzzy_find_phrase(raw_text, phrase, start_bound=0, limit_idx=None):
    """Find phrase using sliding window to handle typos."""
    if limit_idx is None:
        limit_idx = len(raw_text)
        
    scope_text = raw_text[start_bound:limit_idx]
    
    # Try exact match first
    exact = scope_text.find(phrase)
    if exact != -1:
        return start_bound + exact, start_bound + exact + len(phrase)
    
    # Sliding window fallback
    words = phrase.split()
    window_size = 4 if len(words) >= 4 else len(words)
    
    if len(words) < window_size:
        window_size = len(words)
        
    attempts = 0
    max_attempts = len(words) - window_size + 1
    
    for i in range(max_attempts):
        chunk_words = words[i : i+window_size]
        pattern = r"\b" + r"\W+".join(re.escape(w) for w in chunk_words) + r"\b"
        
        matches = list(re.finditer(pattern, scope_text, re.IGNORECASE))
        
        if matches:
            match = matches[0]
            return start_bound + match.start(), start_bound + match.end()
            
    return None, None

def char_to_line(text, char_idx):
    """Convert character index to line number."""
    return text[:char_idx].count('\n') + 1
    
def process_book(filepath):
    """Process a book and generate metadata file."""
    filename = os.path.basename(filepath)
    metadata_filename = os.path.splitext(filename)[0] + ".metadata.json"
    metadata_path = os.path.join(METADATA_DIR, metadata_filename)
    
    # Check if metadata already exists
    if os.path.exists(metadata_path):
        print(f"\n📘 {filename}")
        print(f"   ✅ Metadata already exists, skipping AI processing")
        with open(metadata_path, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        print(f"   📍 Boundaries: Lines {metadata['boundaries']['start_line']}-{metadata['boundaries']['end_line']}")
        return metadata
    
    print(f"\n📘 Processing: {filename}")
    
    with open(filepath, 'r', encoding='utf-8') as f:
        raw_text = f.read()

    # Gutenberg boundary detection
    header_match = re.search(r"\*\*\* START OF (THE|THIS) PROJECT GUTENBERG EBOOK .*? \*\*\*", raw_text, re.IGNORECASE)
    footer_match = re.search(r"\*\*\* END OF (THE|THIS) PROJECT GUTENBERG EBOOK .*? \*\*\*", raw_text, re.IGNORECASE)

    content_start_idx = 0
    content_end_idx = len(raw_text)

    if header_match:
        content_start_idx = header_match.end()
        while content_start_idx < len(raw_text) and raw_text[content_start_idx].isspace():
            content_start_idx += 1
            
    if footer_match:
        content_end_idx = footer_match.start()

    print(f"   🔍 Gutenberg Scope: {content_start_idx}:{content_end_idx} (Size: {content_end_idx - content_start_idx})")
    
    # Extract author from filename
    author = filename.split('_')[0].capitalize() if '_' in filename else filename.split(' by ')[-1].replace('.txt', '') if ' by ' in filename else "Unknown"

    # Find start boundary
    print("   - Asking AI to find the true start...")
    scope_text = raw_text[content_start_idx:content_end_idx]
    head_sample = scope_text[:SCAN_HEAD_SIZE]
    start_phrase, _ = get_true_start_phrase(head_sample, author)

    start_char = None
    start_line = None
    
    if start_phrase:
        anchor_start, anchor_end = fuzzy_find_phrase(raw_text, start_phrase, content_start_idx, content_end_idx)
        
        if anchor_start is not None:
            print(f"   ✅ Fuzzy/Exact matched start at index {anchor_start}: '{raw_text[anchor_start:anchor_start+30]}...'")
            start_char = anchor_start
            start_line = char_to_line(raw_text, anchor_start)
        else:
            print(f"   ⚠️ AI proposed start phrase not found. Phrase: {repr(start_phrase)}")
    else:
        print("   ⚠️ AI could not determine start.")

    # Find end boundary
    print("   - Asking AI to find the true end...")
    tail_sample = scope_text[-SCAN_TAIL_SIZE:]
    
    # Structural heuristics
    structural_cut_offset = detect_structural_end(tail_sample)
    if structural_cut_offset is not None:
        tail_start_rel = len(scope_text) - len(tail_sample)
        cut_rel_idx = tail_start_rel + structural_cut_offset
        cut_abs_idx = content_start_idx + cut_rel_idx
        
        print(f"   ✂️  Structural Heuristic: limiting scope to index {cut_abs_idx} (found marker/notes).")
        
        content_end_idx = cut_abs_idx
        scope_text = raw_text[content_start_idx:content_end_idx]
        tail_sample = tail_sample[:structural_cut_offset]
        
    end_phrase, _ = get_true_end_phrase(tail_sample, author)

    end_char = None
    end_line = None
    
    if end_phrase:
        anchor_start, anchor_end = fuzzy_find_phrase(raw_text, end_phrase, content_start_idx, content_end_idx)
        
        if anchor_start is not None:
            distance_from_end = content_end_idx - anchor_end
            if distance_from_end > 1000:
                print(f"   ⚠️ WARNING: End phrase is {distance_from_end} chars before scope end. Might be premature.")
        
            print(f"   ✅ Fuzzy/Exact matched end at index {anchor_end}")
            end_char = anchor_end
            end_line = char_to_line(raw_text, anchor_end)
        else:
            print(f"   ⚠️ AI proposed end phrase not found. Phrase: {repr(end_phrase)}")
    else:
        print("   ⚠️ AI could not determine end.")

    # Create metadata
    metadata = {
        "filename": filename,
        "author": author,
        "title": os.path.splitext(filename)[0],
        "boundaries": {
            "start_line": start_line,
            "end_line": end_line,
            "start_char": start_char,
            "end_char": end_char,
            "start_phrase": start_phrase,
            "end_phrase": end_phrase,
            "exclusions": []  # For manually added exclusion ranges (translator notes, etc.)
        },
        "curated_by": "auto_curator v2.0",
        "model": MODEL_NAME,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "notes": "To exclude translator/editor interjections, manually add to 'exclusions' array."
    }
    
    # Save metadata
    with open(metadata_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    
    print(f"   💾 Saved metadata to {metadata_path}")
    if start_line and end_line:
        print(f"   📍 Boundaries: Lines {start_line}-{end_line}")
    
    return metadata

def main():
    """Process all txt files in the library."""
    txt_files = glob.glob(os.path.join(LIBRARY_DIR, "*.txt"))
    
    if not txt_files:
        print("No .txt files found in library directory.")
        return
    
    print(f"Found {len(txt_files)} text file(s) in library.")
    
    for filepath in txt_files:
        try:
            process_book(filepath)
        except Exception as e:
            print(f"   ❌ Error processing {os.path.basename(filepath)}: {e}")

if __name__ == "__main__":
    main()