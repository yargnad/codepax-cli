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
    expected_digest = source.get("expected_digest")
    recorded_size = source.get("size_bytes")

    issues: List[str] = []
    if recorded_hash and recorded_hash != hash_val:
        issues.append(
            f"hash mismatch for {source.get('id', 'source')} (expected {recorded_hash}, got {hash_val})"
        )
    if expected_digest and expected_digest != hash_val:
        issues.append(
            f"expected_digest mismatch for {source.get('id', 'source')} (expected {expected_digest}, got {hash_val})"
        )
    if recorded_size and recorded_size != size_val:
        issues.append(
            f"size mismatch for {source.get('id', 'source')} (expected {recorded_size}, got {size_val})"
        )

    status = "clean" if not issues else "drifted"
    source["modification_status"] = status
    history_entry = {
        "checked_at": datetime.datetime.utcnow().isoformat() + "Z",
        "observed_digest": hash_val,
        "observed_size": size_val,
        "expected_hash": recorded_hash,
        "expected_digest": expected_digest,
        "status": status,
    }
    if issues:
        history_entry["notes"] = "; ".join(issues)
    source.setdefault("modification_history", []).append(history_entry)

    if issues:
        if strict:
            raise ValueError("; ".join(issues))
        for msg in issues:
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


def normalize_pg_id(raw_id: str) -> str:
    cleaned = raw_id.strip().strip("/")
    for prefix in ("ebooks/", "files/", "cache/epub/"):
        if cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix):]
            break
    cleaned = cleaned.replace("pg", "").replace("epub/", "")
    if cleaned.endswith(".txt"):
        cleaned = cleaned[:-4]
    if cleaned.endswith("-0"):
        cleaned = cleaned[:-2]
    digits = "".join(ch for ch in cleaned if ch.isdigit())
    return digits or cleaned


def resolve_external(uri: str, resolvers: Dict[str, Any]) -> Optional[Tuple[str, Dict[str, str], Optional[str]]]:
    parsed = urllib.parse.urlparse(uri)
    cfg = resolvers.get(parsed.scheme)
    if not cfg:
        return None

    identifier = (parsed.netloc + parsed.path).lstrip("/")
    if parsed.scheme == "pg":
        identifier = normalize_pg_id(identifier)
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


def validate_functions_map(functions: Dict[str, Any], strict: bool = True) -> bool:
    ok = True
    for name, spec in functions.items():
        if not isinstance(spec, dict):
            msg = f"function '{name}' must be an object"
            ok = False
            if strict:
                raise ValueError(msg)
            print(f"[warn] {msg}")
            continue

        if not spec.get("name") and not spec.get("id"):
            msg = f"function '{name}' missing required 'name' or 'id'"
            ok = False
            if strict:
                raise ValueError(msg)
            print(f"[warn] {msg}")

        encoding = spec.get("encoding")
        if encoding is not None and not isinstance(encoding, str):
            msg = f"function '{name}' encoding must be a string if provided"
            ok = False
            if strict:
                raise ValueError(msg)
            print(f"[warn] {msg}")

    return ok


def validate_exclusions(exclusions: Any, source_id: str, strict: bool = True) -> bool:
    if not isinstance(exclusions, list):
        return True
    ok = True
    last_end = -1
    for excl in sorted(exclusions, key=lambda x: x.get("start", 0)):
        start = excl.get("start")
        end = excl.get("end")
        if start is None or end is None:
            msg = f"source {source_id} exclusion missing start/end"
            ok = False
        elif start > end:
            msg = f"source {source_id} exclusion start>{end} (start={start}, end={end})"
            ok = False
        elif start <= last_end:
            msg = f"source {source_id} exclusions overlap at {start}-{end}"
            ok = False
        else:
            msg = None
        last_end = max(last_end, end if isinstance(end, int) else last_end)
        if msg:
            if strict:
                raise ValueError(msg)
            print(f"[warn] {msg}")
    return ok


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


def fetch_content_with_cache(
    uri: str,
    base_dir: Path,
    resolvers: Dict[str, Any],
    functions: Dict[str, Any],
    encoding: str = "utf-8",
    cache_dir: Optional[Path] = None,
) -> Tuple[bytes, str]:
    if cache_dir:
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_key = hashlib.sha256(uri.encode()).hexdigest()
        cache_path = cache_dir / f"{cache_key}.bin"
        if cache_path.exists():
            data = cache_path.read_bytes()
            return data, encoding

    data, enc = fetch_content(uri, base_dir, resolvers, functions, encoding=encoding)

    if cache_dir:
        cache_path.write_bytes(data)

    return data, enc


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

def _iter_uris(uri_field: Any) -> List[str]:
    if isinstance(uri_field, list):
        return [str(u) for u in uri_field]
    if isinstance(uri_field, str):
        return [uri_field]
    return []


