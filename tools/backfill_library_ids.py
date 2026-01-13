"""
Backfill Project Gutenberg IDs for Existing Library
Scans local text files, finds their PG IDs via API, and updates/generates CODEX files.
"""
import os
import glob
import re
import requests
import subprocess
from rich.console import Console
from rich.prompt import Prompt
from rich.table import Table

console = Console()
API_BASE = "https://gutendex.com/books"

def search_book_api(title, author):
    """Search Gutendex for a book."""
    query = f"{title} {author}"
    try:
        response = requests.get(API_BASE, params={"search": query})
        response.raise_for_status()
        data = response.json()
        return data['results']
    except:
        return []

def get_local_metadata(filepath):
    """Extract rough metadata from filename."""
    filename = os.path.basename(filepath)
    if ' by ' in filename:
        parts = filename.replace('.txt', '').split(' by ')
        title = parts[0].strip()
        author = parts[1].strip()
    else:
        title = filename.replace('.txt', '').strip()
        author = ""
    return title, author

def find_pg_id_in_text(filepath):
    """Try to find PG ID in text content."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            # Read first 5k chars only
            content = f.read(5000)
            
        # Match "eBook #1234"
        match = re.search(r'eBook #(\d+)', content, re.IGNORECASE)
        if match:
            return int(match.group(1))
            
        return None
    except:
        return None

def main():
    console.print("[bold blue]🔄 Library Metadata Backfill[/bold blue]")
    
    library_dir = os.path.dirname(__file__)
    txt_files = glob.glob(os.path.join(library_dir, "*.txt"))
    
    console.print(f"Found {len(txt_files)} files to audit.")
    
    updated_count = 0
    skipped_count = 0
    
    for filepath in txt_files:
        filename = os.path.basename(filepath)
        
        # Skip if already has ID in filename (some users rename like "1234-body.txt")
        # In this user's case, they are "Title by Author.txt"
        
        title, author = get_local_metadata(filepath)
        console.print(f"\n[bold]Checking:[/bold] {filename}")
        
        # 1. Check text content
        found_id = find_pg_id_in_text(filepath)
        source = "Text Header"
        
        # 2. If not in text, search API
        if not found_id:
            console.print(f"   [dim]Searching API for '{title} {author}'...[/dim]")
            results = search_book_api(title, author)
            
            if results:
                # Simple heuristic: take first result
                best = results[0]
                found_id = best['id']
                source = f"API ({best['title'][:30]}...)"
            
        if found_id:
            console.print(f"   ✅ Found ID: [green]{found_id}[/green] via {source}")
            
            # Check if CODEX needs update
            # We assume we always want to run curator to ensure latest format + ID
            
            if Prompt.ask("   Update/Generate CODEX?", choices=["y", "n"], default="y") == "y":
                 subprocess.run(["python", "auto_curator_codex.py", filepath, "--pg-id", str(found_id)], check=False)
                 updated_count += 1
            else:
                 skipped_count += 1
        else:
            console.print(f"   ❌ No ID found.")
            skipped_count += 1
            
    console.print(f"\n[bold green]Backfill Complete![/bold green]")
    console.print(f"Updated: {updated_count} | Skipped: {skipped_count}")

if __name__ == "__main__":
    main()
