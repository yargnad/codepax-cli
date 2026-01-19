# CODEX Format Specification v0.1 (Draft)

Unified, inline-first manifest for personas, annotations, and curated text. The canonical artifact is a single JSON file that AIs can parse directly; an optional `codex.zip` is only a compressed wrapper around the same manifest and any hydrated assets.

## Artifacts
 **Multi-source URIs:** `sources[*].uri` may be a string or array of URIs; hydrate/verify fetch each in order and join with newlines before hashing.

- Optional: `extensions.functions` as a map of function specs (must include `name`/`id`, optional `description`/`model`/`encoding`/`mode`/`parameters`/`notes`); validated before hydrating `func://` URIs.

## Integrity
- Every source must include `hash` = `sha256:<64 hex>` and `size_bytes`.
- Optional `expected_digest`, `modification_status` (`clean|drifted|unknown`), and `modification_history[]` can track observed checksums/sizes. Hydration/validation updates these and still fails in strict mode on mismatches.
- If `content` is present, it must match hash/size; if null, hydration must fetch and verify.
- Strict mode fails on any mismatch; relaxed mode may warn.
- `pg://` IDs are normalized to numeric Gutenberg IDs (strip pg/ebooks/cache prefixes and file suffixes) before resolution.

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
- Recommended `$schema`: `https://raw.githubusercontent.com/yargnad/codepax-cli/master/tools/codex_v2_schema.json` (include in every manifest so tools/LLMs can fetch the shape).
- Consumers must ignore unknown fields; use `extensions.<namespace>` for project data.

## License
Spec text: CC0 1.0 (Public Domain).
