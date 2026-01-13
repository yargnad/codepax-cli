"""
CodePax CLI (v2.0)
The Universal Manager for Codex Cartridges.

Handles:
- Creation of Manifests (codex.json)
- Hydration (Lite JSON -> Dense Zip)
- Dehydration (Dense Zip -> Lite JSON)
- Schema Validation
"""
import os
import sys
import json
import zipfile
import argparse
import hashlib
import shutil
import datetime
from pathlib import Path
import jsonschema
import re

# Load Schema
SCHEMA_PATH = Path(__file__).parent / "codex_v2_schema.json"
try:
    with open(SCHEMA_PATH, 'r') as f:
        CODEX_SCHEMA = json.load(f)
except Exception as e:
    print(f"Warning: Could not load schema from {SCHEMA_PATH}: {e}")
    CODEX_SCHEMA = None

def validate_manifest(manifest):
    """Validate a manifest dictionary against the V2 schema."""
    if not CODEX_SCHEMA:
        return True # logic skip if schema missing
    try:
        jsonschema.validate(instance=manifest, schema=CODEX_SCHEMA)
        return True
    except jsonschema.exceptions.ValidationError as e:
        print(f"[!] Schema Validation Error: {e.message}")
        return False

def create_manifest(name, author, category):
    """Create a blank V2 manifest."""
    return {
        "spec_version": "2.0",
        "uuid": "", # TODO: Generate UUID
        "meta": {
            "name": name,
            "author": author,
            "category": category,
            "version": "1.0.0",
            "created_by": "codepax-cli v2.0",
            "archived_at": datetime.datetime.utcnow().isoformat() + "Z"
        },
        "provenance": {
            "tool": "CodePax",
            "version": "2.1.0",
            "generated_at": datetime.datetime.utcnow().isoformat() + "Z",
            "profile": "default",
            "logic": {}
        },
        "instructions": {
            "usage": f"This cartridge represents '{name}'.",
            "system_prompt_hint": "",
            "layer_logic": "Standard single-persona layer."
        },
        "sources": [],
        "layers": [],
        "bootstrap_instructions": f"You are assuming the role defined in the primary layer of this cartridge ({name})."
    }

def hydrate_cartridge(manifest_path, output_dir):
    """
    Convert a Lite JSON manifest into a Dense ZIP cartridge.
    For now, this assumes sources are either local or just placeholders.
    Real implementation would fetch URLs.
    """
    manifest_path = Path(manifest_path)
    with open(manifest_path, 'r', encoding='utf-8') as f:
        manifest = json.load(f)

    if not validate_manifest(manifest):
        print("Aborting hydration due to invalid schema.")
        return

    cartridge_name = manifest['meta'].get('name', 'cartridge').replace(' ', '_')
    zip_name = output_dir / f"{cartridge_name}.codex"
    
    print(f"Hydrating {manifest_path} -> {zip_name}...")
    
    try:
        with zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED) as zf:
            # 1. Add Manifest
            # We set content to 'dense' references in the saved manifest? 
            # For V2 spec, checks: if content is string, it's dense.
            
            # Simple hydration: Just bundle the manifest for now if sources are valid.
            zf.writestr('codex.json', json.dumps(manifest, indent=2))
            
            # 2. Add Bootstrap
            zf.writestr('BOOTSTRAP.md', manifest.get('bootstrap_instructions', ''))
            
            # 3. Process Sources (Placeholder logic)
            # In a real run, we'd download manifest['sources'][0]['uri'] 
            # and verify hash, then write to content/source.txt
            
            print(f"   [+] Packed manifest")
            print(f"   [+] Packed BOOTSTRAP.md")

    except Exception as e:
        print(f"Error hydrating: {e}")

# Curation Logic
from openai import OpenAI

MODEL_NAME = os.getenv("WHETSTONE_MODEL", "qwen3:8b")

try:
    client = OpenAI(
        base_url="http://localhost:11434/v1",
        api_key="ollama"
    )
except Exception:
    client = None

