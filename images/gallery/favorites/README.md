# Favorites Archive

- `current-favorites-2026-05-06.json`: latest favorites pulled from Chrome local storage on May 6, 2026.
- `current/`: the materialized files copied from the Instagram exports for that live favorites snapshot.
- `recovered-favorites.json`: the earlier recovered snapshot from the partially corrupted storage record.
- `recovered-*.{jpg,webp}`: files copied from that earlier recovered favorites set.

Use `scripts/materialize_insta_manifest.py` to turn any future exported favorites JSON into a real folder inside this repo.
