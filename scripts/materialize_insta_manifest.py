#!/usr/bin/env python3
"""
Copy Instagram favorites from an exported viewer manifest into a real folder.

Example:
  python3 scripts/materialize_insta_manifest.py \
    --manifest /path/to/insta-favorites-12.json \
    --exports-root /Users/jhankarimov/Downloads/photos-insta \
    --dest /Users/jhankarimov/Documents/NEWSFEED/JK/images/gallery/favorites
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


def load_manifest(path: Path) -> list[dict]:
    payload = json.loads(path.read_text())
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict) and isinstance(payload.get("favorites"), list):
        return payload["favorites"]
    raise ValueError("Manifest must be a JSON array or an object with a favorites array.")


def candidate_sources(exports_root: Path, item: dict) -> list[Path]:
    rel_path = item.get("relPath") or item.get("id")
    if not rel_path:
        return []

    candidates: list[Path] = []
    archive_hint = item.get("archiveHint")
    if archive_hint:
        candidates.append(exports_root / archive_hint / rel_path)

    matches = sorted(exports_root.glob(f"*/{rel_path}"))
    candidates.extend(matches)
    return candidates


def slug_name(index: int, item: dict, source: Path) -> str:
    ext = source.suffix.lower()
    filename = item.get("filename") or source.name
    stem = Path(filename).stem[:80]
    safe = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in stem).strip("-") or f"favorite-{index:03d}"
    return f"{index:03d}-{safe}{ext}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--exports-root", required=True, type=Path)
    parser.add_argument("--dest", required=True, type=Path)
    parser.add_argument("--no-prefix", action="store_true", help="Keep original filenames instead of prefixing them.")
    args = parser.parse_args()

    items = load_manifest(args.manifest)
    args.dest.mkdir(parents=True, exist_ok=True)

    copied: list[dict] = []
    missing: list[dict] = []

    for index, item in enumerate(items, start=1):
        source = next((path for path in candidate_sources(args.exports_root, item) if path.exists()), None)
        if source is None:
            missing.append(item)
            continue

        target_name = source.name if args.no_prefix else slug_name(index, item, source)
        target = args.dest / target_name
        shutil.copy2(source, target)
        copied.append(
            {
                "index": index,
                "filename": target.name,
                "source": str(source),
                "relPath": item.get("relPath") or item.get("id"),
                "archiveHint": item.get("archiveHint"),
                "type": item.get("type"),
                "year": item.get("year"),
                "month": item.get("month"),
            }
        )

    summary = {
        "manifest": str(args.manifest),
        "exportsRoot": str(args.exports_root),
        "dest": str(args.dest),
        "copied": copied,
        "missing": missing,
    }
    (args.dest / "materialized-summary.json").write_text(json.dumps(summary, indent=2))

    print(f"Copied {len(copied)} file(s) into {args.dest}")
    if missing:
        print(f"Missing {len(missing)} file(s). See materialized-summary.json for details.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
