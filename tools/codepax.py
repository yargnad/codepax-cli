"""
CodePax CLI (v0.1 draft)
Inline-first CODEX manager for creating, validating, hydrating, and dehydrating manifests.
"""
import argparse
import datetime
import hashlib
import json
import sys
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import jsonschema
import requests

try:  # Optional function calling support
    import functiongemma  # type: ignore
except ImportError:  # pragma: no cover - optional dependency
    functiongemma = None

VERSION = "0.1.0"
SCHEMA_PATH = Path(__file__).parent / "codex_v2_schema.json"


# -------------------- Schema Handling --------------------

def load_schema() -> Optional[Dict[str, Any]]:
    try:
        with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:  # pragma: no cover - defensive
        print(f"[warn] Could not load schema {SCHEMA_PATH}: {exc}")
        return None


CODEX_SCHEMA = load_schema()


def validate_manifest(manifest: Dict[str, Any]) -> bool:
    """Validate manifest against the v0.1 schema."""
    if CODEX_SCHEMA is None:
        print("[warn] Schema not loaded; skipping JSON Schema validation")
        return True
    try:
        jsonschema.validate(instance=manifest, schema=CODEX_SCHEMA)
        return True
    except jsonschema.exceptions.ValidationError as exc:
        print(f"[error] Schema validation failed: {exc.message}")
        return False


# -------------------- Helpers --------------------

def compute_sha256_and_size(content_bytes: bytes) -> Tuple[str, int]:
    digest = hashlib.sha256()
    digest.update(content_bytes)
    return f"sha256:{digest.hexdigest()}", len(content_bytes)


def ensure_hash_and_size(source: Dict[str, Any], content_bytes: bytes, strict: bool = True) -> None:
    hash_val, size_val = compute_sha256_and_size(content_bytes)
    recorded_hash = source.get("hash")
    recorded_size = source.get("size_bytes")

    if recorded_hash and recorded_hash != hash_val:
        msg = f"hash mismatch for {source.get('id', 'source')} (expected {recorded_hash}, got {hash_val})"
        if strict:
            raise ValueError(msg)
        print(f"[warn] {msg}")
    if recorded_size and recorded_size != size_val:
        msg = f"size mismatch for {source.get('id', 'source')} (expected {recorded_size}, got {size_val})"
        if strict:
            raise ValueError(msg)
        print(f"[warn] {msg}")

    source["hash"] = recorded_hash or hash_val
    source["size_bytes"] = recorded_size or size_val


def write_manifest(manifest: Dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    print(f"[ok] wrote {path}")


def read_manifest(manifest_path: Path) -> Tuple[Dict[str, Any], Path]:
    if manifest_path.suffix == ".zip":
        with zipfile.ZipFile(manifest_path, "r") as zf:
            with zf.open("codex.json") as f:
                manifest = json.load(f)
        base_dir = Path(".")
    else:
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
        base_dir = manifest_path.parent
    return manifest, base_dir


def load_externs(path: Optional[Path]) -> Dict[str, Any]:
    if not path:
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except Exception as exc:  # pragma: no cover - defensive
        print(f"[warn] Failed to load externs from {path}: {exc}")
        return {}


def load_remotes(path: Optional[Path]) -> Dict[str, str]:
    if not path:
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, dict):
                raise ValueError("remotes file must map alias -> base_url")
            return {k: str(v) for k, v in data.items()}
    except Exception as exc:  # pragma: no cover - defensive
        print(f"[warn] Failed to load remotes from {path}: {exc}")
        return {}


def resolve_external(uri: str, resolvers: Dict[str, Any]) -> Optional[Tuple[str, Dict[str, str], Optional[str]]]:
    parsed = urllib.parse.urlparse(uri)
    cfg = resolvers.get(parsed.scheme)
    if not cfg:
        return None

    identifier = (parsed.netloc + parsed.path).lstrip("/")
    template = cfg.get("template")
    if not template:
        return None

    target_uri = template.format(id=identifier)
    headers = cfg.get("headers", {}) if isinstance(cfg.get("headers"), dict) else {}
    encoding = cfg.get("encoding")
    return target_uri, headers, encoding


