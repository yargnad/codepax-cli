# CodePax CLI

[![PyPI version](https://badge.fury.io/py/codepax-cli.svg)](https://badge.fury.io/py/codepax-cli)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

The reference CLI for [CODEX](specs/CODEX_SPEC.md) – portable AI personas and conversations.

**CODEX is a makefile for minds.** Distribute 5KB recipes. Hydrate full personas locally.

## 🚀 Quickstart

```bash
# Install
pip install codepax-cli

# Download example
curl -O https://raw.githubusercontent.com/yargnad/codepax-cli/main/examples/sherlock_holmes.codex-lite.json

# Hydrate to full offline persona
codepax hydrate sherlock_holmes.codex-lite.json

# Verify integrity
codepax verify sherlock_holmes.codex-dense/
```

## 📖 CODEX Format v1.0

- **[Overview](specs/CODEX_SPEC.md)** – Goals, tiers (Lite/Dense/Persona), platforms
- **[Lite v1.0](specs/CODEX_LITE_SPEC.md)** – Recipes (<100KB), hydration pipeline
- **[Dense v1.0](specs/CODEX_DENSE_SPEC.md)** – Offline personas (Whetstone)
- **[Persona v1.0](specs/CODEX_PERSONA_SPEC.md)** – Digital souls, consent, psychographics

## 🎯 Platforms Using CODEX

| Platform | CODEX Tier | Use Case |
|----------|------------|----------|
| [The Whetstone](https://github.com/yargnad/The-Whetstone) | Dense + Persona | Offline philosophy, digital soul export |
| Eidolon Triptych | Lite | Cloud fiction/roleplay, multi-character symposia |
| [The Crystalizer](https://github.com/yargnad/The-Crystalizer) | Lite + Dense | Conversation archiving → persona extraction |

## 🛡️ Security Philosophy

**Chatty by default. Never silent about risks.**

```
⚠️  MODIFICATION DETECTED!
   -  Derived from pristine recipe
   -  2 authorized changes by alice@example.com
   
   Continue hydration? [y/N]
```

- Source digests prevent tampering.
- Modifications require explicit consent.
- `--strict` fails on ANY issue.

## Commands

```bash
codepax hydrate sherlock.codex-lite.json      # Lite → Dense
codepax verify sherlock.codex-dense/          # Integrity check
codepax create-lite --name "Socrates" ...     # Build new recipe
codepax derive --change "temp=0.45" ...       # Create modified version
```

## Examples

```bash
# Strict mode (fail on issues)
codepax hydrate --strict holmes.codex-lite.json

# Paranoid verification
codepax verify --verify-all holmes.codex-dense/
```

## Installation

```bash
pip install codepax-cli
```

## License

MIT. Format is forever open. Build on it.

**Prior art established:** Specs published 2026-01-18 [v1.0-spec](https://github.com/yargnad/codepax-cli/releases/tag/v1.0-spec).

***