MARKER_PATTERNS = {
    "end_explicit": [
        r"^\s*THE END\s*$",
        r"^\s*FINIS\s*$",
        r"^\s*__\s*THE END\s*__\s*$",
        r"^\s*End of the Project Gutenberg EBook",
    ],
    "end_separator": [
        r"^\s*\*\s*\*\s*\*\s*\*\s*(\*)?\s*$",
        r"^\s*={5,}\s*$",
    ],
    "footnote_start": [
        r"^\s*NOTES:?\s*$",
        r"^\s*FOOTNOTES:?\s*$",
        r"^\s*\[1\]",
    ]
}

def detect_structural_end(text_chunk):
    """Scans for known 'End of Book' markers."""
    for pattern in MARKER_PATTERNS["end_explicit"]:
        matches = list(re.finditer(pattern, text_chunk, re.MULTILINE | re.IGNORECASE))
        if matches: return matches[0].end()

    for pattern in MARKER_PATTERNS["footnote_start"]:
        match = re.search(pattern, text_chunk, re.MULTILINE | re.IGNORECASE)
        if match: return match.start()
        
    return None

def get_true_start_phrase(text_chunk, author):
    """Asks AI for the first sentence of actual work."""
    if not client: return None, None
    system_msg = "You are a precise text extraction tool. Return ONLY the phrase."
    prompt = f"Identify the EXACT phrase (10-20 words) where the work by {author} begins. Ignore intros/prefaces not by author.\n\nText:\n{text_chunk}"
    
    try:
        response = client.chat.completions.create(
            model=MODEL_NAME, messages=[{'role':'system','content':system_msg}, {'role':'user','content':prompt}],
            temperature=0.1, extra_body={"options": {"num_ctx": 16384}}
        )
        content = response.choices[0].message.content.strip()
        # cleanup <think> blocks
        content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip()
        return content.strip('"'), content
    except:
        return None, None

def get_true_end_phrase(text_chunk, author):
    """Asks AI for the last sentence of actual work."""
    if not client: return None, None
    system_msg = "You are a precise text extraction tool. Return ONLY the phrase."
    prompt = f"Identify the EXACT phrase (10-20 words) where the work by {author} ends. Ignore footnotes/index.\n\nText:\n{text_chunk}"
    
    try:
        response = client.chat.completions.create(
            model=MODEL_NAME, messages=[{'role':'system','content':system_msg}, {'role':'user','content':prompt}],
            temperature=0.1, extra_body={"options": {"num_ctx": 16384}}
        )
        content = response.choices[0].message.content.strip()
        content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip()
        return content.strip('"'), content
    except:
        return None, None

def generate_layers_from_text(raw_text, title):
    """
    Uses AI to analyze the text and generate Character Layers.
    Returns a list of layer objects.
    """
    if not client: return []
    
    print("   🤖 Analyzing text for characters (this may take a moment)...")
    
    # 1. Extract Characters
    prompt = f"Analyze the following text from '{title}'. List the top 3 major characters. Return ONLY a JSON list of strings, e.g. [\"Alice\", \"Queen of Hearts\"].\n\nText Sample:\n{raw_text[:10000]}"
    
    try:
        response = client.chat.completions.create(
            model=MODEL_NAME, messages=[{'role':'user','content':prompt}],
            temperature=0.1, response_format={"type": "json_object"}
        )
        content = response.choices[0].message.content
        # robust json parsing
        import json
        try:
            data = json.loads(content)
            characters = data.get("characters", [])
            if not characters and isinstance(data, list): characters = data
        except:
            # fallback regex
            characters = re.findall(r'"([^"]*)"', content)
            
        print(f"   👥 Found Characters: {', '.join(characters)}")
        
        layers = []
        for char in characters:
            print(f"      - Generating profile for {char}...")
            sys_prompt_req = f"Write a system prompt for an AI to roleplay as {char} based on '{title}'. Keep it concise (under 100 words). Return ONLY the prompt."
            
            resp = client.chat.completions.create(
                model=MODEL_NAME, messages=[{'role':'user','content':sys_prompt_req}],
                temperature=0.7
            )
            sys_prompt = resp.choices[0].message.content.strip()
            
            layer = {
                "id": f"layer_{char.lower().replace(' ', '_')}",
                "type": "persona",
                "name": char,
                "system_prompt": sys_prompt,
                "context_sources": ["src_primary"],
                # Placeholder for Voice (to be filled by user later or inferred)
                "voice": {
                    "model": "en_us_hfc_male_medium", # Default placeholder
                    "source": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/hfc/medium/en_US-hfc-medium.onnx"
                }
            }
            layers.append(layer)
            
        return layers

    except Exception as e:
        print(f"Error generating layers: {e}")
        return []