def load_functions(path: Optional[Path]) -> Dict[str, Any]:
    if not path:
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except Exception as exc:  # pragma: no cover - defensive
        print(f"[warn] Failed to load functions from {path}: {exc}")
        return {}


def resolve_function(uri: str, functions: Dict[str, Any]) -> Optional[Tuple[Dict[str, Any], Dict[str, str]]]:
    parsed = urllib.parse.urlparse(uri)
    if parsed.scheme != "func":
        return None
    name = parsed.netloc or parsed.path.lstrip("/")
    spec = functions.get(name)
    if not spec:
        raise ValueError(f"function '{name}' not found in provided functions map")
    params = dict(urllib.parse.parse_qsl(parsed.query))
    return spec, params


def call_functiongemma(spec: Dict[str, Any], params: Dict[str, str], encoding: str) -> Tuple[bytes, str]:
    if functiongemma is None:
        raise RuntimeError("functiongemma package not installed; pip install functiongemma to enable func:// sources")
    model = spec.get("model", "functiongemma-270m")
    fn_name = spec.get("name") or spec.get("id") or "fn"

    # Best-effort generic invocation; adjust if your functiongemma client differs.
    try:
        client = functiongemma.Client(model=model)  # type: ignore[attr-defined]
    except Exception as exc:
        raise RuntimeError(f"failed to init functiongemma client: {exc}")

    try:
        if hasattr(client, "call"):
            result = client.call(fn_name, params)  # type: ignore[arg-type]
        elif hasattr(client, "invoke"):
            result = client.invoke(fn_name, params)  # type: ignore[arg-type]
        else:
            raise RuntimeError("functiongemma client missing call/invoke; adjust integration")
    except Exception as exc:
        raise RuntimeError(f"functiongemma call failed: {exc}")

    if isinstance(result, dict):
        content = result.get("content") or result.get("text") or json.dumps(result)
    else:
        content = str(result)
    return str(content).encode(encoding), encoding


def fetch_content(uri: str, base_dir: Path, resolvers: Dict[str, Any], functions: Dict[str, Any], encoding: str = "utf-8") -> Tuple[bytes, str]:
    fn_resolved = resolve_function(uri, functions)
    if fn_resolved:
        spec, params = fn_resolved
        return call_functiongemma(spec, params, encoding)

    external = resolve_external(uri, resolvers)
    if external:
        target_uri, headers, override_encoding = external
        req = urllib.request.Request(target_uri, headers=headers)
        with urllib.request.urlopen(req) as resp:  # nosec - caller controls URI
            data = resp.read()
        return data, override_encoding or encoding

    if uri.startswith("file://"):
        file_path = Path(uri.replace("file://", ""))
        return file_path.read_bytes(), encoding
    if uri.startswith("http://") or uri.startswith("https://"):
        with urllib.request.urlopen(uri) as resp:  # nosec - caller controls URI
            return resp.read(), encoding
    # Treat as relative/local path
    file_path = (base_dir / uri).resolve()
    return file_path.read_bytes(), encoding


# -------------------- Manifest creation --------------------

def create_manifest(name: str, author: str, category: str) -> Dict[str, Any]:
    now = datetime.datetime.utcnow().isoformat() + "Z"
    return {
        "spec_version": VERSION,
        "uuid": str(__import__("uuid").uuid4()),
        "meta": {
            "name": name,
            "author": author or "Unknown",
            "category": category or "general",
            "version": VERSION,
            "state": "lite",
            "created_by": f"codepax-cli {VERSION}",
            "created_at": now,
        },
        "provenance": {
            "tool": "codepax",
            "version": VERSION,
            "generated_at": now,
            "profile": "default",
            "logic": {},
        },
        "instructions": {
            "usage": f"This cartridge represents '{name}'.",
            "system_prompt_hint": "",
            "layer_logic": "",
        },
        "sources": [],
        "layers": [],
        "history": [],
        "extensions": {},
    }


