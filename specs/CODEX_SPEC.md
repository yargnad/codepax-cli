# CODEX Specification v1.0

## Overview

CODEX is a self-describing container format for AI personas and conversations. A `.codex` file is a **makefile for minds** – deterministic instructions to build reproducible intelligence from public sources.

### Tiers

| Tier | Size | Contents | Use Case |
|------|------|----------|----------|
| **Lite** | <100KB | Recipe (sources + behavior) | Distribution (Triptych) |
| **Dense** | 10MB-1GB | Hydrated persona (vectors + manifest) | Offline (Whetstone) |
| **Persona** | Varies | Digital soul (assessment + provenance) | Export/sharing |

### Security Model

**Immutable by default. Explicitly mutable.**

- **Source digests** verify content integrity.  
- **Modification history** tracks every change.  
- **Chatty CLI** always warns about issues.  
- `--strict` fails on ANY anomaly.

```
⚠️  Source drift detected! Continue? [y/N]
```

## Design Principles

1. **Determinism:** Same CODEX → same persona.  
2. **Portability:** Works across models/platforms.  
3. **Legality:** Pointers, not copyrighted bulk text.  
4. **Transparency:** Provenance + consent mandatory.  
5. **Safety:** Chatty defaults prevent silent risks.

## Platforms

- **The Whetstone:** Dense/Persona (offline philosophy appliance).  
- **Eidolon Triptych:** Lite (cloud fiction/roleplay).  
- **Persona Foundry:** Persona creation wizards.

## Detailed Specs

- [Lite v1.0](CODEX_LITE_SPEC.md)
- [Dense v1.0](CODEX_DENSE_SPEC.md)  
- [Persona v1.0](CODEX_PERSONA_SPEC.md)

**Published:** 2026-01-18 (prior art established).
```

***

## 3. `specs/CODEX_LITE_SPEC.md` (Ready to expand)

```markdown
# CODEX Lite v1.0

Small JSON recipes (<100KB) that hydrate into full personas.

## Schema

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "required": ["meta", "behavior", "sources"],
  "properties": {
    "meta": { "$ref": "#/definitions/meta" },
    "behavior": { "$ref": "#/definitions/behavior" },
    "constraints": { "$ref": "#/definitions/constraints" },
    "sources": { "$ref": "#/definitions/sources" }
  }
}
```

## Security & Immutability

**Sources MUST include `expected_digest`:**

```json
{
  "sources": [{
    "type": "gutenberg",
    "id": "1661",
    "expected_digest": {
      "sha256": "e3b0c442...",
      "size_bytes": 512347
    }
  }]
}
```

**CLI validates before hydration:**

```
✅ Digest matches ✓
⚠️  Modified recipe! Continue? [y/N]
```

## Hydration Pipeline

1. **Parse** recipe.  
2. **Verify** source digests.  
3. **Fetch** (respect robots.txt, rate limits).  
4. **Sanitize** (exclusion_regex, processing_rules).  
5. **Chunk/embed** → Dense output.  

**Deterministic:** Same inputs → same chunks → same vectors.

## Example

[examples/sherlock_holmes.codex-lite.json](https://github.com/yargnad/codepax-cli/blob/main/examples/sherlock_holmes.codex-lite.json)
```
