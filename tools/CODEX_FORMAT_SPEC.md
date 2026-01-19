# CODEX Format Specification v0.1 (Draft)

Unified, inline-first manifest for personas, annotations, and curated text. The canonical artifact is a single JSON file that AIs can parse directly; an optional `codex.zip` is only a compressed wrapper around the same manifest and any hydrated assets.

## Artifacts
- **Lite (canonical):** `.codex.json` — manifest with `content` null/absent; always usable inline.
- **Dense (optional transport):** `codex.zip` — same manifest plus hydrated assets under `content/`; no extra bootstrap files.

## Manifest Essentials (codex.json)
- `spec_version`: `0.1.x`
- `uuid`: RFC 4122
- `meta`: `name`, `version`, `state` (`lite`|`dense`), optional `description`, `category`, `tags`, `author`, `created_by`, `created_at`, `archived_at`
- `provenance` (opt): `tool`, `version`, `generated_at`, `profile`, `logic` (`ai_model`, `prompts`, `parameters`)
- `instructions` (opt): `usage`, `system_prompt_hint`, `layer_logic`, `bootstrap_hint` (all inline)
- `sources[]`: `id`, `uri`, `type` (default `text/plain`), `hash` (`sha256:<hex64>`), `size_bytes`, `content` (null|string), optional `encoding`, `curation.exclusions[] {start,end,reason,...}`, `notes`
- `layers[]`: `id`, `name`, `type` (`persona`|`analysis`|`visuals`), optional `system_prompt`, `context_sources`, `parameters`, `voice`, `tags`, `base_model_hint`, `recommended_models`
- Optional: `history[]` (version/date/action/actor/notes), `extensions` (namespaced project data)

## Integrity
- Every source must include `hash` = `sha256:<64 hex>` and `size_bytes`.
- If `content` is present, it must match hash/size; if null, hydration must fetch and verify.
- Strict mode fails on any mismatch; relaxed mode may warn.

## Lifecycle
- **Lite → Hydrate:** fetch URIs, verify `sha256`+`size_bytes`, inline `content`, set `meta.state="dense"`, optionally bundle manifest+assets into `codex.zip`.
- **Dense → Dehydrate:** recompute hash/size, set `content` to null, set `meta.state="lite"`, optionally drop assets leaving only the manifest.

## Optional `codex.zip` Layout (Dense Transport)
```
example.codex.zip
├── codex.json          # manifest (meta.state="dense" when hydrated)
└── content/
    └── src_text_01.txt # hydrated asset, hash/size match manifest
```
All bootstrapping guidance stays inline in the manifest.

## Use Cases
- Persona portability (multiple layers/views over shared sources)
- Research notebooks with exclusions/annotations/filters
- Teaching/study guides with layered material for exams/labs

## Naming
- Lite: `{slug}.codex.json`
- Dense: `{slug}.codex.zip`

## Validation & Schema
- Authoritative JSON Schema: [codex_v2_schema.json](./codex_v2_schema.json)
- Consumers must ignore unknown fields; use `extensions.<namespace>` for project data.

## License
Spec text: CC0 1.0 (Public Domain).