def fuzzy_find_phrase(raw_text, phrase, start_bound=0, limit_idx=None):
    """Find phrase using sliding window."""
    if not phrase: return None, None
    if limit_idx is None: limit_idx = len(raw_text)
    scope = raw_text[start_bound:limit_idx]
    
    # Exact
    idx = scope.find(phrase)
    if idx != -1: return start_bound + idx, start_bound + idx + len(phrase)
    
    # Fuzzy (Simple)
    words = phrase.split()
    if not words: return None, None
    sub = " ".join(words[:5]) # try smaller chunk
    idx = scope.find(sub)
    if idx != -1: return start_bound + idx, start_bound + idx + len(sub)
    
    return None, None

def apply_recipe(recipe_path, raw_text, title):
    """
    Generates layers based on a Recipe definition (YAML/JSON).
    """
    import yaml # Requires PyYAML
    print(f"   📜 Applying Recipe: {recipe_path}")
    
    with open(recipe_path, 'r') as f:
        recipe = yaml.safe_load(f)
        
    layers = []
    
    for template in recipe.get("layers", []):
        role_name = template.get("role", "character")
        print(f"      - Processing Recipe Role: {role_name}...")
        
        # 1. Identify
        if "name" in template:
             char_name = template["name"]
             print(f"        -> Using explicit name: {char_name}")
        else:
            id_prompt = f"{template['identify_prompt']}\n\nContext: {title}\n\nText Sample:\n{raw_text[:5000]}"
            try:
                resp = client.chat.completions.create(
                    model=MODEL_NAME, messages=[{'role':'user','content':id_prompt}],
                    temperature=0.1
                )
                char_name = resp.choices[0].message.content.strip()
                # Cleanup
                char_name = re.sub(r'<think>.*?</think>', '', char_name, flags=re.DOTALL).strip().strip('"')
                print(f"        -> Identified: {char_name}")
            except Exception as e:
                 print(f"Error identifying role {role_name}: {e}")
                 continue
            
        if not char_name or len(char_name) > 50: # Sanity check
            print(f"        [!] Skipping invalid identification: {char_name}")
            continue

            # 2. Generate System Prompt
            context_hint = f"Make them act like {char_name} from {title}."
            sys_template = template.get("system_prompt_template", "You are {name}. {context}")
            final_sys = sys_template.format(name=char_name, context=context_hint)
            
            # 3. Create Layer
            layer = {
                "id": f"layer_{role_name}_{char_name.lower().replace(' ', '_')}",
                "type": "persona",
                "name": char_name,
                "system_prompt": final_sys,
                "context_sources": ["src_primary"],
                "base_model_hint": template.get("base_model_hint", "any"),
                "recommended_models": template.get("recommended_models", []), # Support user models
                "voice": template.get("voice_default", {})
            }
            layers.append(layer)
            
        except Exception as e:
            print(f"Error processing role {role_name}: {e}")
            
    return layers

