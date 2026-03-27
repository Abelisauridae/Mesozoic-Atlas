# Mesozoic Atlas

Static Mesozoic atlas app built from PBDB occurrence data plus supplemental dinosaur size enrichment.

Each species record includes a generated description summary, and exact World Dinosaur Dataset matches can also contribute a short supplemental note.
Each species also includes image metadata that points to a local lineage-aware silhouette.

## Open the app

Open `index.html` in a browser. The data is loaded from local JavaScript files, so it does not require a local dev server just to view it.

## Rebuild the database

1. Refresh the raw source cache in `data/raw` if you want newer source exports.
2. Run:

```bash
python3 dinosaur-atlas/scripts/build_dinosaur_data.py
```

The generator writes:

- `data/dinosaur-database.json`
- `data/dinosaur-database.js`
- `data/world-land.json`
- `data/world-land.js`

The data filenames intentionally stay stable so the static site and GitHub Pages deployment do not need extra routing changes.

## Current dataset coverage

- 2,932 accepted species across dinosaurs, pterosaurs, marine reptiles, crocodyliforms, and turtles
- 2,877 species with mapped fossil coordinates
- 6,881 aggregated fossil localities
- group coverage: 1,595 dinosaurs, 276 pterosaurs, 386 marine reptiles, 295 crocodyliforms, 380 turtles
- 295 exact size matches
- 131 genus-proxy size matches
- image coverage for all 2,932 species through local lineage-aware silhouettes
- public data files remain below GitHub's 25 MB web upload limit

## Sources

- PBDB taxonomic names API for accepted species and taxonomy across multiple Mesozoic clades
- PBDB fossil occurrences API for coordinates and interval data
- World Dinosaur Dataset for dinosaur length, weight, and type enrichment where available
- Natural Earth 1:110m land polygons for the map backdrop
