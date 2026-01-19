# CODEX Format Specification v0.1

Manifest-first, inline-friendly cartridge for personas, annotations, and curated text. Lite JSON is canonical; `codex.zip` is optional compression of the same manifest plus hydrated assets. No separate bootstrap files are required inside the zip.

## Core Tenets
- One manifest (`codex.json`) is authoritative.
- Lite (content null) must be directly usable by LLMs/tools.
- Dense (content hydrated) is optional and typically shipped as `codex.zip` for space.
- Every source carries `sha256` + `size_bytes`; strict validation fails on drift.
- Unknown fields are ignored; extensions are namespaced under `extensions`.

## Required Structures (summary)
- `spec_version`: `0.1.x`
- `uuid`: RFC 4122
- `meta`: `name`, `version`, `state` (`lite`|`dense`), optional description/category/tags/author/created_by/created_at/archived_at
- `provenance` (opt): tool/version/generated_at/profile/logic(ai_model/prompts/parameters)
- `instructions` (opt): usage/system_prompt_hint/layer_logic/bootstrap_hint
- `sources[]`: id, uri, type(default text/plain), hash(`sha256:<hex64>`), size_bytes, content(null|string), encoding?, curation.exclusions?, notes?
- `layers[]`: id, name, type(`persona`|`analysis`|`visuals`), optional base_model_hint/recommended_models/system_prompt/context_sources/parameters/voice/tags
- `history[]` (opt): version/date/action/actor/notes
- `extensions` (opt): namespaced project data

## Lifecycle
- Lite → Hydrate: fetch URIs, verify `sha256`+`size_bytes`, inline content, set `meta.state="dense"`, optionally package manifest+assets into `codex.zip`.
- Dense → Dehydrate: recompute hashes/sizes, set content to null, set `meta.state="lite"`, optionally drop assets leaving the manifest.

## Schema
See tools/codex_v2_schema.json for the authoritative JSON Schema aligned to this draft.

## Example
A trimmed Lite example lives in specs/CODEX_SPEC.md under “Example (Lite, trimmed)”.