def hydrate(
    manifest_path: Path,
    out_path: Optional[Path],
    bundle_zip: bool,
    strict: bool,
    externs_path: Optional[Path],
    functions_path: Optional[Path] = None,
    cache_dir: Optional[Path] = None,
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

    validate_functions_map(functions, strict=strict)

    for source in manifest.get("sources", []):
        content = source.get("content")
        encoding = source.get("encoding") or "utf-8"

        if content is None:
            uris = _iter_uris(source.get("uri"))
            if not uris:
                raise ValueError(f"source {source.get('id','?')} missing uri and content")
            payloads: List[bytes] = []
            for uri in uris:
                data, encoding = fetch_content_with_cache(
                    uri,
                    base_dir,
                    resolvers,
                    functions,
                    encoding=encoding,
                    cache_dir=cache_dir,
                )
                payloads.append(data)
            content_bytes = b"\n".join(payloads)
            source["content"] = content_bytes.decode(encoding, errors="replace")
        else:
            content_bytes = str(content).encode(encoding)

        curation = source.get("curation", {}) if isinstance(source.get("curation"), dict) else {}
        exclusions = curation.get("exclusions") if isinstance(curation, dict) else None
        validate_exclusions(exclusions, source.get("id", "source"), strict=strict)

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


def verify(
    manifest_path: Path,
    strict: bool,
    externs_path: Optional[Path],
    functions_path: Optional[Path],
    cache_dir: Optional[Path],
    out_path: Optional[Path],
) -> None:
    manifest, base_dir = read_manifest(manifest_path)
    ok = validate_manifest(manifest)

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

    try:
        validate_functions_map(functions, strict=strict)
    except ValueError as exc:
        print(f"[error] {exc}")
        ok = False

    for source in manifest.get("sources", []):
        encoding = source.get("encoding") or "utf-8"
        if source.get("content") is not None:
            content_bytes = str(source["content"]).encode(encoding)
        else:
            uris = _iter_uris(source.get("uri"))
            if not uris:
                print(f"[error] source {source.get('id','?')} missing uri and content")
                ok = False
                continue
            payloads: List[bytes] = []
            for uri in uris:
                try:
                    data, encoding = fetch_content_with_cache(
                        uri,
                        base_dir,
                        resolvers,
                        functions,
                        encoding=encoding,
                        cache_dir=cache_dir,
                    )
                    payloads.append(data)
                except Exception as exc:
                    print(f"[error] failed to fetch {uri}: {exc}")
                    ok = False
                    break
            if not payloads:
                continue
            content_bytes = b"\n".join(payloads)

        try:
            ensure_hash_and_size(source, content_bytes, strict=strict)
        except ValueError as exc:
            print(f"[error] {exc}")
            ok = False

        curation = source.get("curation", {}) if isinstance(source.get("curation"), dict) else {}
        exclusions = curation.get("exclusions") if isinstance(curation, dict) else None
        try:
            validate_exclusions(exclusions, source.get("id", "source"), strict=strict)
        except ValueError as exc:
            print(f"[error] {exc}")
            ok = False

    if ok:
        print("[ok] verification passed")
    else:
        print("[warn] verification encountered issues")

    if out_path:
        write_manifest(manifest, out_path)


# -------------------- Validation --------------------

def validate(manifest_path: Path, strict: bool) -> None:
    manifest, _ = read_manifest(manifest_path)
    ok = validate_manifest(manifest)

    manifest_functions = manifest.get("extensions", {}).get("functions", {}) if isinstance(manifest.get("extensions"), dict) else {}
    try:
        if isinstance(manifest_functions, dict):
            ok = validate_functions_map(manifest_functions, strict=strict) and ok
    except ValueError as exc:
        print(f"[error] {exc}")
        ok = False

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

        curation = source.get("curation", {}) if isinstance(source.get("curation"), dict) else {}
        exclusions = curation.get("exclusions") if isinstance(curation, dict) else None
        try:
            validate_exclusions(exclusions, source.get("id", "source"), strict=strict)
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
    p_hydrate.add_argument("--cache", help="Directory for cached fetches (optional)")

    p_dehydrate = sub.add_parser("dehydrate", help="Strip inline content to create lite manifest")
    p_dehydrate.add_argument("file", help="Path to dense codex.json or codex.zip")
    p_dehydrate.add_argument("--out", help="Output lite codex.json path")

    p_fetch = sub.add_parser("fetch", help="Fetch a CODEX artifact from a remote repo")
    p_fetch.add_argument("name", help="Package name without extension")
    p_fetch.add_argument("--repo", required=True, help="Remote alias from remotes mapping")
    p_fetch.add_argument("--remotes", help="Path to remotes JSON (alias -> base URL)")
    p_fetch.add_argument("--out", help="Output path (defaults to <name>.codex.json or .zip)")
    p_fetch.add_argument("--zip", action="store_true", help="Fetch codex.zip instead of codex.json")

    p_verify = sub.add_parser("verify", help="Fetch+verify sources without inlining content")
    p_verify.add_argument("file", help="Path to codex.json or codex.zip")
    p_verify.add_argument("--relaxed", action="store_true", help="Warn instead of failing on hash/size mismatch")
    p_verify.add_argument("--externs", help="Path to externs JSON describing external archive resolvers")
    p_verify.add_argument("--functions", help="Path to functions JSON (functiongemma-backed func:// resolvers)")
    p_verify.add_argument("--cache", help="Directory for cached fetches (optional)")
    p_verify.add_argument("--out", help="Write manifest with updated modification_history to this path")

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
            cache_dir=Path(args.cache) if getattr(args, "cache", None) else None,
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

    elif args.command == "verify":
        verify(
            manifest_path=Path(args.file),
            strict=not args.relaxed,
            externs_path=Path(args.externs) if args.externs else None,
            functions_path=Path(args.functions) if getattr(args, "functions", None) else None,
            cache_dir=Path(args.cache) if getattr(args, "cache", None) else None,
            out_path=Path(args.out) if args.out else None,
        )

    else:
        parser.print_help()


if __name__ == "__main__":  # pragma: no cover - CLI entry
    main()
