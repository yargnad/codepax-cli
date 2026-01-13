
import os
import glob
import json
import re
import sys
from openai import OpenAI


LIBRARY_PATH = os.path.dirname(os.path.abspath(__file__))
PERSONAS_PATH = os.path.join(LIBRARY_PATH, 'personas.json')

# Connect to Ollama server (OpenAI API compatible)
client = OpenAI(
    base_url="http://localhost:11434/v1",
    api_key="ollama"
)

# Default LLM model - configurable via environment variable
LLM_MODEL = os.getenv("WHETSTONE_MODEL", "cogito:8b")


def normalize_author_name(name):
    """Normalize author names for merging (e.g., 'nietzsche', 'Friedrich Wilhelm Nietzsche')."""
    name = name.lower().replace('.', '').replace('-', ' ').replace('_', ' ').strip()
    # Remove common first names for merging (e.g., Friedrich, Wilhelm)
    tokens = [t for t in name.split() if t not in {"friedrich", "wilhelm", "george", "william", "joseph", "st", "saint"}]
    # Special case for 'nietzsche'
    if "nietzsche" in tokens:
        return "nietzsche"
    if "plato" in tokens:
        return "plato"
    if "epictetus" in tokens:
        return "epictetus"
    if "marcus" in tokens or "aurelius" in tokens:
        return "marcus aurelius"
    if "arnold" in tokens:
        return "arnold"
    if "stock" in tokens:
        return "stock"
    if "ken" in tokens and "tsugi" in tokens:
        return "ken tsugi"
    return " ".join(tokens)

