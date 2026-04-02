#!/usr/bin/env python3

from __future__ import annotations

import csv
import io
import json
import re
import subprocess
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from urllib.parse import quote

WORLD_DINO_URL = "https://zenodo.org/records/10951509/files/dino.csv?download=1"
WORLD_LAND_URL = (
    "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/"
    "ne_110m_land.geojson"
)
FALLBACK_IMAGE_BASE = "images/fallbacks"
MESOZOIC_END_MA = 66.0

ATLAS_SOURCE_SPECS = [
    {
        "slug": "dinosaurs",
        "base_name": "Dinosauria^Aves",
        "atlas_group": "Dinosaur",
        "lineage": None,
        "requires_mesozoic_filter": True,
    },
    {
        "slug": "pterosaurs",
        "base_name": "Pterosauria",
        "atlas_group": "Pterosaur",
        "lineage": "Pterosauria",
        "requires_mesozoic_filter": False,
    },
    {
        "slug": "ichthyosaurs",
        "base_name": "Ichthyosauria",
        "atlas_group": "Marine reptile",
        "lineage": "Ichthyosauria",
        "requires_mesozoic_filter": False,
    },
    {
        "slug": "plesiosaurs",
        "base_name": "Plesiosauria",
        "atlas_group": "Marine reptile",
        "lineage": "Plesiosauria",
        "requires_mesozoic_filter": False,
    },
    {
        "slug": "mosasaurs",
        "base_name": "Mosasauroidea",
        "atlas_group": "Marine reptile",
        "lineage": "Mosasauroidea",
        "requires_mesozoic_filter": False,
    },
    {
        "slug": "crocodyliforms",
        "base_name": "Crocodyliformes",
        "atlas_group": "Crocodyliform",
        "lineage": "Crocodyliformes",
        "requires_mesozoic_filter": True,
    },
    {
        "slug": "turtles",
        "base_name": "Testudines",
        "atlas_group": "Turtle",
        "lineage": "Testudines",
        "requires_mesozoic_filter": True,
    },
]

MISSING_TAXA = {
    "",
    "NO_CLASS_SPECIFIED",
    "NO_ORDER_SPECIFIED",
    "NO_FAMILY_SPECIFIED",
    "NO_GENUS_SPECIFIED",
}
TRIASSIC_START_MA = 252.17
JURASSIC_START_MA = 201.36
CRETACEOUS_START_MA = 145.0
TRIASSIC_INTERVAL_KEYS = {
    "early triassic",
    "middle triassic",
    "late triassic",
    "induan",
    "olenekian",
    "anisian",
    "ladinian",
    "carnian",
    "norian",
    "rhaetian",
}
JURASSIC_INTERVAL_KEYS = {
    "early jurassic",
    "middle jurassic",
    "late jurassic",
    "hettangian",
    "sinemurian",
    "pliensbachian",
    "toarcian",
    "aalenian",
    "bajocian",
    "bathonian",
    "callovian",
    "oxfordian",
    "kimmeridgian",
    "tithonian",
}
CRETACEOUS_INTERVAL_KEYS = {
    "early cretaceous",
    "late cretaceous",
    "berriasian",
    "valanginian",
    "hauterivian",
    "barremian",
    "aptian",
    "albian",
    "cenomanian",
    "turonian",
    "coniacian",
    "santonian",
    "campanian",
    "maastrichtian",
}

CURATED_SPECIES_OVERRIDES = {
    "Cryolophosaurus ellioti": {
        "order": "Theropoda",
        "classificationNote": (
            "Family placement remains unresolved in the source taxonomy. "
            "The atlas keeps Cryolophosaurus outside a named family and instead "
            "surfaces it as an early theropod close to Averostra in recent "
            "phylogenetic discussions."
        ),
    },
}


def build_pbdb_taxa_url(base_name: str) -> str:
    return (
        "https://paleobiodb.org/data1.2/taxa/list.csv"
        f"?base_name={quote(base_name, safe='')}&rank=species&show=app,parent,size,class&limit=all"
    )


def build_pbdb_occurrences_url(base_name: str) -> str:
    return (
        "https://paleobiodb.org/data1.2/occs/list.csv"
        f"?base_name={quote(base_name, safe='')}&taxon_reso=species&show=coords,class,time&limit=all"
    )


