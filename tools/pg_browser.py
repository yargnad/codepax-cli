"""
Project Gutenberg Browser & Downloader
Uses Gutendex API to search and download books, then auto-curates them.
"""
import os
import sys
import requests
import argparse
import subprocess
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt

console = Console()
API_BASE = "https://gutendex.com/books"

def search_books(query):
    """Search for books using Gutendex API."""
    with console.status(f"[bold green]Searching for '{query}'..."):
        try:
            response = requests.get(API_BASE, params={"search": query})
            response.raise_for_status()
            data = response.json()
            return data['results']
        except Exception as e:
            console.print(f"[bold red]Error searching:[/bold red] {e}")
            return []

def display_results(books):
    """Display search results in a table."""
    table = Table(title="Search Results")
    table.add_column("ID", justify="right", style="cyan", no_wrap=True)
    table.add_column("Title", style="magenta")
    table.add_column("Author", style="green")
    table.add_column("Downloads", justify="right", style="yellow")

    for book in books:
        authors = ", ".join([a['name'] for a in book['authors']])
        title = book['title'][:50] + "..." if len(book['title']) > 50 else book['title']
        table.add_row(str(book['id']), title, authors, str(book['download_count']))

    console.print(table)

def download_book(book):
    """Download the text version of a book."""
    book_id = book['id']
    title = book['title']
    
    # Try to find plain text format
    formats = book['formats']
    text_url = formats.get('text/plain; charset=utf-8') or formats.get('text/plain')
    
    if not text_url:
        # Fallback to standard PG URL pattern
        text_url = f"https://www.gutenberg.org/files/{book_id}/{book_id}-0.txt"
        console.print(f"[yellow]No text format in API. Trying fallback: {text_url}[/yellow]")

    console.print(f"[bold]Downloading:[/bold] {title} (ID: {book_id})")
    
    try:
        response = requests.get(text_url)
        response.raise_for_status()
        
        # Check if we got a valid text file (sometimes fallback redirects to a generic page)
        if "<!DOCTYPE html>" in response.text[:100]:
             # Try another fallback
             text_url = f"https://www.gutenberg.org/cache/epub/{book_id}/pg{book_id}.txt"
             console.print(f"[yellow]Fallback failed. Trying cache URL: {text_url}[/yellow]")
             response = requests.get(text_url)
             response.raise_for_status()

        # Sanitize filename
        safe_title = "".join([c for c in title if c.isalpha() or c.isdigit() or c==' ']).rstrip()
        filename = f"{safe_title} by {book['authors'][0]['name'].split(',')[0]}.txt"
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(response.text)
            
        console.print(f"[bold green]Saved to:[/bold green] {filename}")
        return filename
        
    except Exception as e:
        console.print(f"[bold red]Download failed:[/bold red] {e}")
        return None

def main():
    console.print("[bold blue]📖 Project Gutenberg Browser[/bold blue]")
    
    while True:
        query = Prompt.ask("\n[bold]Search (or 'q' to quit)[/bold]")
        if query.lower() in ('q', 'quit', 'exit'):
            break
            
        books = search_books(query)
        
        if not books:
            console.print("[yellow]No results found.[/yellow]")
            continue
            
        display_results(books)
        
        selection = Prompt.ask("[bold]Enter ID to download (or 's' to search again)[/bold]")
        if selection.lower() == 's':
            continue
            
        try:
            selected_id = int(selection)
            selected_book = next((b for b in books if b['id'] == selected_id), None)
            
            if selected_book:
                filename = download_book(selected_book)
                
                if filename:
                    # Trigger auto-curator
                    if Prompt.ask("Run auto-curator now?", choices=["y", "n"], default="y") == "y":
                         # We'll import and run the function directly to avoid subprocess overhead if possible,
                         # but for now subprocess is safer to keep state clean.
                         console.print(f"[dim]Running auto_curator_codex.py on {filename}...[/dim]")
                         subprocess.run(["python", "auto_curator_codex.py", filename, "--pg-id", str(selected_id)], check=False)
            else:
                console.print("[red]ID not found in search results.[/red]")
                
        except ValueError:
            console.print("[red]Invalid input.[/red]")

if __name__ == "__main__":
    main()
