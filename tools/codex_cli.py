"""
CODEX CLI Manager
An Ollama-like CLI for managing and running literary persona cartridges.

Usage:
  codex pull "Marcus Aurelius"   # Search, download, and curate
  codex list                     # List installed cartridges
  codex run "Frodo"              # Start a chat session (placeholder)
  codex rm "19978"               # Remove a cartridge
"""
import os
import sys
import glob
import json
import argparse
import subprocess
import shutil
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt

# Import browser logic
from pg_browser import search_books, download_book

console = Console()
BASE_DIR = os.path.dirname(__file__)
CODEX_DIR = os.path.abspath(os.path.join(BASE_DIR, "codex_library"))
os.makedirs(CODEX_DIR, exist_ok=True)

def list_cartridges():
    """List installed CODEX cartridges."""
    files = glob.glob(os.path.join(CODEX_DIR, "*.codex"))
    
    table = Table(title="Installed Cartridges (CODEX Library)")
    table.add_column("Name", style="bold cyan")
    table.add_column("ID", style="dim")
    table.add_column("Author", style="green")
    table.add_column("Size", justify="right")
    table.add_column("Category", style="magenta") # inferred

    for f in files:
        name = os.path.basename(f).replace('.codex', '')
        size_mb = os.path.getsize(f) / (1024 * 1024)
        
        # Try to read metadata from zip without full extraction
        try:
            import zipfile
            with zipfile.ZipFile(f, 'r') as z:
                meta = json.loads(z.read('codex.json'))
                author = meta['work']['author']
                pg_id = meta['source']['pg_id']
                
                # Simple heuristic for category
                subjects = str(meta['work'].get('subjects', [])).lower()
                category = "Philosophy" 
                if "fiction" in subjects or "drama" in subjects or "poetry" in subjects:
                    category = "Literature/Fiction"
                if "history" in subjects:
                    category = "History"
                    
        except:
            author = "Unknown"
            pg_id = "?"
            category = "Unknown"

        table.add_row(name, str(pg_id), author, f"{size_mb:.1f} MB", category)

    console.print(table)
    console.print(f"[dim]Total: {len(files)} cartridges[/dim]")

def pull_cartridge(query):
    """Search, download, and curate a new cartridge."""
    console.print(f"[bold green]Pulling '{query}'...[/bold green]")
    
    # 1. Search
    results = search_books(query)
    if not results:
        console.print("[red]No books found.[/red]")
        return

    # If multiple results, ask user or pick top philosophy one? 
    # For a CLI 'pull', we might want to be interactive if ambiguous, 
    # or just take the top result like docker/ollama if exact match.
    
    # Let's show top 5 and ask
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("#", style="dim", width=4)
    table.add_column("Title")
    table.add_column("Author")
    table.add_column("Category")
    
    for i, book in enumerate(results[:5]):
        subjects = ",".join(book.get('subjects', []))
        cat = "Philosophy" if "Philosophy" in subjects else "General"
        table.add_row(str(i+1), book['title'][:60], book['authors'][0]['name'], cat)
        
    console.print(table)
    
    choice = Prompt.ask("Select a number to pull", choices=[str(i+1) for i in range(len(results[:5]))] + ['q'], default='1')
    if choice == 'q':
        return

    book = results[int(choice)-1]
    
    # 2. Download
    txt_filename = download_book(book)
    if not txt_filename:
        return

    # 3. Curate
    console.print(f"[bold]Curating '{book['title']}' into CODEX format...[/bold]")
    # Run auto_curator_codex.py via subprocess to ensure clean state
    # Pass explicit ID
    cmd = ["python", "auto_curator_codex.py", txt_filename, "--pg-id", str(book['id'])]
    
    # If high-performance mode requested (user has 128GB RAM!)
    # We could set the model env var here if we had a config
    
    subprocess.run(cmd)
    
    # Clean up raw txt file?
    # For now, keep it in library as cache, or move to tmp?
    # The existing flow keeps .txt in library. 
    console.print(f"[bold green]Successfully pulled '{book['title']}'![/bold green]")

def run_chat(name):
    """Start a chat session (Placeholder for Whetstone integration)."""
    # Find the codex file
    matches = glob.glob(os.path.join(CODEX_DIR, f"*{name}*.codex"))
    if not matches:
        console.print(f"[red]Cartridge '{name}' not found. Try 'codex list'[/red]")
        return
    
    target = matches[0]
    cartridge_name = os.path.basename(target).replace('.codex', '')
    
    console.print(Panel(f"[bold yellow]Initializing Persona: {cartridge_name}[/bold yellow]\n[dim]Loading CODEX cartridge...[/dim]"))
    
    # In a real integration, this would load the persona generator
    console.print("\n[i] Frodo: Hello! I am ready to speak with you. (Simulated)[/i]")
    
    while True:
        user_input = Prompt.ask(f"[bold cyan]You[/bold cyan]")
        if user_input.lower() in ('exit', 'quit'):
            break
        console.print(f"[bold green]{cartridge_name}[/bold green]: That is an interesting question regarding '{user_input}'. [dim](Whetstone integration pending)[/dim]")

def main():
    parser = argparse.ArgumentParser(description="CODEX CLI Manager")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Pull
    pull_parser = subparsers.add_parser("pull", help="Download and curate a cartridge")
    pull_parser.add_argument("query", help="Name of book or author to pull")

    # List
    list_parser = subparsers.add_parser("list", help="List installed cartridges")

    # Run
    run_parser = subparsers.add_parser("run", help="Run a persona from a cartridge")
    run_parser.add_argument("name", help="Name of cartridge to run")

    args = parser.parse_args()

    if args.command == "list":
        list_cartridges()
    elif args.command == "pull":
        pull_cartridge(args.query)
    elif args.command == "run":
        run_chat(args.name)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
