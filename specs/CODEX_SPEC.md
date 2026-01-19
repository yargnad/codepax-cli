# CODEX Specification v0.1 (Draft)

Unified, inline-first manifest for portable text, notes, annotations, personas, prompts, and filters. The canonical artifact is a single JSON file that AIs can parse directly; an optional codex.zip is only a compressed wrapper around the same manifest and any hydrated assets.

## Core Principles

1. Manifest-first, inline-friendly. One JSON manifest is authoritative; an AI should not need to unzip anything to use it.
2. Deterministic + portable. Same manifest + validated sources → same outputs across runtimes and models.
3. Provable integrity. Every source carries sha256 + size_bytes; strict mode fails on drift.
4. Transparent provenance. Tools, prompts, and verification notes are recorded.
5. Extensible and safe. Unknown fields are ignored; project data belongs in namespaced extensions.

## Artifact Forms

 - Multi-source URIs: `sources[*].uri` may be a single string or an array of URIs; hydrate/verify will fetch each in order and join with newlines before hashing.

## Top-Level Manifest
 - Hashes: Every sources[*] MUST include hash = sha256:<64 hex> and size_bytes. When content is present, it MUST match the hash/size. When content is null, hydration/verify must fetch, hash, and check.
- uuid (string, RFC 4122).
- meta (object):
 - externs (optional, under extensions.externs): scheme resolvers (template/headers/encoding) for custom URI schemes. Multi-source URIs remain compatible with extern resolution.
  - state (enum: lite, dense)
  - description, category (strings, optional)
  - tags (array of strings, optional)
  - author, created_by, created_at, archived_at (optional strings; created_at/archived_at ISO 8601)
- provenance (object, optional): tool, version, generated_at (ISO 8601), profile, and logic (ai_model, prompts array, parameters object).
- instructions (object, optional): usage (string), system_prompt_hint, layer_logic, bootstrap_hint (all optional strings). All bootstrapping stays inline.
- sources (array): each source is:
  - id (string)
  - uri (string URI or array of URIs)
  - type (string, default text/plain)
  - hash (string, sha256:<hex64>)
  - size_bytes (integer, ≥0)
  - content (string | null | omitted). Null/omitted = Lite; string = hydrated inline.
  - encoding (string, optional, e.g., utf-8)
  - curation (object, optional): exclusions array of {start, end, reason, detection_method?, confidence?}; additional curation metadata allowed.
  - notes (string, optional)
- layers (array): each layer is:
  - id (string), name (string), type (enum: persona, analysis, visuals)
  - base_model_hint (string, optional) and recommended_models (array of strings, optional)
  - system_prompt (string, optional)
  - context_sources (array of source IDs, optional)
  - parameters (object, optional)
  - voice (object, optional): model, source (URI), hf_repo, speed (number), pitch (number)
  - tags (array of strings, optional)
- history (array, optional): entries with version, date (ISO 8601), action, actor, notes.
- extensions (object, optional): namespaced sub-objects, e.g., "whetstone": {...}.
- functions (optional, under extensions.functions): map of function specs keyed by name; each entry must include a name/id and optional description/model/encoding/mode/parameters/notes. CLI validates shape before hydrating func:// URIs.

## Integrity & Validation

- Hashes: Every sources[*] MUST include hash = sha256:<64 hex> and size_bytes. When content is present, it MUST match the hash/size. When content is null, hydration/verify must fetch, hash, and check.
- Optional integrity extras: sources may include expected_digest (upstream checksum), modification_status (clean|drifted|unknown), and modification_history[] entries with observed digests/sizes and timestamps. Hydration/validation updates status/history; strict mode still fails on mismatches.
- Strict vs relaxed: Strict mode fails on any hash/size mismatch or missing required fields; relaxed mode warns but continues.
- URI helpers: pg:// IDs are normalized to numeric Gutenberg IDs (stripping pg/ebooks/cache prefixes and file suffixes) before resolving against extern templates.
- Curation/exclusions hygiene: exclusions should be ordered and non-overlapping; tools SHOULD warn on overlaps.
- Canonical JSON: UTF-8, no BOM. Producers SHOULD emit stable key order when signing, but consumers MUST be order-tolerant.
- Forward compatibility: Unknown fields outside reserved names MUST be ignored by consumers.

## Schema discovery

- Add `$schema` at the top level pointing to the public schema so tools/LLMs can self-validate. Recommended value:
  `"$schema": "https://raw.githubusercontent.com/yargnad/codepax-cli/master/tools/codex_v2_schema.json"`
- Optional but recommended for AI-only portability: embed a **minimal** schema snippet inline (see example) so an AI that cannot fetch URLs can still understand the shape.
- For dense `.codex` zips, optionally include `codex.schema.json` alongside `codex.json` so the schema travels with the artifact.
- The `$schema` field is optional but strongly recommended for portability.

## Lifecycle

- Lite → Hydrate: fetch each source, verify sha256 + size_bytes, optionally inline content, optionally write the manifest and assets into codex.zip, set meta.state = "dense".
- Hydrated assets are stored next to the manifest inside the zip (e.g., content/<id>.<ext>); the manifest remains unchanged except for content and meta.state.
- Dense → Dehydrate: recompute and store hash/size_bytes, set content to null, set meta.state = "lite", optionally drop assets and keep only the manifest.

## Example (Lite, trimmed)

{
  "$schema": "https://raw.githubusercontent.com/yargnad/codepax-cli/master/tools/codex_v2_schema.json",
  "spec_version": "0.1.0",
  "uuid": "550e8400-e29b-41d4-a716-446655440000",
  "meta": {
    "name": "Alice in Wonderland",
    "version": "0.1.0",
    "state": "lite",
    "tags": ["fiction", "persona"]
  },
  "provenance": {
    "tool": "codepax",
    "version": "0.1.0",
    "generated_at": "2026-01-18T16:00:00Z"
  },
  "instructions": {
    "usage": "Load layer_alice for the main persona; layer_hatter for alternate tone."
  },
  "sources": [
    {
      "id": "src_text_01",
      "uri": "https://www.gutenberg.org/files/11/11-0.txt",
      "type": "text/plain",
      "hash": "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
      "size_bytes": 152399,
      "content": null,
      "curation": {
        "exclusions": [{"start": 0, "end": 500, "reason": "header"}]
      }
    }
  ],
  "layers": [
    {
      "id": "layer_alice",
      "name": "Alice",
      "type": "persona",
      "system_prompt": "You are Alice. Curious, polite, occasionally bewildered.",
      "context_sources": ["src_text_01"],
      "parameters": {"temperature": 0.7}
    }
  ],
  "extensions": {
    "whetstone": {"visual_style": "woodcut"},
    "schema_embed": {
      "required": ["spec_version", "uuid", "meta", "sources", "layers"],
      "properties": {
        "meta": {"properties": {"state": {"enum": ["lite", "dense"]}}},
        "sources": {"items": {"properties": {"id": {"type": "string"}, "uri": {"type": ["string", "array"]}}}}
      }
    },
    "persona": {
      "$schema": "https://example.com/schemas/codex-persona.schema.json",
      "schema_embed": {
        "type": "object",
        "properties": {"primary_layer": {"type": "string"}},
        "required": ["primary_layer"]
      },
      "primary_layer": "layer_alice"
    }
  }
}

## Optional codex.zip Layout (Dense)

alice.codex.zip
├── codex.json          # same manifest, now meta.state="dense"; content inlined or external
└── content/
    └── src_text_01.txt # hydrated asset (hash/size match manifest)

All bootstrapping guidance stays inline; no separate files are required inside the zip.