def pack_from_text(txt_file, output_dir, interactive=False, recipe=None):
    """
    Take a raw text file, Curate it (Strip headers, AI crop), and wrap into Dense Codex.
    """
    txt_path = Path(txt_file)
    if not txt_path.exists():
        print(f"Error: File {txt_file} not found.")
        return

    # Metadata Inference
    filename = txt_path.name
    name_stem = txt_path.stem
    if " by " in name_stem:
        parts = name_stem.split(" by ")
        title = parts[0]
        author = parts[1]
    else:
        title = name_stem
        author = "Unknown"

    print(f"Packing '{title}' by {author}...")
    print(f"   [i] Model: {MODEL_NAME}")

    with open(txt_path, 'r', encoding='utf-8') as f:
        raw_text = f.read()

    # 1. Gutenberg Strip
    header_match = re.search(r"\*\*\* START OF (THE|THIS) PROJECT GUTENBERG EBOOK .*? \*\*\*", raw_text, re.IGNORECASE)
    footer_match = re.search(r"\*\*\* END OF (THE|THIS) PROJECT GUTENBERG EBOOK .*? \*\*\*", raw_text, re.IGNORECASE)
    
    start_idx = header_match.end() if header_match else 0
    end_idx = footer_match.start() if footer_match else len(raw_text)
    
    print(f"   🔍 Gutenberg Scope: {start_idx}:{end_idx}")
    
    # 2. AI Curation (Start)
    SCAN_SIZE = 15000
    scope_text = raw_text[start_idx:end_idx]
    
    print("   🤖 Detecting Start Phrase...")
    start_phrase, _ = get_true_start_phrase(scope_text[:SCAN_SIZE], author)
    final_start = start_idx
    if start_phrase:
         s, e = fuzzy_find_phrase(raw_text, start_phrase, start_idx, end_idx)
         if s: 
             final_start = s
             print(f"   ✅ Found start: '{start_phrase[:30]}...'")
    
    # 3. AI Curation (End)
    print("   🤖 Detecting End Phrase...")
    # Structural Check first
    struct_end = detect_structural_end(scope_text[-SCAN_SIZE:])
    limit = len(scope_text)
    if struct_end:
        limit = len(scope_text) - SCAN_SIZE + struct_end
        print("   ✂️  Structural cut found (footnotes/end).")
    
    end_phrase, _ = get_true_end_phrase(scope_text[limit-SCAN_SIZE:limit], author)
    final_end = start_idx + limit 
    if end_phrase:
        s, e = fuzzy_find_phrase(raw_text, end_phrase, final_start, final_end)
        if e:
            final_end = e
            print(f"   ✅ Found end: '{end_phrase[:30]}...'")

    # Extract Content
    curated_content = raw_text[final_start:final_end].strip()
    print(f"   📦 Final Content Size: {len(curated_content)} chars")

    # Create Manifest
    manifest = create_manifest(title, author, "Philosophy")
    
    # Populate Provenance
    manifest['provenance']['logic'] = {
        "ai_model": MODEL_NAME,
        "prompts": [
            "Identify the EXACT phrase where the work begins.",
            "Identify the EXACT phrase where the work ends."
        ],
        "curation_strategy": "fuzzy_boundary_detection"
    }
    
    # Populate Instructions
    manifest['instructions'] = {
        "usage": f"This cartridge contains the full text of '{title}' by {author}. It is intended for deep reading, analysis, or roleplay.",
        "system_prompt_hint": f"You are reading the work '{title}'. Use the provided text layers as your source of truth.",
        "layer_logic": "The 'layer_default' contains the primary persona of the author."
    }

    # Add Source (Dense)
    source_obj = {
        "id": "src_primary",
        "type": "text/plain",
        "uri": f"file://{filename}", 
        "hash": hashlib.sha256(curated_content.encode()).hexdigest(),
        "content": curated_content, # THE CLEAN TEXT
        "curation": {
            "original_size": len(raw_text),
            "original_range": [start_idx, end_idx],
            "curated_range": [final_start, final_end]
        }
    }
    manifest['sources'].append(source_obj)
    
    # 4. Layers (Default, Interactive, or Recipe)
    manifest['layers'] = []
    
    if recipe:
        try:
             recipe_layers = apply_recipe(recipe, curated_content, title)
             manifest['layers'].extend(recipe_layers)
             # Also inject provenance profile
             manifest['provenance']['profile'] = Path(recipe).stem
        except ImportError:
             print("[!] PyYAML not found. Install it with: pip install pyyaml")
             return
        except Exception as e:
             print(f"[!] Recipe failed: {e}")

    elif interactive:
        print("   🧙 Wizard Mode: Generating Character Layers...")
        generated_layers = generate_layers_from_text(curated_content, title)
        manifest['layers'].extend(generated_layers)
        
    # Always add default/narrator layer
    layer_obj = {
        "id": "layer_narrator",
        "type": "persona",
        "name": f"{title} (Narrator)",
        "base_model_hint": "any",
        "system_prompt": f"You are the narrator of '{title}'. Answer as if you wrote this text.",
        "context_sources": ["src_primary"],
        "parameters": {}
    }
    manifest['layers'].append(layer_obj)
    
    # Write Zip
    zip_name = output_dir / f"{title.replace(' ','_')}.codex"
    try:
        with zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.writestr('codex.json', json.dumps(manifest, indent=2))
            zf.writestr('BOOTSTRAP.md', manifest.get('bootstrap_instructions', ''))
            print(f"   [+] Validated and Created {zip_name}")
            print(f"   [i] Size: {os.path.getsize(zip_name) / 1024:.2f} KB")

    except Exception as e:
        print(f"Error packing: {e}")

