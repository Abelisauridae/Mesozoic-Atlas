#!/usr/bin/env python3
"""Check completion of the 110-image Dinosaur Atlas family art set."""

from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
MANIFEST_PATH = ROOT / "family-image-manifest.csv"
IMAGE_DIR = ROOT / "final-family-art"
ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".svg"}


def load_manifest_ids(path: Path) -> list[str]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return [row["image_id"] for row in reader]


def discover_images(path: Path) -> dict[str, str]:
    found: dict[str, str] = {}
    if not path.exists():
        return found
    for file_path in sorted(path.iterdir()):
        if not file_path.is_file():
            continue
        if file_path.suffix.lower() not in ALLOWED_EXTENSIONS:
            continue
        found[file_path.stem] = file_path.name
    return found


def main() -> int:
    expected_ids = load_manifest_ids(MANIFEST_PATH)
    actual_files = discover_images(IMAGE_DIR)

    missing_ids = [image_id for image_id in expected_ids if image_id not in actual_files]
    extra_files = [name for stem, name in sorted(actual_files.items()) if stem not in expected_ids]

    payload = {
        "expectedCount": len(expected_ids),
        "completedCount": len(expected_ids) - len(missing_ids),
        "missingCount": len(missing_ids),
        "complete": not missing_ids,
        "missingImageIds": missing_ids,
        "extraFiles": extra_files,
        "imageDirectory": str(IMAGE_DIR),
        "manifestPath": str(MANIFEST_PATH),
    }

    print(json.dumps(payload, indent=2))
    return 0 if not missing_ids else 1


if __name__ == "__main__":
    raise SystemExit(main())
