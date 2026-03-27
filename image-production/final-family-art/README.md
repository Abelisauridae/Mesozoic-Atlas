# Final Family Art

Put approved production images for the atlas here.

## Naming rule

Each final image should use the `image_id` from `family-image-manifest.csv` as its filename stem.

Examples:

- `family-abelisauridae.png`
- `family-ceratopsidae.webp`
- `fallback-saurischia.png`

## Accepted formats

- `.png`
- `.jpg`
- `.jpeg`
- `.webp`
- `.svg`

## Completion check

Run:

```bash
python3 check_image_completion.py
```

from the `image-production` folder to see how many of the 110 required images are present.
