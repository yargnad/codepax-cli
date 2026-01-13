"""
Interactive tool for adding exclusion ranges to metadata files.
Use this to manually mark translator notes, editor comments, etc.
"""
import os
import json
from pathlib import Path

METADATA_DIR = Path(__file__).parent / ".metadata"

def char_to_line(text, char_idx):
    """Convert character index to line number."""
    return text[:char_idx].count('\n') + 1

def add_exclusion_interactive(metadata_filename):
    """Interactively add an exclusion range to a metadata file."""
    metadata_path = METADATA_DIR / metadata_filename
    
    if not metadata_path.exists():
        print(f"❌ Metadata file not found: {metadata_filename}")
        return
    
    # Load metadata
    with open(metadata_path, 'r', encoding='utf-8') as f:
        metadata = json.load(f)
    
    # Load original text
    txt_filename = metadata['filename']
    txt_path = METADATA_DIR.parent / txt_filename
    
    if not txt_path.exists():
        print(f"❌ Original text file not found: {txt_filename}")
        return
    
    with open(txt_path, 'r', encoding='utf-8') as f:
        raw_text = f.read()
    
    print(f"\n{'='*60}")
    print(f"Adding Exclusion to: {txt_filename}")
    print(f"{'='*60}")
    
    # Show current boundaries
    bounds = metadata['boundaries']
    print(f"\nCurrent Boundaries:")
    print(f"  Start: Line {bounds['start_line']} (char {bounds['start_char']})")
    print(f"  End:   Line {bounds['end_line']} (char {bounds['end_char']})")
    
    # Show existing exclusions
    exclusions = bounds.get('exclusions', [])
    if exclusions:
        print(f"\nExisting Exclusions: {len(exclusions)}")
        for i, excl in enumerate(exclusions, 1):
            print(f"  {i}. Lines {excl.get('start_line', '?')}-{excl.get('end_line', '?')}: {excl.get('reason', 'No reason')}")
    else:
        print("\nNo existing exclusions.")
    
    # Get exclusion details
    print(f"\n{'='*60}")
    print("Define Exclusion Range")
    print(f"{'='*60}")
    
    reason = input("Reason (e.g., 'Translator's Note', 'Editor's Comment'): ").strip()
    
    # Option 1: By line numbers
    print("\nEnter range by:")
    print("  1. Line numbers")
    print("  2. Character indices")
    choice = input("Choice (1 or 2): ").strip()
    
    if choice == "1":
        start_line = int(input("Start line: "))
        end_line = int(input("End line: "))
        
        # Convert to character indices
        lines = raw_text.split('\n')
        start_char = sum(len(line) + 1 for line in lines[:start_line-1])
        end_char = sum(len(line) + 1 for line in lines[:end_line])
    else:
        start_char = int(input("Start character index: "))
        end_char = int(input("End character index: "))
        start_line = char_to_line(raw_text, start_char)
        end_line = char_to_line(raw_text, end_char)
    
    # Preview
    preview_text = raw_text[start_char:min(start_char+200, end_char)]
    print(f"\nPreview of excluded text:")
    print(f"{'─'*60}")
    print(preview_text)
    if len(preview_text) == 200:
        print("... (truncated)")
    print(f"{'─'*60}")
    
    confirm = input("\nAdd this exclusion? (y/n): ").strip().lower()
    if confirm != 'y':
        print("Cancelled.")
        return
    
    # Add exclusion
    exclusion = {
        "start_line": start_line,
        "end_line": end_line,
        "start_char": start_char,
        "end_char": end_char,
        "reason": reason
    }
    
    if 'exclusions' not in metadata['boundaries']:
        metadata['boundaries']['exclusions'] = []
    
    metadata['boundaries']['exclusions'].append(exclusion)
    
    # Save
    with open(metadata_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Exclusion added successfully!")
    print(f"   Total exclusions: {len(metadata['boundaries']['exclusions'])}")

def list_metadata_files():
    """List all available metadata files."""
    if not METADATA_DIR.exists():
        print("No metadata directory found.")
        return []
    
    files = list(METADATA_DIR.glob("*.metadata.json"))
    return files

def main():
    """Main interactive menu."""
    print("\n" + "="*60)
    print("📝 Exclusion Range Editor")
    print("="*60)
    
    files = list_metadata_files()
    
    if not files:
        print("\nNo metadata files found. Run auto_curator.py first.")
        return
    
    print(f"\nFound {len(files)} curated file(s):\n")
    for i, filepath in enumerate(files, 1):
        print(f"  {i}. {filepath.name}")
    
    print("\n  0. Exit")
    
    choice = input("\nSelect file number: ").strip()
    
    if choice == "0":
        return
    
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(files):
            add_exclusion_interactive(files[idx].name)
        else:
            print("Invalid selection.")
    except ValueError:
        print("Invalid input.")

if __name__ == "__main__":
    main()
