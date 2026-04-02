#!/usr/bin/env python3

from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

WIKIPEDIA_PAGE_BASE = "https://en.wikipedia.org/wiki/"
WIKISPECIES_PAGE_BASE = "https://species.wikimedia.org/wiki/"
USER_AGENT = "Codex Mesozoic Atlas/1.0"
REQUEST_PAUSE_SECONDS = 0.6
MAX_RETRIES = 5
FAMILY_PATTERN = re.compile(r"\b([A-Z][A-Za-z-]*idae)\b")
WIKIPEDIA_FAMILY_ROW_PATTERN = re.compile(
    r"(?:<th[^>]*>|<td[^>]*>)\s*Family(?:</a>)?:?\s*</(?:th|td)>\s*<td[^>]*>(.*?)</td>",
    re.IGNORECASE | re.DOTALL,
)
WIKISPECIES_FAMILY_ROW_PATTERN = re.compile(
    r"Familia:\s*(.*?)<br\s*/?>",
    re.IGNORECASE | re.DOTALL,
)
TAG_PATTERN = re.compile(r"<[^>]+>")
WHITESPACE_PATTERN = re.compile(r"\s+")


def fetch_text(url: str) -> tuple[str, str]:
    last_error = None
    for attempt in range(MAX_RETRIES):
        if attempt:
            time.sleep(min(8, 2**attempt))
        else:
            time.sleep(REQUEST_PAUSE_SECONDS)

        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                return response.read().decode("utf-8"), response.geturl()
        except urllib.error.HTTPError as error:
            last_error = error
            if error.code not in {429, 500, 502, 503, 504}:
                raise
        except urllib.error.URLError as error:
            last_error = error

    if last_error:
        raise last_error
    raise RuntimeError(f"Failed to fetch {url}")


def title_from_url(url: str) -> str:
    return clean_title(urllib.parse.unquote(url.rstrip("/").rsplit("/", 1)[-1]))


def fetch_page(base_url: str, title: str) -> dict | None:
    encoded_title = urllib.parse.quote(clean_title(title).replace(" ", "_"))
    url = f"{base_url}{encoded_title}"
    try:
        html, final_url = fetch_text(url)
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return None
        raise
    except urllib.error.URLError:
        return None

    return {
        "title": title_from_url(final_url),
        "pageUrl": final_url,
        "text": html,
    }


def extract_family_from_html(html: str) -> str | None:
    for pattern in (WIKIPEDIA_FAMILY_ROW_PATTERN, WIKISPECIES_FAMILY_ROW_PATTERN):
        row_match = pattern.search(html)
        if not row_match:
            continue

        cell_html = row_match.group(1)
        families = {
            match.group(1)
            for match in FAMILY_PATTERN.finditer(TAG_PATTERN.sub(" ", cell_html))
        }
        if len(families) == 1:
            return next(iter(families))
    return None


def clean_title(title: str) -> str:
    return WHITESPACE_PATTERN.sub(" ", title.replace("_", " ")).strip()


def load_json_if_exists(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def write_checkpoint(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def build_missing_family_enrichment(output_path: Path) -> dict:
    project_root = Path(__file__).resolve().parents[1]
    database_path = project_root / "data" / "dinosaur-database.json"
    database = json.loads(database_path.read_text(encoding="utf-8"))
    species = database["species"]
    missing = [item for item in species if not item.get("family")]

    genus_candidates: dict[str, list[str]] = {}
    for item in missing:
        genus_candidates.setdefault(item["genus"], []).append(item["scientificName"])

    existing = load_json_if_exists(output_path)
    wikipedia_cache: dict[str, dict | None] = {}
    wikispecies_cache: dict[str, dict | None] = {}
    genus_mappings: dict[str, dict] = dict(existing.get("byGenus") or {})
    species_mappings: dict[str, dict] = dict(existing.get("byScientificName") or {})
    unresolved_by_genus: dict[str, list[str]] = {}
    for record in existing.get("unresolved") or []:
        unresolved_by_genus.setdefault(record["genus"], []).append(record["scientificName"])

    processed_genera = set(genus_mappings)

    total_genera = len(genus_candidates)
    for index, (genus, scientific_names) in enumerate(sorted(genus_candidates.items()), start=1):
        if genus in processed_genera:
            continue
        if index == 1 or index % 25 == 0 or index == total_genera:
            print(f"Checking genus {index}/{total_genera}: {genus}", flush=True)
        candidates = [genus, *scientific_names]
        resolved = None

        for candidate in candidates:
            candidate_title = clean_title(candidate)
            for source_name, base_url, cache in (
                ("Wikipedia", WIKIPEDIA_PAGE_BASE, wikipedia_cache),
                ("Wikispecies", WIKISPECIES_PAGE_BASE, wikispecies_cache),
            ):
                if candidate_title not in cache:
                    cache[candidate_title] = fetch_page(base_url, candidate_title)
                parsed = cache[candidate_title]
                if not parsed:
                    continue

                family = extract_family_from_html(parsed.get("text", ""))
                if not family:
                    continue

                resolved = {
                    "family": family,
                    "pageTitle": parsed.get("title") or candidate_title,
                    "pageUrl": parsed.get("pageUrl")
                    or f"{base_url}{urllib.parse.quote((parsed.get('title') or candidate_title).replace(' ', '_'))}",
                    "matchedTitle": candidate_title,
                    "matchedLevel": "genus" if candidate_title == genus else "species",
                    "sourceSite": source_name,
                }
                break
            if resolved:
                break

        if resolved:
            genus_mappings[genus] = resolved
            unresolved_by_genus.pop(genus, None)
            for scientific_name in scientific_names:
                species_mappings[scientific_name] = resolved
        else:
            unresolved_by_genus[genus] = list(scientific_names)

        if index == 1 or index % 10 == 0 or index == total_genera:
            write_checkpoint(
                output_path,
                {
                    "generatedAt": datetime.now(timezone.utc).isoformat(),
                    "source": "Wikipedia and Wikispecies explicit family rows",
                    "speciesChecked": len(missing),
                    "recoveredSpeciesCount": len(species_mappings),
                    "recoveredGenusCount": len(genus_mappings),
                    "byScientificName": species_mappings,
                    "byGenus": genus_mappings,
                    "unresolved": [
                        {
                            "scientificName": scientific_name,
                            "genus": unresolved_genus,
                        }
                        for unresolved_genus, names in sorted(unresolved_by_genus.items())
                        for scientific_name in names
                    ],
                },
            )

    return {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "source": "Wikipedia and Wikispecies explicit family rows",
        "speciesChecked": len(missing),
        "recoveredSpeciesCount": len(species_mappings),
        "recoveredGenusCount": len(genus_mappings),
        "byScientificName": species_mappings,
        "byGenus": genus_mappings,
        "unresolved": [
            {
                "scientificName": scientific_name,
                "genus": unresolved_genus,
            }
            for unresolved_genus, names in sorted(unresolved_by_genus.items())
            for scientific_name in names
        ],
    }


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    output_path = project_root / "data" / "raw" / "wikipedia-family-enrichment.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    enrichment = build_missing_family_enrichment(output_path)
    write_checkpoint(output_path, enrichment)

    print(f"Recovered species: {enrichment['recoveredSpeciesCount']}", flush=True)
    print(f"Recovered genera: {enrichment['recoveredGenusCount']}", flush=True)
    print(f"Still unresolved: {len(enrichment['unresolved'])}", flush=True)


if __name__ == "__main__":
    main()
