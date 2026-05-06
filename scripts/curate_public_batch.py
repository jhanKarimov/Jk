#!/usr/bin/env python3
"""
Build a larger public-ready photo batch from the Instagram export.

This script selects one representative still image from many post blocks,
balances picks across requested years, copies the source assets into the repo,
and emits a manifest that can be merged into the site's public gallery.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
from collections import Counter
from html import unescape
from pathlib import Path

from bs4 import BeautifulSoup

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".heic"}
MUSIC_WORDS = {
    "techno",
    "industrial",
    "frisson",
    "show",
    "concert",
    "music",
    "dance",
    "club",
    "basement",
    "stage",
    "timidus",
    "timidusart",
    "synth",
    "darksynth",
    "dj",
}
TRAVEL_WORDS = {
    "warsaw",
    "ankara",
    "baku",
    "new york",
    "nyc",
    "boston",
    "beach",
    "sea",
    "boat",
    "memorial",
    "sunset",
    "trip",
    "travel",
}
LOVERS_WORDS = {
    "love",
    "lovers",
    "queen",
    "kiss",
    "desire",
    "aphrodite",
    "tiger",
    "together",
    "heart",
}
SOLITUDE_WORDS = {
    "alone",
    "lonely",
    "internal",
    "silence",
    "dream",
    "ghost",
    "dark",
    "solitude",
    "sad",
    "sorrow",
    "maze",
}


def clean_text(text: str) -> str:
    text = unescape(text or "")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def slugify(value: str) -> str:
    safe = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return safe or "archive-fragment"


def title_from_caption(caption: str, source: Path) -> str:
    caption = clean_text(caption)
    if caption:
        words = re.findall(r"[A-Za-z0-9']+", caption)[:4]
        if words:
            return " ".join(word.capitalize() for word in words)
    return source.stem.replace("-", " ").replace("_", " ").title()


def infer_category(caption: str) -> str:
    lowered = caption.lower()
    if any(word in lowered for word in MUSIC_WORDS):
        return "music"
    if any(word in lowered for word in TRAVEL_WORDS):
        return "travel"
    if "@" in caption or any(word in lowered for word in LOVERS_WORDS | SOLITUDE_WORDS):
        return "portrait"
    return "street"


def infer_moods(category: str, caption: str) -> list[str]:
    lowered = caption.lower()
    moods: list[str] = []
    if category == "music" or any(word in lowered for word in MUSIC_WORDS):
        moods.append("nightlife")
    if category == "travel" or any(word in lowered for word in TRAVEL_WORDS):
        moods.append("travel")
    if category == "street":
        moods.append("street")
    if category == "portrait" or any(word in lowered for word in SOLITUDE_WORDS):
        moods.append("solitude")
    if any(word in lowered for word in LOVERS_WORDS):
        moods.append("lovers")
    if not moods:
        moods.append("street")
    return list(dict.fromkeys(moods))


def short_caption(caption: str, limit: int = 180) -> str:
    caption = clean_text(caption)
    return caption if len(caption) <= limit else caption[: limit - 3].rstrip() + "..."


def parse_blocks(html_path: Path, source_root_name: str) -> list[dict]:
    soup = BeautifulSoup(html_path.read_text(), "html.parser")
    blocks: list[dict] = []
    for block in soup.select("div.pam._3-95._2ph-._a6-g.uiBoxWhite.noborder"):
        caption_el = block.select_one("h2._3-95._2pim._a6-h._a6-i")
        date_el = block.select_one("div._3-94._a6-o")
        caption = clean_text(caption_el.get_text(" ", strip=True) if caption_el else "")
        posted_at = clean_text(date_el.get_text(" ", strip=True) if date_el else "")
        year_match = re.search(r"(20\d{2})", posted_at)
        month_match = re.search(r"^[A-Za-z]{3} ([0-9]{1,2}), (20\d{2})", posted_at)
        month = ""
        if month_match:
            month_name = posted_at[:3].lower()
            month_map = {
                "jan": "01",
                "feb": "02",
                "mar": "03",
                "apr": "04",
                "may": "05",
                "jun": "06",
                "jul": "07",
                "aug": "08",
                "sep": "09",
                "oct": "10",
                "nov": "11",
                "dec": "12",
            }
            month = month_map.get(month_name, "")
        hrefs: list[str] = []
        for anchor in block.select("a[href]"):
            href = anchor["href"]
            if not href.startswith("media/"):
                continue
            if Path(href).suffix.lower() not in IMAGE_EXTS:
                continue
            if "/stories/" in href:
                continue
            hrefs.append(href)
        if not hrefs or not year_match:
            continue
        blocks.append(
            {
                "caption": caption,
                "postedAt": posted_at,
                "year": year_match.group(1),
                "month": month,
                "hrefs": hrefs,
                "sourceRoot": source_root_name,
            }
        )
    return blocks


def load_existing_sources(path: Path) -> set[str]:
    items = json.loads(path.read_text())
    return {item.get("source", "") for item in items if item.get("source")}


def build_batch(
    export_root: Path,
    dest: Path,
    existing_manifest: Path,
    quotas: dict[str, int],
) -> list[dict]:
    existing_sources = load_existing_sources(existing_manifest)
    parsed: list[dict] = []
    for html_name in ("posts_1.html", "archived_posts.html"):
        html_path = export_root / "your_instagram_activity" / "media" / html_name
        parsed.extend(parse_blocks(html_path, export_root.name))

    selected: list[dict] = []
    chosen_sources: set[str] = set()
    per_year: Counter[str] = Counter()
    dest.mkdir(parents=True, exist_ok=True)

    for year, quota in quotas.items():
        year_blocks = [block for block in parsed if block["year"] == year]
        for block in year_blocks:
            if per_year[year] >= quota:
                break
            rel_path = next(
                (
                    href
                    for href in block["hrefs"]
                    if f"{export_root.name}/{href}" not in existing_sources
                    and href not in chosen_sources
                ),
                None,
            )
            if not rel_path:
                continue

            source = export_root / rel_path
            if not source.exists():
                continue

            index = len(selected) + 1
            title = title_from_caption(block["caption"], source)
            category = infer_category(block["caption"])
            moods = infer_moods(category, block["caption"])
            stem = slugify(title)[:48]
            target = dest / f"batch-{index:03d}-{stem}{source.suffix.lower()}"
            shutil.copy2(source, target)
            selected.append(
                {
                    "id": f"public-batch-{index:03d}-{stem}",
                    "src": target.as_posix(),
                    "title": title,
                    "caption": block["caption"],
                    "category": category,
                    "year": block["year"],
                    "month": block["month"],
                    "postedAt": block["postedAt"],
                    "source": f"{export_root.name}/{rel_path}",
                    "featuredClassic": True,
                    "moods": moods,
                    "captionShort": short_caption(block["caption"]),
                }
            )
            per_year[year] += 1
            chosen_sources.add(rel_path)

    return selected


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--export-root", type=Path, required=True)
    parser.add_argument("--dest", type=Path, required=True)
    parser.add_argument("--existing-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    quotas = {"2019": 14, "2020": 22, "2021": 19}
    items = build_batch(args.export_root, args.dest, args.existing_manifest, quotas)
    args.output.write_text(json.dumps(items, indent=2))
    print(f"Created {len(items)} public batch item(s) at {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
