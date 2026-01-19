# CodePax CLI (v0.1 inline-first)

Lightweight CLI for the CODEX v0.1 inline-first spec: validate, hydrate, and dehydrate portable AI persona manifests.

## 🚀 Quickstart

```bash
# Install (local dev)


# Create a lite manifest
python tools/codepax.py init --name "Example Persona" --author "You" --out example.codex.json

# Hydrate (with externs or func:// if needed)
python tools/codepax.py hydrate example.codex.json --zip

# Dehydrate back to lite
python tools/codepax.py dehydrate example.codex.json --out example.lite.codex.json

# Validate
python tools/codepax.py validate example.codex.json
```

## Commands

- `init` – scaffold a lite manifest.
- `validate` – schema + hash/size checks (`--relaxed` to warn instead of fail).
- `hydrate` – fetch/inline sources, set `meta.state=dense`, optionally bundle `--zip` (supports `--externs` and `--functions` for extern resolvers and func:// via functiongemma).
- `dehydrate` – strip inline content, recompute hashes, set `meta.state=lite`.

## Features

- Inline-first CODEX v0.1: `.codex.json` canonical, optional `.codex.zip` transport.
- Integrity: every source carries `sha256` + `size_bytes`; strict vs relaxed validation.
- Extern resolvers: map custom schemes (e.g., `pg://123`) via `extensions.externs` or `--externs`.
- Function calling: hydrate `func://name?...` via functiongemma (default model `functiongemma-270m`) with specs from `extensions.functions` or `--functions`.

## Pointers

- Spec: [specs/CODEX_SPEC.md](specs/CODEX_SPEC.md)
- Schema: [tools/codex_v2_schema.json](tools/codex_v2_schema.json)
- Extern example: [tools/externs/project_gutenberg.json](tools/externs/project_gutenberg.json)
- Function examples: [tools/functions/functiongemma_examples.json](tools/functions/functiongemma_examples.json)

## License

MIT. Format text CC0 where noted in spec.
   

