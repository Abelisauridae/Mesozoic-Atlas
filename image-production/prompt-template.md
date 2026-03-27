# Dinosaur Atlas Prompt Template

Use this as the master template for any image model or illustrator brief.

## Master prompt

```text
Create a square illustrated dinosaur family card for [TAXON], a [LEVEL] dinosaur group from the Dinosaur Atlas project. Show one featured adult animal as the clear focal subject, using [COMPOSITION_ARCHETYPE]. Emphasize the family-defining anatomy: [KEY_TRAITS]. The animal must read instantly at thumbnail size.

Visual style: premium natural-history illustration card, crisp black linework, soft cel-shaded color, subtle surface texture, muted realistic palette, clean silhouette design, museum-compendium aesthetic, simplified but believable prehistoric habitat, strong readability, polished digital illustration rather than photoreal painting.

Environment: [HABITAT]. Lighting: [LIGHTING]. Color direction: [PALETTE]. Mood: confident, elegant, scientifically inspired, and cohesive with a premium dinosaur atlas card set.

Layout constraints: square composition, rounded card border area, reserved blank title band at the bottom for later typography, optional reserved badge space in the lower-right corner, no rendered text, no logo, no watermark. Keep the habitat graphic and supportive, not overcrowded. The subject should dominate the card.
```

## Negative prompt

```text
photorealistic, movie poster, 3d render, anime, chibi, toy, plastic, low detail, muddy anatomy, extra limbs, malformed claws, monster design, fantasy dragon, random spikes, oversaturated neon, gibberish text, logo, watermark, collage, multi-panel layout, modern plants, humans, vehicles, excessive gore, cluttered background
```

## Per-image fill-ins

- `TAXON`: family or major clade name
- `LEVEL`: `family` or `major clade`
- `COMPOSITION_ARCHETYPE`: one of the locked body-plan compositions from the house style guide
- `KEY_TRAITS`: 3 to 6 anatomical features that define the taxon
- `HABITAT`: broad habitat cue only, not a distracting story scene
- `LIGHTING`: usually soft natural light or warm diffuse daylight
- `PALETTE`: muted, natural, and lineage-appropriate

## House defaults

- one hero animal
- square card art
- readable silhouette first, texture second
- clean linework with soft graphic shading
- generated title area left blank for post-production text