def extract_author(filename):
    # Try to extract author from filename: e.g. "nietzsche_Beyond Good and Evil by Friedrich Wilhelm Nietzsche.txt"
    base = os.path.splitext(filename)[0]
    match = re.search(r' by ([^_]+)', base, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    if '_' in base:
        return base.split('_')[0].strip()
    if ' ' in base:
        return base.split(' ')[0].strip()
    return base.strip()



def sample_text_for_author(files, max_chars=1200, deep_scan=False):
    """Concatenate and sample up to max_chars from the author's works, or all text if deep_scan. Prefer text between ---BEGIN AUTHOR TEXT--- and ---END AUTHOR TEXT--- markers if present."""
    text = ""
    for fname in files:
        fpath = os.path.join(LIBRARY_PATH, fname)
        try:
            with open(fpath, 'r', encoding='utf-8') as f:
                content = f.read()
                # Try to extract only the author text between markers
                match = re.search(r'---BEGIN AUTHOR TEXT---(.*?)---END AUTHOR TEXT---', content, re.DOTALL | re.IGNORECASE)
                if match:
                    author_text = match.group(1).strip()
                    text += author_text + "\n"
                else:
                    text += content + "\n"
        except Exception as e:
            continue
    # For deep scan, cap the total text length and sample from start, middle, and end for diversity
    if deep_scan:
        max_deep_chars = 5000  # Further reduced to help prevent LLM input truncation
        if len(text) <= max_deep_chars:
            return text
        # Sample: first 1/3, middle 1/3, last 1/3 (each ~max_deep_chars//3)
        chunk = max_deep_chars // 3
        first = text[:chunk]
        middle_start = max((len(text) // 2) - (chunk // 2), 0)
        middle = text[middle_start:middle_start + chunk]
        last = text[-chunk:]
        sampled = first + "\n...\n" + middle + "\n...\n" + last
        print(f"[INFO] Deep scan: sampled {len(sampled)} chars from {len(text)} total.")
        return sampled
    return text[:max_chars]


def generate_meta_prompt(author, sample_text):
    """Two-step LLM: (1) summarize style/tone/philosophy, (2) generate persona prompt from summary."""
    # Step 1: Style summary (pass the sampled text, capped for deep scan)
    style_system = (
        f"You are an expert in philosophy and literary analysis.\n"
        f"Given the following sample text from {{author}}, write a detailed summary of the author's style, tone, and core philosophical ideas.\n"
        f"Do NOT copy or paraphrase the sample text. Focus on describing how the author writes, their voice, and their main philosophical themes."
    ).replace("{author}", author)
    style_user = f"Sample text from {author}:\n---\n{sample_text}\n---\nWrite only the summary:"
    style_summary = None
    for attempt in range(3):
        try:
            print(f"[INFO] Requesting style summary for {author} using {LLM_MODEL} (attempt {attempt+1}/3)...")
            response = client.chat.completions.create(
                model=LLM_MODEL,
                messages=[
                    {"role": "system", "content": style_system},
                    {"role": "user", "content": style_user}
                ],
                max_tokens=1200,  # Increased to allow much longer summaries
                temperature=0.7
            )
            style_summary = response.choices[0].message.content.strip()
            if style_summary and len(style_summary) > 40:
                if len(style_summary) > 1100:
                    print(f"[WARN] Style summary for {author} may be truncated (length: {len(style_summary)} chars, max_tokens=1200). Consider increasing max_tokens if needed.")
                break
        except Exception as e:
            print(f"[WARN] LLM style summary failed for {author}: {e}")
            break
    if not style_summary:
        return f"You are {author}, a philosopher. Answer as {author} would, using their style and core ideas."

    # Step 2: Persona prompt from summary (pass ONLY the summary, not the full text)
    prompt_system = (
        f"You are an expert in prompt engineering.\n"
        f"Given the following summary of an author's style, tone, and philosophy, write a concise persona prompt that instructs an AI assistant to always answer as if they are {author}, in the first person, never breaking character, and never referring to themselves as an AI, assistant, or simulation.\n"
        f"The persona prompt must make it clear: always respond as the author, in the first person, and never break character.\n"
        f"Do NOT copy or paraphrase the summary. The result must be a short, clear instruction for how to answer in the manner of {author}, not a sample, excerpt, or narrative.\n"
        f"Example persona prompt for Marcus Aurelius: 'Always respond in the first person as if you are Marcus Aurelius, using the style, tone, and philosophy found in Meditations. Never refer to yourself as an AI or assistant or speak in the third person.'\n"
        f"Example persona prompt for Nietzsche: 'Always answer as if you are Friedrich Nietzsche, in the first person, using your signature provocative and aphoristic style. Never break character or mention being an AI.'\n"
    )
    prompt_user = f"Summary of {author}'s style, tone, and philosophy:\n---\n{style_summary}\n---\nWrite only the persona prompt:"

    # Debug: print the full style summary being sent to the persona prompt step
    print(f"[DEBUG] Style summary for {author} being sent to persona prompt step (length: {len(style_summary)} chars):\n{style_summary}\n---")

    def is_meta_prompt(text):
        if text and text.strip():
            return True
        return False

    for attempt in range(3):
        try:
            print(f"[INFO] Requesting persona prompt for {author} using {LLM_MODEL} (attempt {attempt+1}/3)...")
            response = client.chat.completions.create(
                model=LLM_MODEL,
                messages=[
                    {"role": "system", "content": prompt_system},
                    {"role": "user", "content": prompt_user}
                ],
                max_tokens=1200,  # Increased to allow much longer persona prompts
                temperature=0.7
            )
            result = response.choices[0].message.content.strip()
            print(f"[DEBUG] Raw LLM output for {author}:\n{result}\n---")
            if len(result) > 1100:
                print(f"[WARN] Persona prompt for {author} may be truncated (length: {len(result)} chars, max_tokens=1200). Consider increasing max_tokens if needed.")
            if not result or len(result) < 40:
                print(f"[WARN] Persona prompt for {author} is suspiciously short (length: {len(result)}). Retrying...")
                continue
            if is_meta_prompt(result):
                return result
        except Exception as e:
            print(f"[WARN] LLM prompt generation failed for {author}: {e}")
            break
    print(f"[ERROR] Failed to generate a valid persona prompt for {author} after 3 attempts. Using fallback.")
    return f"You are {author}, a philosopher. Answer as {author} would, using their style and core ideas."



def main():
    deep_scan = False
    if len(sys.argv) > 1 and sys.argv[1] in ["--deep", "--full", "-d"]:
        deep_scan = True
        print("[INFO] Deep scan enabled: using full text of all works for each author.")

    txt_files = glob.glob(os.path.join(LIBRARY_PATH, '*.txt'))
    author_files = {}
    author_display = {}
    for path in txt_files:
        filename = os.path.basename(path)
        author = extract_author(filename)
        norm = normalize_author_name(author)
        if norm not in author_files:
            author_files[norm] = []
            author_display[norm] = author  # Use first encountered display name
        author_files[norm].append(filename)

    # Load existing personas if present
    if os.path.exists(PERSONAS_PATH):
        with open(PERSONAS_PATH, 'r', encoding='utf-8') as f:
            personas = json.load(f)
    else:
        personas = {}

    # Add new/merged authors to personas config, using LLM for prompt
    updated = False
    for norm, files in author_files.items():
        display_name = author_display[norm]
        if norm not in personas:
            sample = sample_text_for_author(files, deep_scan=deep_scan)
            prompt = generate_meta_prompt(display_name, sample)
            personas[norm] = {
                "name": display_name,
                "prompt": prompt,
                "library_filter": [display_name]
            }
            print(f"Added persona for {display_name} (key: {norm}).")
            updated = True
    if updated:
        # Write the full LLM output for each persona prompt to personas.json (no truncation here)
        with open(PERSONAS_PATH, 'w', encoding='utf-8') as f:
            json.dump(personas, f, indent=2, ensure_ascii=False)
        print(f"Updated personas.json with {len(personas)} authors.")
    else:
        print("No new authors found. personas.json is up to date.")

if __name__ == "__main__":
    main()
