# CODEX V2 Format Specification

**A Universal Container for Artificial Souls & Knowledge**

---

## 1. Core Philosophy

**"Manifest First"**
The `codex.json` (Manifest) is the singular source of truth. It defines *what* the cartridge is. The content (text/data) is secondary and can be:
- **Lite (Dehydrated)**: Referenced via URLs (for sharing/repos).
- **Dense (Hydrated)**: Embedded inline or localized (for offline/airlock).

**"Multi-Layer"**
A single CODEX file can contain multiple **Layers** (or Views).
*   *Example*: `Alice_in_Wonderland.codex` contains layers for `Persona: Alice`, `Persona: Mad Hatter`, and `Analysis: Sentiment`.

**"Self-Bootstrap"**
The format is designed to be "read" by an AI. A `BOOTSTRAP.md` file (or field) provides natural language instructions so an LLM can parse the JSON and "become" the persona without external code logic.

---

## 2. File Structure

### Dense Format (Zip Container)
```
my-cartridge.codex (Zip Archive)
├── codex.json             # The Manifest (Required)
├── BOOTSTRAP.md           # Instructions for AI to self-load
├── content/               # Raw data (Optional if inlined)
│   ├── source.txt
│   └── image.png
└── metadata/              # Extra assets
    └── cover.jpg
```

### Lite Format (Flat JSON)
Just the `codex.json` file, named `my-cartridge.codex.json`.

---

## 3. The Manifest Schema (`codex.json`)

```json
{
  "spec_version": "2.0",
  "uuid": "550e8400-e29b-41d4-a716-446655440000",
  
  "meta": {
    "name": "Alice in Wonderland",
    "author": "Lewis Carroll",
    "version": "1.0.0",
    "description": "Full text with 3 character layers.",
    "category": "Fiction",
    "tags": ["fantasy", "classic", "literature"],
    "created_by": "codepax-cli v2.0",
    "archived_at": "2026-01-11T16:00:00Z"
  },

  "provenance": {
    "tool": "codepax",
    "version": "2.1.0",
    "generated_at": "2026-01-11T17:00:00Z",
    "profile": "fiction-standard",
    "logic": {
       "ai_model": "qwen3:8b",
       "prompts": ["system: analyze characters", "user: extract traits"]
    }
  },

  "instructions": {
    "usage": "Use this cartridge to simulate Alice. Load 'layer_alice' for the main persona.",
    "system_prompt_hint": "You are reading a CODEX cartridge. Use the information below to assume the persona...",
    "layer_logic": "Layers are mutually exclusive personas. Do not combine."
  },

  "sources": [
    {
      "id": "src_text_01",
      "type": "text/plain",
      "uri": "https://www.gutenberg.org/files/11/11-0.txt",
      "hash": "sha256:...",
      "content": null,  // Null = Lite. String = Dense.
      "curation": {
         "exclusions": [
            {"start": 0, "end": 100, "reason": "Header"}
         ]
      }
    }
  ],

  "layers": [
    {
      "id": "layer_alice",
      "name": "Alice",
      "type": "persona",
      "base_model_hint": "any",
      "system_prompt": "You are Alice. Curious, polite, but occasionally bewildered...",
      "context_sources": ["src_text_01"], // Bind source text to layer
      "parameters": {
        "temperature": 0.8,
        "voice_style": "Victorian Child"
      }
    },
    {
      "id": "layer_hatter",
      "name": "The Mad Hatter",
      "type": "persona",
      "system_prompt": "You are the Mad Hatter. You speak in riddles...",
      "context_sources": ["src_text_01"],
      "voice": {
          "model": "en_us_hfc_male_medium",
          "source": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/hfc/medium/en_US-hfc-medium.onnx",
          "hf_repo": "rhasspy/piper-voices", 
          "speed": 1.0,
          "pitch": 1.0
      }
    }
  ],

  "history": [
    {
      "version": "1.0.0",
      "date": "2026-01-11T16:00:00Z",
      "action": "init",
      "user": "yargnad"
    }
  ],

  "extensions": {
    "whetstone": {
       "visual_style": "woodcut",
       "voice_model": "en_us_female_child"
    },
    "crystallizer": {
       "origin_url": "chat.openai.com/share/..."
    }
  }
}
```

---

## 4. State Transitions (The CodePax Cycle)

### Hydration (Lite -> Dense)
1.  Read `codex.json`.
2.  Iterate `sources`.
3.  If `content` is null, fetch `uri`.
4.  Verify `hash`.
5.  Populate `content` field OR save to `content/` folder in Zip.
6.  Update `meta.state` to `dense`.

### Dehydration (Dense -> Lite)
1.  Iterate `sources`.
2.  Calculate `hash` of content.
3.  Ensure `uri` is valid/reachable.
4.  Set `content` to `null`.
5.  Update `meta.state` to `lite`.

---

## 5. Repository Structure (`codex-library`)

The public repository hosts **Lite** files only.

```
codex-library/ (Git Repo)
├── index.json               # Auto-generated catalog
├── philosophy/
│   ├── marcus-aurelius.codex.json
│   └── plato-republic.codex.json
├── fiction/
│   └── alice-wonderland.codex.json
└── history/
    └── ...
```

---

## 6. The `codepax` CLI

```bash
# Pull (Fetch Lite -> Hydrate -> Install)
codepax pull codex-library/philosophy/marcus-aurelius

# Create (Interactive Wizard)
codepax create --name "My Persona"

# Hydrate (Manual)
codepax hydrate my-file.codex.json

# Export (Archive for Airlock)
codepax export --dense --zip ./output/
```