# -------------------- Hydration / Dehydration --------------------

def hydrate(
    manifest_path: Path,
    out_path: Optional[Path],
    bundle_zip: bool,
    strict: bool,
    externs_path: Optional[Path],
    functions_path: Optional[Path] = None,
) -> None:
    manifest, base_dir = read_manifest(manifest_path)
    if not validate_manifest(manifest):
        sys.exit(1)

    resolvers = {}
    manifest_resolvers = manifest.get("extensions", {}).get("externs", {}) if isinstance(manifest.get("extensions"), dict) else {}
    if isinstance(manifest_resolvers, dict):
        resolvers.update(manifest_resolvers)
    file_resolvers = load_externs(externs_path)
    resolvers.update(file_resolvers)

    functions: Dict[str, Any] = {}
    manifest_functions = manifest.get("extensions", {}).get("functions", {}) if isinstance(manifest.get("extensions"), dict) else {}
    if isinstance(manifest_functions, dict):
        functions.update(manifest_functions)
    cli_functions = load_functions(functions_path)
    functions.update(cli_functions)

    for source in manifest.get("sources", []):
        content = source.get("content")
        encoding = source.get("encoding") or "utf-8"

        if content is None:
            uri = source.get("uri")
            if not uri:
                raise ValueError(f"source {source.get('id','?')} missing uri and content")
            content_bytes, encoding = fetch_content(uri, base_dir, resolvers, functions, encoding=encoding)
            source["content"] = content_bytes.decode(encoding, errors="replace")
        else:
            content_bytes = str(content).encode(encoding)

        ensure_hash_and_size(source, content_bytes, strict=strict)

    manifest.setdefault("meta", {})["state"] = "dense"

    if bundle_zip:
        final_out = out_path or manifest_path.with_suffix(".codex.zip")
        with zipfile.ZipFile(final_out, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("codex.json", json.dumps(manifest, indent=2))
            for source in manifest.get("sources", []):
                content = source.get("content")
                if content is None:
                    continue
                src_id = source.get("id", "source")
                suffix = Path(source.get("uri", "")).suffix or ".txt"
                zf.writestr(f"content/{src_id}{suffix}", content)
        print(f"[ok] bundled dense cartridge -> {final_out}")
    else:
        final_out = out_path or manifest_path.with_name(f"{manifest_path.stem}.dense.codex.json")
        write_manifest(manifest, final_out)


def dehydrate(input_path: Path, out_path: Optional[Path]) -> None:
    manifest, _ = read_manifest(input_path)

    for source in manifest.get("sources", []):
        content = source.get("content")
        if content is None:
            continue
        encoding = source.get("encoding") or "utf-8"
        content_bytes = str(content).encode(encoding)
        ensure_hash_and_size(source, content_bytes, strict=False)
        source["content"] = None

    manifest.setdefault("meta", {})["state"] = "lite"
    final_out = out_path or input_path.with_name(f"{input_path.stem}.codex.json")
    write_manifest(manifest, final_out)


# -------------------- Validation --------------------

def validate(manifest_path: Path, strict: bool) -> None:
    manifest, _ = read_manifest(manifest_path)
    ok = validate_manifest(manifest)

    for source in manifest.get("sources", []):
        content = source.get("content")
        if content is None:
            continue
        encoding = source.get("encoding") or "utf-8"
        try:
            ensure_hash_and_size(source, str(content).encode(encoding), strict=strict)
        except ValueError as exc:
            print(f"[error] {exc}")
            ok = False

    if ok:
        print("[ok] manifest is valid")
    else:
        sys.exit(1)


# -------------------- Remote Fetch --------------------

def fetch_codex(package: str, repo: str, remotes_path: Optional[Path], out_path: Optional[Path], fetch_zip: bool) -> None:
    remotes = load_remotes(remotes_path)
    if repo not in remotes:
        raise ValueError(f"repo alias '{repo}' not found in remotes mapping")
    base = remotes[repo].rstrip("/")
    ext = ".codex.zip" if fetch_zip else ".codex.json"
    url = f"{base}/{package}{ext}"

    print(f"[info] fetching {url}...")
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()

    target = out_path or Path(f"{package}{ext}")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(resp.content)
    print(f"[ok] wrote {target}")


# -------------------- CLI --------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="CodePax CLI v0.1 (CODEX inline-first)")
    sub = parser.add_subparsers(dest="command")

    p_init = sub.add_parser("init", help="Create a new lite manifest")
    p_init.add_argument("--name", required=True)
    p_init.add_argument("--author", default="Unknown")
    p_init.add_argument("--category", default="general")
    p_init.add_argument("--out", default="codex.json")

    p_validate = sub.add_parser("validate", help="Validate a manifest against schema and hashes")
    p_validate.add_argument("file", help="Path to codex.json or codex.zip")
    p_validate.add_argument("--relaxed", action="store_true", help="Warn instead of failing on hash/size mismatch")

    p_hydrate = sub.add_parser("hydrate", help="Hydrate sources into manifest (optionally bundle codex.zip)")
    p_hydrate.add_argument("file", help="Path to lite codex.json or codex.zip")
    p_hydrate.add_argument("--out", help="Output path (json or zip)")
    p_hydrate.add_argument("--zip", action="store_true", help="Bundle hydrated cartridge as codex.zip")
    p_hydrate.add_argument("--relaxed", action="store_true", help="Warn instead of failing on hash/size mismatch")
    p_hydrate.add_argument("--externs", help="Path to externs JSON describing external archive resolvers")
    p_hydrate.add_argument("--functions", help="Path to functions JSON (functiongemma-backed func:// resolvers)")

    p_dehydrate = sub.add_parser("dehydrate", help="Strip inline content to create lite manifest")
    p_dehydrate.add_argument("file", help="Path to dense codex.json or codex.zip")
    p_dehydrate.add_argument("--out", help="Output lite codex.json path")

    p_fetch = sub.add_parser("fetch", help="Fetch a CODEX artifact from a remote repo")
    p_fetch.add_argument("name", help="Package name without extension")
    p_fetch.add_argument("--repo", required=True, help="Remote alias from remotes mapping")
    p_fetch.add_argument("--remotes", help="Path to remotes JSON (alias -> base URL)")
    p_fetch.add_argument("--out", help="Output path (defaults to <name>.codex.json or .zip)")
    p_fetch.add_argument("--zip", action="store_true", help="Fetch codex.zip instead of codex.json")

    return parser


def main(argv: Optional[List[str]] = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "init":
        manifest = create_manifest(args.name, args.author, args.category)
        write_manifest(manifest, Path(args.out))

    elif args.command == "validate":
        validate(Path(args.file), strict=not args.relaxed)

    elif args.command == "hydrate":
        hydrate(
            Path(args.file),
            Path(args.out) if args.out else None,
            bundle_zip=args.zip,
            strict=not args.relaxed,
            externs_path=Path(args.externs) if args.externs else None,
            functions_path=Path(args.functions) if getattr(args, "functions", None) else None,
        )

    elif args.command == "dehydrate":
        dehydrate(Path(args.file), Path(args.out) if args.out else None)

    elif args.command == "fetch":
        fetch_codex(
            package=args.name,
            repo=args.repo,
            remotes_path=Path(args.remotes) if args.remotes else None,
            out_path=Path(args.out) if args.out else None,
            fetch_zip=bool(getattr(args, "zip", False)),
        )

    else:
        parser.print_help()


if __name__ == "__main__":  # pragma: no cover - CLI entry
    main()
