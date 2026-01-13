"""
Utility functions for reading curated text boundaries.
Used by persona generator to extract author text from raw Project Gutenberg files.
"""
import os
import json
from pathlib import Path

METADATA_DIR = Path(__file__).parent / ".metadata"

def get_author_text(filepath):
    """
    Extract author text from a file using its metadata boundaries.
    Automatically excludes any defined exclusion ranges (translator notes, etc).
    
    Args:
        filepath: Path to the original .txt file
        
    Returns:
        str: The author's text only (no headers, footers, footnotes, or excluded sections)
        None: If metadata doesn't exist or boundaries aren't set
    """
    # Load metadata
    filename = os.path.basename(filepath)
    metadata_filename = os.path.splitext(filename)[0] + ".metadata.json"
    metadata_path = METADATA_DIR / metadata_filename
    
    if not metadata_path.exists():
        print(f"⚠️ No metadata found for {filename}. Run auto_curator.py first.")
        return None
    
    with open(metadata_path, 'r', encoding='utf-8') as f:
        metadata = json.load(f)
    
    boundaries = metadata.get('boundaries', {})
    start_char = boundaries.get('start_char')
    end_char = boundaries.get('end_char')
    exclusions = boundaries.get('exclusions', [])
    
    if start_char is None or end_char is None:
        print(f"⚠️ Incomplete boundaries in metadata for {filename}")
        return None
    
    # Read the original file
    with open(filepath, 'r', encoding='utf-8') as f:
        raw_text = f.read()
    
    # If no exclusions, simple extraction
    if not exclusions:
        return raw_text[start_char:end_char]
    
    # Build author text by excluding ranges
    author_text_parts = []
    current_pos = start_char
    
    # Sort exclusions by start position
    sorted_exclusions = sorted(exclusions, key=lambda x: x['start_char'])
    
    for exclusion in sorted_exclusions:
        excl_start = exclusion['start_char']
        excl_end = exclusion['end_char']
        
        # Skip exclusions outside our boundary
        if excl_end <= start_char or excl_start >= end_char:
            continue
        
        # Add text before this exclusion
        if current_pos < excl_start:
            author_text_parts.append(raw_text[current_pos:excl_start])
        
        # Skip the exclusion
        current_pos = max(current_pos, excl_end)
    
    # Add remaining text after last exclusion
    if current_pos < end_char:
        author_text_parts.append(raw_text[current_pos:end_char])
    
    return ''.join(author_text_parts)

def get_metadata(filepath):
    """
    Get the full metadata for a file.
    
    Args:
        filepath: Path to the original .txt file
        
    Returns:
        dict: Metadata including boundaries, model used, timestamp, etc.
        None: If metadata doesn't exist
    """
    filename = os.path.basename(filepath)
    metadata_filename = os.path.splitext(filename)[0] + ".metadata.json"
    metadata_path = METADATA_DIR / metadata_filename
    
    if not metadata_path.exists():
        return None
    
    with open(metadata_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def list_curated_files():
    """
    List all files that have been curated (have metadata).
    
    Returns:
        list: Paths to .txt files that have metadata
    """
    if not METADATA_DIR.exists():
        return []
    
    curated_files = []
    for metadata_file in METADATA_DIR.glob("*.metadata.json"):
        # Find corresponding .txt file
        txt_filename = metadata_file.stem.replace('.metadata', '') + '.txt'
        txt_path = METADATA_DIR.parent / txt_filename
        if txt_path.exists():
            curated_files.append(str(txt_path))
    
    return curated_files

# Example usage
if __name__ == "__main__":
    import glob
    
    # Find all txt files in library
    txt_files = glob.glob(str(METADATA_DIR.parent / "*.txt"))
    
    for filepath in txt_files:
        print(f"\n{'='*60}")
        print(f"File: {os.path.basename(filepath)}")
        
        # Get metadata
        metadata = get_metadata(filepath)
        if metadata:
            print(f"Author: {metadata['author']}")
            print(f"Curated by: {metadata['curated_by']} ({metadata['model']})")
            bounds = metadata['boundaries']
            print(f"Boundaries: Lines {bounds['start_line']}-{bounds['end_line']}")
            
            # Get author text
            author_text = get_author_text(filepath)
            if author_text:
                print(f"Author text length: {len(author_text)} chars")
                print(f"Preview: {author_text[:100]}...")
        else:
            print("❌ Not curated yet")