def fetch_text(url: str) -> str:
    result = subprocess.run(
        ["curl", "-Lsf", url],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Failed to fetch {url}: {result.stderr.strip()}")
    return result.stdout


def load_source_text(cache_path: Path, url: str) -> str:
    if cache_path.exists():
        return cache_path.read_text(encoding="utf-8")
    text = fetch_text(url)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(text, encoding="utf-8")
    return text


def parse_csv(text: str) -> list[dict[str, str]]:
    return list(csv.DictReader(io.StringIO(text, newline="")))


def load_json_if_exists(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def strip_accents(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def normalize_lookup(value: str | None) -> str:
    if not value:
        return ""
    cleaned = strip_accents(value)
    return re.sub(r"[^a-z0-9]+", "", cleaned.lower())


def clean_taxon(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    if cleaned in MISSING_TAXA:
        return None
    return cleaned or None


def clean_interval(value: str | None) -> str | None:
    value = (value or "").strip()
    return value or None


def parse_float(value: str | None) -> float | None:
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def parse_length_m(value: str | None) -> float | None:
    if not value:
        return None
    match = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*m", value.lower())
    if not match:
        return None
    return round(float(match.group(1)), 2)


def parse_weight_kg(value: str | None) -> float | None:
    if not value:
        return None
    match = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*kg", value.lower())
    if not match:
        return None
    return round(float(match.group(1)), 2)


def clean_whitespace(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = re.sub(r"\s+", " ", value).strip()
    return cleaned or None


def dedupe_leading_token(text: str) -> str:
    return re.sub(r"^\s*([A-Z][A-Za-z-]+)\s+\1\b", r"\1", text)


def clean_comment_text(value: str | None) -> str | None:
    cleaned = clean_whitespace(value)
    if not cleaned:
        return None
    cleaned = dedupe_leading_token(cleaned)
    cleaned = re.sub(r"\s+([,.;:!?])", r"\1", cleaned)
    return cleaned


def extract_comment_excerpt(value: str | None, max_sentences: int = 2, max_chars: int = 280) -> str | None:
    cleaned = clean_comment_text(value)
    if not cleaned:
        return None
    parts = re.split(r"(?<=[.!?])\s+", cleaned)
    excerpt = " ".join(part.strip() for part in parts[:max_sentences] if part.strip()).strip()
    if not excerpt:
        return None
    if len(excerpt) > max_chars:
        excerpt = excerpt[: max_chars - 1].rsplit(" ", 1)[0].rstrip(",;:-")
        excerpt = f"{excerpt}..."
    return excerpt


def lookup_family_enrichment(
    enrichment: dict,
    scientific_name: str,
    genus: str | None,
) -> str | None:
    exact_match = ((enrichment.get("byScientificName") or {}).get(scientific_name) or {}).get(
        "family"
    )
    if exact_match:
        return clean_taxon(exact_match)

    genus_match = ((enrichment.get("byGenus") or {}).get(genus or "") or {}).get("family")
    if genus_match:
        return clean_taxon(genus_match)

    return None


def canonical_genus(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = re.sub(r"[^A-Za-z]", "", strip_accents(value))
    if not cleaned:
        return None
    return cleaned[0].upper() + cleaned[1:].lower()


def canonical_species_epithet(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = re.sub(r"[^A-Za-z]", "", strip_accents(value))
    return cleaned.lower() or None


def indefinite_article(phrase: str) -> str:
    return "an" if phrase[:1].lower() in {"a", "e", "i", "o", "u"} else "a"


def family_descriptor(value: str | None) -> str | None:
    if not value:
        return None
    return f"{value[:-4].lower()}id" if value.endswith("idae") else value.lower()


def pluralize(count: int, singular: str, plural: str | None = None) -> str:
    if count == 1:
        return singular
    return plural or f"{singular}s"


def pick_first_nonempty(values: list[str | None]) -> str | None:
    for value in values:
        if value:
            return value
    return None


def round_if_number(value: float | None, digits: int = 2) -> float | None:
    if value is None:
        return None
    return round(value, digits)


def format_temporal_label(early: str | None, late: str | None) -> str | None:
    if early and late and early != late:
        return f"{early} to {late}"
    return early or late


def interval_to_period(interval: str | None) -> str | None:
    if not interval:
        return None
    lowered = interval.lower()
    if any(key in lowered for key in TRIASSIC_INTERVAL_KEYS):
        return "Triassic"
    if any(key in lowered for key in JURASSIC_INTERVAL_KEYS):
        return "Jurassic"
    if any(key in lowered for key in CRETACEOUS_INTERVAL_KEYS):
        return "Cretaceous"
    return None


def geologic_period(
    max_ma: float | None,
    early_interval: str | None = None,
    late_interval: str | None = None,
) -> str | None:
    interval_period = interval_to_period(early_interval) or interval_to_period(late_interval)
    if interval_period:
        return interval_period
    if max_ma is None:
        return None
    if max_ma > JURASSIC_START_MA:
        return "Triassic"
    if max_ma >= CRETACEOUS_START_MA:
        return "Jurassic"
    if max_ma >= MESOZOIC_END_MA:
        return "Cretaceous"
    return None


def row_has_mesozoic_age(row: dict[str, str]) -> bool:
    early_interval = clean_interval(row.get("early_interval"))
    late_interval = clean_interval(row.get("late_interval"))
    if interval_to_period(early_interval) or interval_to_period(late_interval):
        return True

    candidates = (
        row.get("firstapp_max_ma"),
        row.get("lastapp_max_ma"),
        row.get("max_ma"),
        row.get("min_ma"),
    )
    for candidate in candidates:
        value = parse_float(candidate)
        if value is not None and value >= MESOZOIC_END_MA:
            return True
    return False


def annotate_source_rows(
    rows: list[dict[str, str]],
    source_spec: dict[str, str | bool],
) -> list[dict[str, str]]:
    annotated = []
    for row in rows:
        if source_spec["requires_mesozoic_filter"] and not row_has_mesozoic_age(row):
            continue
        enriched_row = dict(row)
        enriched_row["atlas_group"] = str(source_spec["atlas_group"])
        enriched_row["atlas_lineage"] = str(source_spec["lineage"] or "")
        enriched_row["source_base_name"] = str(source_spec["base_name"])
        annotated.append(enriched_row)
    return annotated


def group_noun(atlas_group: str | None) -> str:
    return {
        "Dinosaur": "dinosaur",
        "Pterosaur": "pterosaur",
        "Marine reptile": "marine reptile",
        "Crocodyliform": "crocodyliform",
        "Turtle": "turtle",
    }.get(atlas_group or "", "mesozoic animal")


def lineage_phrase(lineage: str | None) -> str | None:
    return {
        "Saurischia": "saurischian dinosaur",
        "Ornithischia": "ornithischian dinosaur",
        "Pterosauria": "pterosaur",
        "Ichthyosauria": "ichthyosaur",
        "Plesiosauria": "plesiosaur",
        "Mosasauroidea": "mosasaur",
        "Crocodyliformes": "crocodyliform",
        "Testudines": "turtle",
    }.get(lineage or "")


def infer_atlas_group(
    source_group: str | None,
    major_clade: str | None,
    order: str | None,
) -> str | None:
    if source_group:
        return source_group

    lowered_order = (order or "").lower()
    if lowered_order == "pterosauria":
        return "Pterosaur"
    if lowered_order in {"ichthyosauria", "plesiosauria", "squamata"}:
        return "Marine reptile"
    if lowered_order == "crocodyliformes":
        return "Crocodyliform"
    if lowered_order == "testudines":
        return "Turtle"
    if major_clade in {"Saurischia", "Ornithischia"}:
        return "Dinosaur"
    return None


def resolve_lineage(
    atlas_group: str | None,
    source_lineage: str | None,
    major_clade: str | None,
    order: str | None,
) -> str | None:
    if source_lineage:
        return source_lineage
    if atlas_group == "Dinosaur" and major_clade in {"Saurischia", "Ornithischia"}:
        return major_clade
    return order or major_clade


def row_priority(row: dict[str, str]) -> tuple[int, int, int]:
    exact_name = 1 if row.get("taxon_name") == row.get("accepted_name") else 0
    no_difference = 1 if not (row.get("difference") or "").strip() else 0
    occurrences = int(row.get("n_occs") or "0")
    return (exact_name, no_difference, occurrences)


def round_geometry_coordinates(coords):
    if isinstance(coords, list):
        if coords and isinstance(coords[0], (int, float)):
            return [round(float(coords[0]), 3), round(float(coords[1]), 3)]
        return [round_geometry_coordinates(item) for item in coords]
    return coords


def simplify_land_geojson(raw_geojson: dict) -> dict:
    features = []
    for feature in raw_geojson.get("features", []):
        geometry = feature.get("geometry") or {}
        features.append(
            {
                "type": "Feature",
                "geometry": {
                    "type": geometry.get("type"),
                    "coordinates": round_geometry_coordinates(
                        geometry.get("coordinates", [])
                    ),
                },
            }
        )
    return {"type": "FeatureCollection", "features": features}


def most_common(values: list[str]) -> str | None:
    filtered = [value for value in values if value]
    if not filtered:
        return None
    return Counter(filtered).most_common(1)[0][0]


def build_type_phrase(
    atlas_group: str | None,
    lineage: str | None,
    major_clade: str | None,
    family: str | None,
    type_label: str | None,
) -> str:
    noun = group_noun(atlas_group)
    if type_label:
        lowered = type_label.lower()
        if atlas_group == "Dinosaur":
            return lowered if "dinosaur" in lowered else f"{lowered} dinosaur"
        return lowered if noun in lowered else f"{lowered} {noun}"
    if family:
        return f"{family_descriptor(family)} {noun}"
    lineage_label = lineage_phrase(lineage)
    if lineage_label:
        return lineage_label
    if major_clade:
        major_clade_label = lineage_phrase(major_clade)
        if major_clade_label:
            return major_clade_label
        if atlas_group == "Dinosaur":
            return f"{major_clade.lower()} dinosaur"
        return major_clade.lower()
    return noun


def build_time_phrase(temporal_range: dict) -> str:
    period = temporal_range.get("period")
    label = temporal_range.get("label")
    if period and label and label != period:
        return f"from the {label} of the {period}"
    if period:
        return f"from the {period}"
    if label:
        return f"from the {label}"
    return ""


def build_size_sentence(size: dict) -> str | None:
    parts = []
    if size.get("lengthM") is not None:
        parts.append(f"about {size['lengthM']:.1f} m long")
    if size.get("weightKg") is not None:
        parts.append(f"roughly {int(round(size['weightKg'])):,} kg in mass")
    if not parts:
        return None
    match = size.get("match")
    if match == "genus_proxy":
        return f"A genus-level size proxy suggests it was {' and '.join(parts)}."
    return f"Available enrichment suggests it was {' and '.join(parts)}."


def build_locality_sentence(locality_count: int) -> str:
    if locality_count <= 0:
        return "No mapped fossil locality is currently attached to this species in the atlas."
    return (
        f"It is currently linked to {locality_count} mapped fossil "
        f"{pluralize(locality_count, 'locality', 'localities')} in the atlas."
    )


def choose_fallback_image(
    atlas_group: str | None,
    lineage: str | None,
    major_clade: str | None,
    family: str | None,
    order: str | None,
    type_label: str | None,
) -> str:
    lowered_group = (atlas_group or "").lower()
    lowered_lineage = (lineage or "").lower()
    lowered_major = (major_clade or "").lower()
    lowered_type = (type_label or "").lower()
    lowered_family = (family or "").lower()
    lowered_order = (order or "").lower()
    avialan_families = {
        "phasianidae",
        "megapodiidae",
        "cracidae",
        "odontophoridae",
        "alexornithidae",
        "hesperornithidae",
        "archaeopterygidae",
    }
    sauropod_families = {
        "rebbachisauridae",
        "mamenchisauridae",
        "euhelopodidae",
        "saltasauridae",
        "titanosauridae",
        "diplodocidae",
        "camarasauridae",
        "brachiosauridae",
        "nemegtosauridae",
        "euhelopodidae",
        "macronaria",
    }
    raptor_families = {
        "dromaeosauridae",
        "troodontidae",
        "oviraptoridae",
        "caenagnathidae",
        "alvarezsauridae",
        "ornithomimidae",
        "therizinosauridae",
        "avimimidae",
        "unenlagiidae",
        "archaeopterygidae",
    }

    if lowered_group == "pterosaur" or lowered_lineage == "pterosauria":
        return f"{FALLBACK_IMAGE_BASE}/pterosaur.svg"
    if (
        lowered_group == "marine reptile"
        or lowered_lineage in {"ichthyosauria", "plesiosauria", "mosasauroidea"}
    ):
        return f"{FALLBACK_IMAGE_BASE}/marine-reptile.svg"
    if lowered_group == "crocodyliform" or lowered_lineage == "crocodyliformes":
        return f"{FALLBACK_IMAGE_BASE}/crocodilian.svg"
    if (
        lowered_group == "turtle"
        or lowered_lineage == "testudines"
        or lowered_order == "testudines"
    ):
        return f"{FALLBACK_IMAGE_BASE}/turtle.svg"
    if (
        lowered_major in {"aves", "avialae"}
        or "ornithes" in lowered_order
        or "ornithiformes" in lowered_order
        or "aves" in lowered_order
        or "avial" in lowered_order
        or "bird" in lowered_type
        or "avian" in lowered_type
        or "avial" in lowered_type
        or lowered_family in avialan_families
    ):
        return f"{FALLBACK_IMAGE_BASE}/birdlike.svg"
    if (
        "ceratops" in lowered_type
        or lowered_family in {
            "ceratopsidae",
            "protoceratopsidae",
            "leptoceratopsidae",
            "psittacosauridae",
        }
    ):
        return f"{FALLBACK_IMAGE_BASE}/ceratopsian.svg"
    if (
        "hadrosaur" in lowered_type
        or "duck-billed" in lowered_type
        or "ornithopod" in lowered_type
        or lowered_family in {
            "hadrosauridae",
            "iguanodontidae",
            "hypsilophodontidae",
            "rhabdodontidae",
        }
    ):
        return f"{FALLBACK_IMAGE_BASE}/hadrosaur.svg"
    if lowered_family == "stegosauridae":
        return f"{FALLBACK_IMAGE_BASE}/stegosaur.svg"
    if lowered_family == "tyrannosauridae":
        return f"{FALLBACK_IMAGE_BASE}/tyrannosaur.svg"
    if (
        "sauropod" in lowered_type
        or "prosauropod" in lowered_type
        or lowered_family in sauropod_families
    ):
        return f"{FALLBACK_IMAGE_BASE}/sauropod.svg"
    if (
        "armoured" in lowered_type
        or "armored" in lowered_type
        or lowered_family in {"ankylosauridae", "nodosauridae", "stegosauridae"}
    ):
        return f"{FALLBACK_IMAGE_BASE}/armored.svg"
    if lowered_family in raptor_families:
        return f"{FALLBACK_IMAGE_BASE}/raptor.svg"
    if (
        "ceratopsian" in lowered_type
        or "ornithopod" in lowered_type
        or "pachycephalo" in lowered_type
        or "ornithisch" in lowered_type
        or lowered_major == "ornithischia"
    ):
        return f"{FALLBACK_IMAGE_BASE}/ornithischian.svg"
    if "theropod" in lowered_type or lowered_major == "saurischia":
        return f"{FALLBACK_IMAGE_BASE}/theropod.svg"
    return f"{FALLBACK_IMAGE_BASE}/general.svg"


def build_image_record(species: dict, enrichment: dict | None) -> dict:
    fallback_url = choose_fallback_image(
        species.get("atlasGroup"),
        species.get("lineage"),
        species.get("majorClade"),
        species.get("family"),
        species.get("order"),
        (enrichment or {}).get("typeLabel"),
    )

    return {
        "kind": "fallback",
        "detailUrl": fallback_url,
        "listUrl": fallback_url,
        "fallbackUrl": fallback_url,
        "alt": f"Illustration of {species['scientificName']}",
        "sourceDataset": "Local atlas silhouette fallback",
        "sourceUrl": fallback_url,
    }


def build_species_description(species: dict, enrichment: dict | None) -> dict:
    type_phrase = build_type_phrase(
        species.get("atlasGroup"),
        species.get("lineage"),
        species.get("majorClade"),
        species.get("family"),
        (enrichment or {}).get("typeLabel"),
    )
    opening = (
        f"{species['scientificName']} was {indefinite_article(type_phrase)} "
        f"{type_phrase}"
    )
    time_phrase = build_time_phrase(species["temporalRange"])
    if time_phrase:
        opening = f"{opening} {time_phrase}"
    summary_parts = [f"{opening}."]

    size_sentence = build_size_sentence(species["size"])
    if size_sentence:
        summary_parts.append(size_sentence)

    diet = clean_whitespace((enrichment or {}).get("diet"))
    if diet and species["size"].get("match") == "exact":
        summary_parts.append(f"Supplemental enrichment classifies it as {diet.lower()}.")

    summary_parts.append(build_locality_sentence(species["localityCount"]))

    commentary = None
    if enrichment and species["size"].get("match") == "exact":
        commentary = extract_comment_excerpt(enrichment.get("comments"))

    source_match = species["size"].get("match") or "generated"

    return {
        "summary": " ".join(summary_parts),
        "commentary": commentary,
        "sourceMatch": source_match,
    }


def apply_curated_species_overrides(species: dict) -> None:
    override = CURATED_SPECIES_OVERRIDES.get(species["scientificName"])
    if not override:
        return

    for key, value in override.items():
        species[key] = value

    if species.get("order"):
        taxonomy_path = list(species.get("taxonomyPath") or [])
        if species["order"] not in taxonomy_path:
            insertion_index = 0
            for anchor in (species.get("majorClade"), species.get("lineage")):
                if anchor in taxonomy_path:
                    insertion_index = max(insertion_index, taxonomy_path.index(anchor) + 1)
            taxonomy_path.insert(insertion_index, species["order"])
            species["taxonomyPath"] = taxonomy_path


def build_size_indexes(rows: list[dict[str, str]]) -> tuple[dict[str, dict], dict[str, dict]]:
    exact_index: dict[str, dict] = {}
    genus_groups: defaultdict[str, list[dict]] = defaultdict(list)

    for row in rows:
        genus = canonical_genus(row.get("name"))
        if not genus:
            continue

        taxonomy_path = [
            part.strip()
            for part in (row.get("taxonomy") or "").split(",")
            if part.strip()
        ]
        family = next(
            (part for part in reversed(taxonomy_path) if part.endswith("idae")),
            None,
        )
        species_epithet = canonical_species_epithet(row.get("species_type"))
        scientific_name = f"{genus} {species_epithet}" if species_epithet else None
        size_record = {
            "scientificName": scientific_name,
            "genus": genus,
            "family": family,
            "taxonomyPath": taxonomy_path or None,
            "typeLabel": (row.get("type") or "").strip() or None,
            "lengthM": parse_length_m(row.get("length")),
            "weightKg": parse_weight_kg(row.get("weight")),
            "diet": (row.get("diet") or "").strip() or None,
            "meaning": clean_whitespace(row.get("meaning")),
            "howMoved": clean_whitespace(row.get("how_moved")),
            "comments": clean_comment_text(row.get("comments")),
            "imageUrl": clean_whitespace(row.get("img_url")),
            "sourceDataset": "World Dinosaur Dataset",
            "sourceUrl": WORLD_DINO_URL,
        }

        genus_groups[normalize_lookup(genus)].append(size_record)
        if scientific_name:
            exact_index[normalize_lookup(scientific_name)] = size_record

    genus_index: dict[str, dict] = {}
    for genus_key, records in genus_groups.items():
        lengths = [record["lengthM"] for record in records if record["lengthM"] is not None]
        weights = [record["weightKg"] for record in records if record["weightKg"] is not None]
        genus_index[genus_key] = {
            "genus": records[0]["genus"],
            "family": most_common([record["family"] for record in records if record["family"]]),
            "taxonomyPath": max(
                (record["taxonomyPath"] or [] for record in records),
                key=len,
                default=[],
            )
            or None,
            "typeLabel": most_common(
                [record["typeLabel"] for record in records if record["typeLabel"]]
            ),
            "lengthM": round(mean(lengths), 2) if lengths else None,
            "weightKg": round(mean(weights), 2) if weights else None,
            "imageUrl": pick_first_nonempty([record.get("imageUrl") for record in records]),
            "sourceDataset": "World Dinosaur Dataset",
            "sourceUrl": WORLD_DINO_URL,
            "proxyFromSpecies": [
                record["scientificName"]
                for record in records
                if record["scientificName"]
            ][:6],
            "proxySpeciesCount": len(records),
        }

    return exact_index, genus_index


def build_species_database(
    taxa_rows: list[dict[str, str]],
    occurrence_rows: list[dict[str, str]],
    exact_size_index: dict[str, dict],
    genus_size_index: dict[str, dict],
    family_enrichment: dict,
) -> dict:
    preferred_taxa: dict[str, dict[str, str]] = {}
    enrichment_by_id: dict[str, dict | None] = {}

    for row in taxa_rows:
        flags = row.get("flags", "")
        if "F" in flags or "I" in flags:
            continue
        if row.get("accepted_rank") != "species":
            continue
        accepted_name = row.get("accepted_name") or row.get("taxon_name")
        if not accepted_name:
            continue
        if accepted_name.count(" ") < 1:
            continue
        key = row.get("accepted_no") or row.get("taxon_no")
        if not key:
            continue
        existing = preferred_taxa.get(key)
        if existing is None or row_priority(row) > row_priority(existing):
            preferred_taxa[key] = row

    species_by_id: dict[str, dict] = {}

    for key, row in preferred_taxa.items():
        scientific_name = row.get("accepted_name") or row.get("taxon_name")
        genus = clean_taxon(row.get("genus")) or canonical_genus(scientific_name.split()[0])
        exact_size = exact_size_index.get(normalize_lookup(scientific_name))
        genus_size = genus_size_index.get(normalize_lookup(genus))
        size_record = exact_size or genus_size
        size_match = "exact" if exact_size else "genus_proxy" if genus_size else None
        enrichment_by_id[key] = size_record

        family = (
            clean_taxon(row.get("family"))
            or (size_record or {}).get("family")
            or lookup_family_enrichment(family_enrichment, scientific_name, genus)
        )
        major_clade = clean_taxon(row.get("class"))
        order = clean_taxon(row.get("order"))
        atlas_group = infer_atlas_group(
            clean_taxon(row.get("atlas_group")),
            major_clade,
            order,
        )
        lineage = resolve_lineage(
            atlas_group,
            clean_taxon(row.get("atlas_lineage")),
            major_clade,
            order,
        )
        max_ma = parse_float(row.get("firstapp_max_ma"))
        min_ma = parse_float(row.get("lastapp_min_ma"))
        early_interval = clean_interval(row.get("early_interval"))
        late_interval = clean_interval(row.get("late_interval"))

        species_by_id[key] = {
            "id": int(key),
            "scientificName": scientific_name,
            "genus": genus,
            "atlasGroup": atlas_group,
            "lineage": lineage,
            "family": family,
            "majorClade": major_clade,
            "order": order,
            "taxonomyPath": (size_record or {}).get("taxonomyPath")
            or [part for part in [major_clade, lineage, order, family, genus] if part]
            or None,
            "temporalRange": {
                "period": geologic_period(max_ma, early_interval, late_interval),
                "label": format_temporal_label(early_interval, late_interval),
                "earlyInterval": early_interval,
                "lateInterval": late_interval,
                "startMa": round_if_number(max_ma),
                "endMa": round_if_number(min_ma),
            },
            "size": {
                "typeLabel": (size_record or {}).get("typeLabel"),
                "lengthM": (size_record or {}).get("lengthM"),
                "weightKg": (size_record or {}).get("weightKg"),
                "match": size_match,
                "sourceDataset": (size_record or {}).get("sourceDataset"),
                "sourceUrl": (size_record or {}).get("sourceUrl"),
                "proxySpeciesCount": (size_record or {}).get("proxySpeciesCount"),
                "proxyFromSpecies": (size_record or {}).get("proxyFromSpecies"),
            },
            "pbdb": {
                "acceptedNo": int(key),
                "occurrenceCount": int(row.get("n_occs") or "0"),
            },
            "classificationNote": None,
            "description": None,
            "image": None,
            "localityCount": 0,
            "localities": [],
            "coordinateBounds": None,
        }

    species_localities: defaultdict[str, dict[str, dict]] = defaultdict(dict)

    for row in occurrence_rows:
        flags = row.get("flags", "")
        if "F" in flags or "I" in flags:
            continue
        if row.get("accepted_rank") != "species":
            continue

        key = row.get("accepted_no")
        if not key:
            continue
        accepted_name = row.get("accepted_name") or row.get("identified_name") or ""
        if accepted_name.count(" ") < 1:
            continue

        lat = parse_float(row.get("lat"))
        lng = parse_float(row.get("lng"))
        if lat is None or lng is None:
            continue

        if key not in species_by_id:
            scientific_name = accepted_name
            genus = clean_taxon(row.get("genus")) or canonical_genus(scientific_name.split()[0])
            major_clade = clean_taxon(row.get("class"))
            order = clean_taxon(row.get("order"))
            atlas_group = infer_atlas_group(
                clean_taxon(row.get("atlas_group")),
                major_clade,
                order,
            )
            lineage = resolve_lineage(
                atlas_group,
                clean_taxon(row.get("atlas_lineage")),
                major_clade,
                order,
            )
            species_by_id[key] = {
                "id": int(key),
                "scientificName": scientific_name,
                "genus": genus,
                "atlasGroup": atlas_group,
                "lineage": lineage,
                "family": clean_taxon(row.get("family"))
                or lookup_family_enrichment(family_enrichment, scientific_name, genus),
                "majorClade": major_clade,
                "order": order,
                "taxonomyPath": [part for part in [major_clade, lineage, order, clean_taxon(row.get("family")), genus] if part]
                or None,
                "temporalRange": {
                    "period": geologic_period(
                        parse_float(row.get("max_ma")),
                        clean_interval(row.get("early_interval")),
                        clean_interval(row.get("late_interval")),
                    ),
                    "label": format_temporal_label(
                        clean_interval(row.get("early_interval")),
                        clean_interval(row.get("late_interval")),
                    ),
                    "earlyInterval": clean_interval(row.get("early_interval")),
                    "lateInterval": clean_interval(row.get("late_interval")),
                    "startMa": round_if_number(parse_float(row.get("max_ma"))),
                    "endMa": round_if_number(parse_float(row.get("min_ma"))),
                },
                "size": {
                    "typeLabel": None,
                    "lengthM": None,
                    "weightKg": None,
                    "match": None,
                    "sourceDataset": None,
                    "sourceUrl": None,
                    "proxySpeciesCount": None,
                    "proxyFromSpecies": None,
                },
                "pbdb": {
                    "acceptedNo": int(key),
                    "occurrenceCount": 0,
                },
                "classificationNote": None,
                "description": None,
                "image": None,
                "localityCount": 0,
                "localities": [],
                "coordinateBounds": None,
            }
            exact_size = exact_size_index.get(normalize_lookup(scientific_name))
            genus_size = genus_size_index.get(normalize_lookup(genus))
            size_record = exact_size or genus_size
            if key not in enrichment_by_id:
                enrichment_by_id[key] = size_record
            if size_record:
                species_by_id[key]["size"]["typeLabel"] = size_record.get("typeLabel")
                species_by_id[key]["size"]["lengthM"] = size_record.get("lengthM")
                species_by_id[key]["size"]["weightKg"] = size_record.get("weightKg")
                species_by_id[key]["size"]["match"] = (
                    "exact" if exact_size else "genus_proxy" if genus_size else None
                )
                species_by_id[key]["size"]["sourceDataset"] = size_record.get("sourceDataset")
                species_by_id[key]["size"]["sourceUrl"] = size_record.get("sourceUrl")
                species_by_id[key]["size"]["proxySpeciesCount"] = size_record.get(
                    "proxySpeciesCount"
                )
                species_by_id[key]["size"]["proxyFromSpecies"] = size_record.get(
                    "proxyFromSpecies"
                )

        locality_key = row.get("collection_no") or (
            f"{round(lat, 3)}:{round(lng, 3)}:{row.get('early_interval')}:{row.get('late_interval')}"
        )
        locality = species_localities[key].setdefault(
            locality_key,
            {
                "collectionNo": int(row["collection_no"]) if row.get("collection_no") else None,
                "lat": round(lat, 4),
                "lng": round(lng, 4),
                "earlyInterval": clean_interval(row.get("early_interval")),
                "lateInterval": clean_interval(row.get("late_interval")),
                "startMa": round_if_number(parse_float(row.get("max_ma"))),
                "endMa": round_if_number(parse_float(row.get("min_ma"))),
                "count": 0,
            },
        )
        locality["count"] += 1

    for key, species in species_by_id.items():
        apply_curated_species_overrides(species)
        localities = sorted(
            species_localities.get(key, {}).values(),
            key=lambda item: (-item["count"], item["lat"], item["lng"]),
        )
        species["localities"] = localities
        species["localityCount"] = len(localities)
        if localities:
            lats = [item["lat"] for item in localities]
            lngs = [item["lng"] for item in localities]
            species["coordinateBounds"] = {
                "minLat": min(lats),
                "maxLat": max(lats),
                "minLng": min(lngs),
                "maxLng": max(lngs),
            }
        species["description"] = build_species_description(
            species,
            enrichment_by_id.get(key),
        )
        species["image"] = build_image_record(species, enrichment_by_id.get(key))

    species_list = sorted(species_by_id.values(), key=lambda item: item["scientificName"])
    mapped_species = sum(1 for species in species_list if species["localityCount"] > 0)
    total_localities = sum(species["localityCount"] for species in species_list)
    exact_size_count = sum(
        1 for species in species_list if species["size"].get("match") == "exact"
    )
    genus_proxy_size_count = sum(
        1 for species in species_list if species["size"].get("match") == "genus_proxy"
    )
    exact_image_count = sum(1 for species in species_list if species["image"]["kind"] == "exact")
    genus_proxy_image_count = sum(
        1 for species in species_list if species["image"]["kind"] == "genus_proxy"
    )
    fallback_image_count = sum(
        1 for species in species_list if species["image"]["kind"] == "fallback"
    )
    group_counts = Counter(species["atlasGroup"] for species in species_list if species["atlasGroup"])

    return {
        "metadata": {
            "generatedAt": datetime.now(timezone.utc).isoformat(),
            "speciesCount": len(species_list),
            "mappedSpeciesCount": mapped_species,
            "localityCount": total_localities,
            "sizeExactCount": exact_size_count,
            "sizeGenusProxyCount": genus_proxy_size_count,
            "imageExactCount": exact_image_count,
            "imageGenusProxyCount": genus_proxy_image_count,
            "imageFallbackCount": fallback_image_count,
            "groupCounts": dict(sorted(group_counts.items())),
            "notes": [
                "Species are sourced from PBDB feeds spanning dinosaurs, pterosaurs, marine reptiles, crocodyliforms, and turtles.",
                "Lineages with Cenozoic survivors are filtered to retain only Mesozoic-age records in this atlas.",
                "Form taxa and ichnotaxa are excluded by removing PBDB records flagged with F and/or I.",
                "Only accepted species-level PBDB names are retained in the generated database.",
                "Map localities are aggregated from PBDB species-level fossil occurrences with coordinates.",
                "Size values are currently enriched only where the dinosaur-focused World Dinosaur Dataset provides an exact species match or genus proxy.",
                "Missing family names may be conservatively filled from explicit Wikipedia or Wikispecies family rows when PBDB leaves them blank.",
                "Each species record includes a generated description, with supplemental source commentary when an exact enrichment match is available.",
                "Each species record includes a local atlas silhouette fallback image matched to its broad lineage.",
            ],
            "sources": [
                *[
                    {
                        "name": f"PBDB taxa API: {source_spec['base_name']}",
                        "url": build_pbdb_taxa_url(str(source_spec["base_name"])),
                        "role": f"{source_spec['atlas_group']} species and taxonomy",
                    }
                    for source_spec in ATLAS_SOURCE_SPECS
                ],
                *[
                    {
                        "name": f"PBDB occurrences API: {source_spec['base_name']}",
                        "url": build_pbdb_occurrences_url(str(source_spec["base_name"])),
                        "role": f"{source_spec['atlas_group']} occurrence coordinates and interval data",
                    }
                    for source_spec in ATLAS_SOURCE_SPECS
                ],
                {
                    "name": "World Dinosaur Dataset",
                    "url": WORLD_DINO_URL,
                    "role": "Dinosaur length, weight, and type enrichment when available",
                },
                {
                    "name": "Wikipedia",
                    "url": "https://en.wikipedia.org/",
                    "role": "Conservative family backfill from explicit family rows when source taxonomy is blank",
                },
                {
                    "name": "Wikispecies",
                    "url": "https://species.wikimedia.org/",
                    "role": "Conservative family backfill from explicit family rows when source taxonomy is blank",
                },
            ],
        },
        "species": species_list,
    }


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def write_js_assignment(path: Path, variable_name: str, payload: dict) -> None:
    path.write_text(
        f"window.{variable_name} = {json.dumps(payload, separators=(',', ':'))};\n",
        encoding="utf-8",
    )


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    data_dir = project_root / "data"
    raw_dir = data_dir / "raw"
    data_dir.mkdir(parents=True, exist_ok=True)

    taxa_rows: list[dict[str, str]] = []
    occurrence_rows: list[dict[str, str]] = []
    for source_spec in ATLAS_SOURCE_SPECS:
        taxa_rows.extend(
            annotate_source_rows(
                parse_csv(
                    load_source_text(
                        raw_dir / f"pbdb-{source_spec['slug']}-taxa.csv",
                        build_pbdb_taxa_url(str(source_spec["base_name"])),
                    )
                ),
                source_spec,
            )
        )
        occurrence_rows.extend(
            annotate_source_rows(
                parse_csv(
                    load_source_text(
                        raw_dir / f"pbdb-{source_spec['slug']}-occurrences.csv",
                        build_pbdb_occurrences_url(str(source_spec["base_name"])),
                    )
                ),
                source_spec,
            )
        )

    size_rows = parse_csv(
        load_source_text(raw_dir / "world-dinosaur-dataset.csv", WORLD_DINO_URL)
    )
    land_geojson = simplify_land_geojson(
        json.loads(load_source_text(raw_dir / "world-land.geojson", WORLD_LAND_URL))
    )

    exact_size_index, genus_size_index = build_size_indexes(size_rows)
    family_enrichment = load_json_if_exists(raw_dir / "wikipedia-family-enrichment.json")
    database = build_species_database(
        taxa_rows,
        occurrence_rows,
        exact_size_index,
        genus_size_index,
        family_enrichment,
    )

    write_json(data_dir / "dinosaur-database.json", database)
    write_js_assignment(data_dir / "dinosaur-database.js", "DINOSAUR_ATLAS_DATA", database)
    write_json(data_dir / "world-land.json", land_geojson)
    write_js_assignment(data_dir / "world-land.js", "DINOSAUR_ATLAS_WORLD", land_geojson)

    metadata = database["metadata"]
    print(f"Species: {metadata['speciesCount']}")
    print(f"Mapped species: {metadata['mappedSpeciesCount']}")
    print(f"Localities: {metadata['localityCount']}")
    print(f"Exact size matches: {metadata['sizeExactCount']}")
    print(f"Genus proxy size matches: {metadata['sizeGenusProxyCount']}")


if __name__ == "__main__":
    main()