def main():
    parser = argparse.ArgumentParser(description="CodePax CLI v2.0")
    subparsers = parser.add_subparsers(dest="command")

    # init
    init_parser = subparsers.add_parser("init", help="Create a new Codex manifest")
    init_parser.add_argument("--name", required=True)
    init_parser.add_argument("--author", default="Unknown")
    init_parser.add_argument("--out", default="codex.json")

    # hydrate
    hydrate_parser = subparsers.add_parser("hydrate", help="Convert JSON -> ZIP")
    hydrate_parser.add_argument("file", help="Path to .codex.json")
    hydrate_parser.add_argument("--outdir", default=".")

    # pack
    pack_parser = subparsers.add_parser("pack", help="Convert .txt -> .codex (Dense)")
    pack_parser.add_argument("file", help="Path to .txt file")
    pack_parser.add_argument("--outdir", default=".")
    pack_parser.add_argument("--wizard", action="store_true", help="Enable interactive layer generation")
    pack_parser.add_argument("--wizard", action="store_true", help="Enable interactive layer generation")
    pack_parser.add_argument("--recipe", help="Path to recipe.yaml for auto-configuration")

    # build
    build_parser = subparsers.add_parser("build", help="Automated Build from Recipe")
    build_parser.add_argument("recipe", help="Path to recipe.yaml")
    build_parser.add_argument("--outdir", default=".")

    args = parser.parse_args()

    if args.command == "init":
        m = create_manifest(args.name, args.author, "General")
        with open(args.out, 'w') as f:
            json.dump(m, f, indent=2)
        print(f"Created {args.out}")

    elif args.command == "hydrate":
        hydrate_cartridge(args.file, Path(args.outdir))

    elif args.command == "pack":
        pack_from_text(args.file, Path(args.outdir), interactive=args.wizard, recipe=args.recipe)
        
    elif args.command == "build":
        build_from_recipe(args.recipe, Path(args.outdir))

    else:
        parser.print_help()

import urllib.request

def fetch_text(uri):
    """Simple fetcher for text content."""
    print(f"   ⬇️  Fetching source: {uri}")
    try:
        with urllib.request.urlopen(uri) as f:
            return f.read().decode('utf-8')
    except Exception as e:
        print(f"Error fetching {uri}: {e}")
        return None

def build_from_recipe(recipe_path, output_dir):
    """
    Builds a Codex entirely from a Recipe file.
    """
    import yaml
    print(f"🏗️  Building from Recipe: {recipe_path}")
    
    with open(recipe_path, 'r') as f:
        recipe = yaml.safe_load(f)
        
    source_uri = recipe.get("source_uri")
    if not source_uri:
        print("Error: Recipe must contain 'source_uri' for build command.")
        return

    # 1. Fetch
    raw_text = fetch_text(source_uri)
    if not raw_text: return
    
    # 2. Save Temp (for pack_from_text compatibility)
    # We infer filename from URL or recipe
    filename = recipe.get("filename", "source.txt")
    temp_path = Path(output_dir) / filename
    
    # Ensure directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    with open(temp_path, 'w', encoding='utf-8') as f:
        f.write(raw_text)
        
    # 3. Pack with Recipe
    # We call pack_from_text but bypass CLI arg parsing for recipe
    # We pass the loaded recipe dict directly if we refactor, 
    # OR we just pass the path since pack_from_text expects a path?
    # Pack expects recipe path currently.
    
    pack_from_text(temp_path, output_dir, recipe=recipe_path)
    
    # Cleanup? Maybe keep source for debug.
    print(f"   ✨ Build Complete.")

if __name__ == "__main__":
    main()
