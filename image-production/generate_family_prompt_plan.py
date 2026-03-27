#!/usr/bin/env python3
"""Generate a first-pass family-card prompt plan from the atlas manifest."""

from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parent
MANIFEST_PATH = ROOT / "family-image-manifest.csv"
DATABASE_PATH = ROOT.parent / "data" / "dinosaur-database.json"
OUTPUT_CSV_PATH = ROOT / "family-card-prompt-plan.csv"
OUTPUT_SUMMARY_PATH = ROOT / "family-card-prompt-plan.md"


@dataclass(frozen=True)
class GroupSpec:
    composition_archetype: str
    key_traits: str
    habitat: str
    lighting: str
    palette: str
    mood: str
    confidence: str
    review_note: str = ""


GROUP_SPECS: dict[str, GroupSpec] = {
    "abelisaurid_predator": GroupSpec(
        composition_archetype="giant-theropod card: head-and-torso dominant, powerful forward stride, strong front 3/4 view",
        key_traits="deep short skull, horned or ornamented brow region, tiny forelimbs, muscular hind legs, compact predatory build",
        habitat="semi-arid rocky upland with sparse plants and simplified distant volcanic forms",
        lighting="warm late-afternoon light with clean shadow shapes",
        palette="dusty taupe, charcoal, ember orange, muted mauve sky, and dry earth brown",
        mood="fierce, iconic, and controlled",
        confidence="high",
    ),
    "large_theropod_predator": GroupSpec(
        composition_archetype="large-predator card: strong 3/4 stride, head and torso dominant, tail receding cleanly through the frame",
        key_traits="large skull, serrated jaws, muscular neck, strong hind limbs, balanced tail, grasping forelimbs sized appropriately to the lineage",
        habitat="open floodplain or rocky woodland edge with simplified terrain and atmospheric distance",
        lighting="warm directional daylight with subtle haze",
        palette="charcoal, bark brown, sandstone, dusty olive, and warm amber highlights",
        mood="powerful, noble, and dramatic without feeling monstrous",
        confidence="medium",
    ),
    "ceratosaur_predator": GroupSpec(
        composition_archetype="medium-predator card: agile biped in 3/4 view with the head profile clearly readable",
        key_traits="light but predatory build, narrow skull with family-appropriate ornamentation, strong hind legs, long tail, compact forelimbs",
        habitat="dry scrubland or rocky floodplain with low plants and clean negative space behind the head",
        lighting="warm daylight with crisp shadows",
        palette="ochre, umber, dusty red-brown, olive scrub green, and warm stone gray",
        mood="lean, alert, and dangerous",
        confidence="medium",
    ),
    "basal_theropod_predator": GroupSpec(
        composition_archetype="slender-theropod card: full-body dynamic stance, body and tail cleanly visible, head lifted alertly",
        key_traits="slender bipedal predator, long tail, grasping forelimbs, narrow skull, fast-running build",
        habitat="open Triassic or Jurassic floodplain with low cycads, sparse conifers, and lightly layered hills",
        lighting="bright diffuse daylight",
        palette="earth brown, muted rust, sage green, pale stone, and dusty sky blue",
        mood="active, ancestral, and cleanly readable",
        confidence="medium",
    ),
    "tyrannosauroid_predator": GroupSpec(
        composition_archetype="giant-predator card: massive skull and chest forward in a commanding 3/4 stance",
        key_traits="deep skull, heavy jaws, powerful hind limbs, muscular torso, thick tail, reduced forelimbs or smaller arms for the lineage",
        habitat="broad woodland plain with simple trees and open sky around the head silhouette",
        lighting="warm sunset or low-angle daylight",
        palette="charcoal, umber, moss green, dry tan, and horn-ivory accents",
        mood="dominant, iconic, and ancient",
        confidence="high",
    ),
    "spinosaurid_predator": GroupSpec(
        composition_archetype="semiaquatic predator card: long-bodied 3/4 stride with elongated snout and sail clearly visible",
        key_traits="elongated crocodile-like snout, conical teeth, tall sail or extended dorsal spines, strong forelimbs, semi-aquatic posture",
        habitat="river margin or swamp edge with shallow water, reeds, and broad open space around the sail",
        lighting="humid warm daylight with soft reflected light from water",
        palette="olive green, muddy tan, dark slate, muted russet, and wet reed green",
        mood="strange, formidable, and unmistakable",
        confidence="high",
    ),
    "megaraptor_predator": GroupSpec(
        composition_archetype="large-predator card: dynamic 3/4 stride with long arms and grasping claws made prominent",
        key_traits="slender predatory skull, long forelimbs, enlarged hand claws, athletic hind limbs, sweeping tail",
        habitat="wooded floodplain with open ground and distant haze",
        lighting="warm directional daylight",
        palette="charcoal, warm gray, tawny brown, muted forest green, and pale stone",
        mood="fast, dangerous, and elegant",
        confidence="medium",
        review_note="Family-level forelimb emphasis is important here; verify anatomy before final render.",
    ),
    "dromaeosaur_predator": GroupSpec(
        composition_archetype="small-predator card: full-body dynamic pose with tail extended cleanly and raised sickle claw visible",
        key_traits="feathered body, agile build, raised sickle claw, stiff balancing tail, grasping forelimbs, alert predatory posture",
        habitat="light forest path or ferny woodland edge with open space around the silhouette",
        lighting="soft directional daylight through trees",
        palette="tawny brown, cream, charcoal, blue-black feather accents, and warm forest green",
        mood="agile, intelligent, and vivid",
        confidence="high",
    ),
    "troodontid_predator": GroupSpec(
        composition_archetype="small feathered hunter card: full-body poised stance with head, eye, and claw silhouette emphasized",
        key_traits="light feathered body, long legs, grasping hands, alert head, stiff tail, agile predatory stance",
        habitat="woodland edge with low shrubs and clean pale sky openings",
        lighting="bright but soft daylight",
        palette="warm brown, gray, cream, muted amber, and moss green",
        mood="quick, curious, and sharp",
        confidence="medium",
    ),
    "feathered_glider": GroupSpec(
        composition_archetype="small feathered card: full-body perch or gliding-ready stance with wings, tail, and head profile clearly visible",
        key_traits="feathered arms or wings, long feathered tail, light body, grasping feet, bird-like but still dinosaurian anatomy",
        habitat="tree trunks, branches, and fern-rich forest layers with clean sky openings",
        lighting="cool daylight with soft atmospheric depth",
        palette="warm gray, cream, russet, muted black, moss green, and pale teal sky",
        mood="graceful, early-avian, and refined",
        confidence="medium",
    ),
    "alvarezsaur_runner": GroupSpec(
        composition_archetype="small runner card: full-body side or 3/4 pose with long legs and compact body dominating the frame",
        key_traits="light cursorial body, long hind limbs, short powerful forelimbs, narrow head, bird-like posture",
        habitat="dry scrub plain or open woodland floor with low plants and stones",
        lighting="clean daylight with firm shadow shapes",
        palette="sand tan, rust brown, charcoal, muted olive, and pale blue sky",
        mood="nimble, unusual, and lively",
        confidence="medium",
    ),
    "oviraptor_beaked": GroupSpec(
        composition_archetype="beaked-maniraptoran card: full-body 3/4 pose with crest, beak, feathered arms, and tail fan readable",
        key_traits="beaked skull, family-appropriate crest, feathered body or arms, grasping hands, agile bipedal build",
        habitat="desert edge or open floodplain with low shrubs and clear silhouette spacing",
        lighting="warm diffuse daylight",
        palette="dusty tan, cream, muted red-brown, charcoal, and soft sage green",
        mood="ornate, intelligent, and distinctive",
        confidence="medium",
    ),
    "ornithomimosaur_runner": GroupSpec(
        composition_archetype="runner card: full-body side or 3/4 stride with long neck, long legs, and graceful speed emphasized",
        key_traits="ostrich-like body, long legs, long neck, small head, balancing tail, light feathery accents where appropriate",
        habitat="open plain or sandy floodplain with sparse plants and broad sky",
        lighting="bright daylight with clean cast shadows",
        palette="sand, cream, taupe, olive scrub, and pale sky blue",
        mood="swift, elegant, and clean",
        confidence="high",
    ),
    "deinocheirid_giant": GroupSpec(
        composition_archetype="large-beaked oddball card: full-body 3/4 stance with huge forelimbs and unusual silhouette emphasized",
        key_traits="deep-bodied build, long forelimbs, large claws, beaked head, humped or tall-backed silhouette, long legs",
        habitat="wet floodplain with reeds, shallow water, and open space around the torso shape",
        lighting="soft warm daylight",
        palette="muddy tan, olive, slate gray, cream, and reed green",
        mood="imposing, strange, and memorable",
        confidence="high",
    ),
    "therizinosaur_browser": GroupSpec(
        composition_archetype="tall-feathered browser card: full-body 3/4 stance with long claws and pot-bellied torso clearly readable",
        key_traits="long neck, deep torso, enormous hand claws, feathered body, strong hind legs, browsing posture",
        habitat="wooded riverside or ferny floodplain with tall plants framing but not obscuring the claws",
        lighting="warm diffuse forest-edge daylight",
        palette="umber, moss green, cream, charcoal, and muted rust accents",
        mood="uncanny, calm, and majestic",
        confidence="high",
    ),
    "basal_sauropodomorph": GroupSpec(
        composition_archetype="early-long-neck card: full-body side or 3/4 stance with lighter build and neck/tail balance clearly visible",
        key_traits="elongated neck, smaller head, long tail, lighter sauropodomorph body, strong hind limbs, early herbivorous build",
        habitat="Triassic or early Jurassic woodland edge with cycads, conifers, and open ground",
        lighting="clean daylight with slight warm haze",
        palette="dusty brown, olive, cream, bark gray, and pale green-blue sky",
        mood="ancestral, steady, and elegant",
        confidence="medium",
    ),
    "early_sauropod": GroupSpec(
        composition_archetype="early-sauropod card: full-body side profile with strong torso mass and rising neck shape",
        key_traits="long neck, columnar limbs, heavy torso, small head, long tail, primitive sauropod proportions",
        habitat="open conifer plain with fern understory and distant low hills",
        lighting="bright diffuse daylight",
        palette="stone gray, bark brown, sage, pale tan, and soft blue sky",
        mood="monumental and foundational",
        confidence="medium",
    ),
    "sauropod_high_browser": GroupSpec(
        composition_archetype="high-browser sauropod card: full-body composition with tall forequarters and neck reaching upward through the square frame",
        key_traits="long neck, small head, tall shoulders, columnar limbs, immense body mass, long tail",
        habitat="open woodland or river plain with tall trees and clear air around the neck silhouette",
        lighting="bright daylight with cool atmospheric depth",
        palette="stone gray, dusty olive, pale tan, bark brown, and soft blue-green sky",
        mood="majestic, towering, and calm",
        confidence="high",
    ),
    "sauropod_long_neck": GroupSpec(
        composition_archetype="long-neck sauropod card: full-body composition with the neck sweeping upward and the whole body grounded in the foreground",
        key_traits="extremely long neck, small head, deep torso, columnar limbs, long tail, graceful massive proportions",
        habitat="lush conifer forest or broad floodplain clearing with open sky to keep the neck readable",
        lighting="bright diffuse daylight with cool background fade",
        palette="stone gray, sage, dusty taupe, moss, and pale blue-green sky",
        mood="monumental, calm, and ancient",
        confidence="high",
    ),
    "sauropod_whiptail": GroupSpec(
        composition_archetype="slender sauropod card: full-body side or 3/4 stance with long tail and neck sweeping elegantly through the frame",
        key_traits="long neck, elongated whip-like tail or slender tail, lighter sauropod torso, small head, columnar limbs",
        habitat="open floodplain with fern beds, scattered conifers, and distant hills",
        lighting="warm daylight with atmospheric distance",
        palette="slate gray, muted brown, moss green, pale sand, and sky blue",
        mood="graceful, expansive, and stately",
        confidence="high",
    ),
    "sauropod_robust": GroupSpec(
        composition_archetype="robust sauropod card: full-body grounded stance with heavy torso and stable limb posture emphasized",
        key_traits="long neck, small head, broad deep torso, stout limbs, long tail, immense herbivorous build",
        habitat="open woodland or floodplain with low shrubs and broad sky",
        lighting="soft warm daylight",
        palette="weathered brown, taupe, olive, horn-gray, and muted sky blue",
        mood="massive, dependable, and serene",
        confidence="medium",
    ),
    "armored_ankylosaur": GroupSpec(
        composition_archetype="armored quadruped card: full-body low 3/4 stance with armor silhouette and tail weapon clearly visible",
        key_traits="low broad body, osteoderm armor, wide torso, heavy limbs, armored head, tail club where appropriate",
        habitat="open scrub woodland with low cycads and simple background spacing around the armor outline",
        lighting="bright daylight with crisp shadows",
        palette="olive, ochre, bark brown, horn-gray, and dusty green",
        mood="solid, defensive, and iconic",
        confidence="high",
    ),
    "armored_nodosaur": GroupSpec(
        composition_archetype="armored quadruped card: full-body 3/4 stance with shoulder spikes and armor silhouette emphasized",
        key_traits="low armored body, broad torso, strong limbs, shoulder spikes or heavy osteoderms, narrow head, defensive stance",
        habitat="woodland edge with low ferns and clear ground plane",
        lighting="soft daylight",
        palette="olive, muted tan, bark brown, stone gray, and sage green",
        mood="rugged, defensive, and ancient",
        confidence="medium",
    ),
    "stegosaur_plated": GroupSpec(
        composition_archetype="plated herbivore card: full-body side or 3/4 stance with dorsal plates and tail spikes clearly separated from the background",
        key_traits="arched back, large dorsal plates, spiked tail, small head, sturdy hindquarters, quadrupedal herbivore build",
        habitat="open woodland or fern plain with low vegetation and soft distant trees",
        lighting="warm daylight with clean shadow shapes",
        palette="ochre, olive, bark brown, pale horn, and moss green",
        mood="distinctive, stately, and recognizable",
        confidence="high",
    ),
    "ceratopsian_horned": GroupSpec(
        composition_archetype="horned-quadruped card: full-body forward 3/4 stance with the horns and frill dominating the silhouette",
        key_traits="broad facial frill, large brow horns, nasal horn, beaked mouth, heavy quadrupedal build, rugged skin texture",
        habitat="subtropical woodland edge with palms, low shrubs, and soft distant hills",
        lighting="bright diffuse daylight with soft warm shadows",
        palette="olive, ochre, horn-ivory, bark brown, and pale sage sky",
        mood="noble, ancient, and approachable",
        confidence="high",
    ),
    "ceratopsian_small": GroupSpec(
        composition_archetype="small ceratopsian card: full-body 3/4 stance with beak, frill shape, and compact body profile emphasized",
        key_traits="parrot-like beak, modest frill, compact herbivore body, sturdy limbs, clear head ornament silhouette",
        habitat="dry woodland or scrub plain with low plants and distant rocky hills",
        lighting="warm daylight",
        palette="tan, muted olive, ochre, bark brown, and pale blue sky",
        mood="sturdy, distinctive, and lively",
        confidence="medium",
    ),
    "psittacosaur_beaked": GroupSpec(
        composition_archetype="small beaked herbivore card: full-body 3/4 stance with oversized head, beak, and compact body immediately readable",
        key_traits="parrot-like beak, compact body, sturdy hind limbs, long tail, family-appropriate bristles or quills where suitable",
        habitat="dry fern-and-cycad plain with scattered shrubs and open sky",
        lighting="clear daylight with soft shadows",
        palette="sandy tan, olive, warm brown, muted cream, and pale sky blue",
        mood="curious, compact, and memorable",
        confidence="high",
    ),
    "hadrosaur_duckbill": GroupSpec(
        composition_archetype="medium-herbivore card: full-body walking or alert standing pose with the duck-billed head and overall body shape immediately readable",
        key_traits="duck-billed skull, elongated herbivore body, strong hind limbs, balancing tail, family-appropriate crest when suitable",
        habitat="lush river margin or floodplain with layered greenery and calm water",
        lighting="soft morning daylight with gentle atmospheric fade",
        palette="moss green, tan, cream, muted olive, and cool water-blue accents",
        mood="calm, stately, and natural-history focused",
        confidence="high",
    ),
    "iguanodont_ornithopod": GroupSpec(
        composition_archetype="large ornithopod card: full-body 3/4 stance with sturdy torso, beaked head, and powerful forelimbs visible",
        key_traits="beaked head, robust herbivore body, strong hind limbs, muscular forelimbs, long tail, active browsing posture",
        habitat="wooded floodplain with shrubs, low trees, and open negative space behind the head",
        lighting="warm daylight with soft haze",
        palette="olive, bark brown, cream, muted rust, and pale green sky",
        mood="steady, capable, and classic",
        confidence="medium",
    ),
    "small_ornithopod": GroupSpec(
        composition_archetype="small runner-herbivore card: full-body side or 3/4 pose with clean tail and hind-limb silhouette",
        key_traits="small beaked herbivore, long hind limbs, balancing tail, light body, alert posture",
        habitat="open fern plain or woodland floor with low plants and clean horizon space",
        lighting="bright diffuse daylight",
        palette="olive, tan, warm gray, moss green, and pale sky blue",
        mood="nimble, approachable, and clear",
        confidence="medium",
    ),
    "heterodontosaur_small": GroupSpec(
        composition_archetype="small unusual herbivore card: full-body pose with compact body, beaked head, and facial silhouette emphasized",
        key_traits="small beaked body, heterodont dentition cues, long hind limbs, long tail, nimble omnivorous-herbivorous build",
        habitat="dry scrub or fern plain with open space around the body",
        lighting="clear daylight",
        palette="olive, warm tan, cream, bark brown, and dusty green",
        mood="quirky, early, and lively",
        confidence="medium",
    ),
    "pachycephalosaur_dome": GroupSpec(
        composition_archetype="dome-headed herbivore card: full-body 3/4 stance with skull dome and sturdy bipedal body made prominent",
        key_traits="domed or ornamented skull roof, compact bipedal herbivore body, strong hind limbs, balancing tail, sturdy neck",
        habitat="open woodland or scrubland with low grasses and soft distant hills",
        lighting="warm daylight",
        palette="ochre, olive, horn-gray, bark brown, and pale sky",
        mood="tough, distinctive, and grounded",
        confidence="high",
    ),
    "early_bird_perching": GroupSpec(
        composition_archetype="early-bird card: full-body perched or lightly grounded pose with wings, tail, and head profile clearly readable",
        key_traits="small avialan body, feathered wings, bird-like feet, long or moderate tail, early-bird skull profile",
        habitat="branchy woodland edge or lakeside grove with open sky windows around the wings",
        lighting="soft daylight with cool atmospheric depth",
        palette="cream, warm brown, charcoal, moss green, and pale teal sky",
        mood="delicate, alert, and natural-history refined",
        confidence="medium",
        review_note="Many of these lineages need a final anatomical check for wing and tail proportions.",
    ),
    "shoreline_bird": GroupSpec(
        composition_archetype="waterside avialan card: full-body pose near shore with long beak or fish-eating profile emphasized",
        key_traits="bird-like wings, streamlined body, long or specialized beak, clear leg and tail silhouette, fish-eating or waterside posture",
        habitat="lake edge or river shore with reeds, shallow water, and open sky",
        lighting="soft daylight with reflected water light",
        palette="cool gray, cream, olive reed green, muted brown, and pale blue sky",
        mood="graceful, aquatic, and elegant",
        confidence="medium",
    ),
    "diving_bird": GroupSpec(
        composition_archetype="aquatic bird card: full-body shoreline or water-entry pose with body streamlined and feet readable",
        key_traits="diving bird body, streamlined torso, strong feet, reduced or specialized wings where appropriate, elongated neck or head profile",
        habitat="open lake or coastal margin with calm water and distant horizon",
        lighting="clear daylight with cool reflected light",
        palette="slate gray, cream, water blue, reed green, and muted brown",
        mood="sleek, aquatic, and composed",
        confidence="high",
    ),
    "ground_bird": GroupSpec(
        composition_archetype="ground-bird card: full-body 3/4 walking stance with body mass, legs, and plumage silhouette cleanly readable",
        key_traits="ground-dwelling bird body, feathered wings, sturdy legs, compact tail, family-appropriate crest or facial features where suitable",
        habitat="open undergrowth, scrub, or woodland floor with simple layered plants",
        lighting="bright natural daylight",
        palette="earth brown, cream, muted chestnut, charcoal, and soft green",
        mood="alert, terrestrial, and approachable",
        confidence="high",
    ),
    "large_flightless_bird": GroupSpec(
        composition_archetype="large terrestrial bird card: full-body 3/4 stance with height and heavy bird silhouette emphasized",
        key_traits="large bird-like body, long legs, reduced flight capacity, powerful torso, strong neck, clear beak silhouette",
        habitat="open plain or woodland edge with simple vegetation and clear horizon",
        lighting="warm daylight",
        palette="brown, cream, gray, muted olive, and pale sky blue",
        mood="rare, imposing, and unusual",
        confidence="low",
        review_note="Very sparse family-level reference material; use this only as a first-pass concept prompt.",
    ),
    "ootaxon_review": GroupSpec(
        composition_archetype="manual-review card: likely producer animal should be chosen before generation",
        key_traits="family name refers to eggs or trace fossils rather than a conventional animal family",
        habitat="manual review required",
        lighting="manual review required",
        palette="manual review required",
        mood="manual review required",
        confidence="low",
        review_note="Do not batch-generate this one without choosing whether to depict eggs, tracks, or a likely producer animal.",
    ),
    "fallback_ornithischia": GroupSpec(
        composition_archetype="generic ornithischian card: medium beaked herbivore in clean full-body 3/4 stance",
        key_traits="beaked herbivore head, sturdy body, strong hind limbs, balancing tail, clear herbivore silhouette without narrow family-specific traits",
        habitat="open fern plain or woodland edge with low plants and distant trees",
        lighting="bright diffuse daylight",
        palette="olive, tan, bark brown, sage green, and pale sky blue",
        mood="generic, stable, and atlas-friendly",
        confidence="medium",
    ),
    "fallback_saurischia": GroupSpec(
        composition_archetype="generic saurischian card: classic bipedal dinosaur in clean 3/4 stance with long tail and grasping arms",
        key_traits="bipedal saurischian body, long tail, strong hind legs, saurischian pelvis cues, predatory or omnivorous silhouette without narrow family-specific traits",
        habitat="open floodplain with sparse conifers and broad sky",
        lighting="warm daylight",
        palette="taupe, charcoal, muted olive, rust brown, and pale sky blue",
        mood="generic, energetic, and neutral",
        confidence="medium",
    ),
    "fallback_reptilia": GroupSpec(
        composition_archetype="manual-review fallback card for non-dinosaur reptilian records",
        key_traits="this taxon bucket is broader than Dinosauria and should be reviewed before depicting a specific animal type",
        habitat="manual review required",
        lighting="manual review required",
        palette="manual review required",
        mood="manual review required",
        confidence="low",
        review_note="This is not a clean dinosaur-family prompt target; review the specific underlying species before generation.",
    ),
}


FAMILY_TO_GROUP: dict[str, str] = {
    "Abelisauridae": "abelisaurid_predator",
    "Allosauridae": "large_theropod_predator",
    "Carcharodontosauridae": "large_theropod_predator",
    "Megalosauridae": "large_theropod_predator",
    "Metriacanthosauridae": "large_theropod_predator",
    "Neovenatoridae": "large_theropod_predator",
    "Piatnitzkysauridae": "large_theropod_predator",
    "Ceratosauridae": "ceratosaur_predator",
    "Noasauridae": "ceratosaur_predator",
    "Coelophysidae": "basal_theropod_predator",
    "Compsognathidae": "basal_theropod_predator",
    "Dilophosauridae": "basal_theropod_predator",
    "Herrerasauridae": "basal_theropod_predator",
    "Tyrannosauridae": "tyrannosauroid_predator",
    "Proceratosauridae": "tyrannosauroid_predator",
    "Spinosauridae": "spinosaurid_predator",
    "Megaraptoridae": "megaraptor_predator",
    "Dromaeosauridae": "dromaeosaur_predator",
    "Troodontidae": "troodontid_predator",
    "Anchiornithidae": "feathered_glider",
    "Archaeopterygidae": "feathered_glider",
    "Scansoriopterygidae": "feathered_glider",
    "Alvarezsauridae": "alvarezsaur_runner",
    "Nqwebasauridae": "alvarezsaur_runner",
    "Avimimidae": "oviraptor_beaked",
    "Caenagnathidae": "oviraptor_beaked",
    "Caudipterygidae": "oviraptor_beaked",
    "Oviraptoridae": "oviraptor_beaked",
    "Ornithomimidae": "ornithomimosaur_runner",
    "Deinocheiridae": "deinocheirid_giant",
    "Therizinosauridae": "therizinosaur_browser",
    "Anchisauridae": "basal_sauropodomorph",
    "Guaibasauridae": "basal_sauropodomorph",
    "Lessemsauridae": "basal_sauropodomorph",
    "Massospondylidae": "basal_sauropodomorph",
    "Melanorosauridae": "basal_sauropodomorph",
    "Plateosauridae": "basal_sauropodomorph",
    "Riojasauridae": "basal_sauropodomorph",
    "Saturnaliidae": "basal_sauropodomorph",
    "Unaysauridae": "basal_sauropodomorph",
    "Vulcanodontidae": "early_sauropod",
    "Brachiosauridae": "sauropod_high_browser",
    "Euhelopodidae": "sauropod_high_browser",
    "Cetiosauridae": "sauropod_long_neck",
    "Mamenchisauridae": "sauropod_long_neck",
    "Dicraeosauridae": "sauropod_whiptail",
    "Diplodocidae": "sauropod_whiptail",
    "Rebbachisauridae": "sauropod_whiptail",
    "Balochisauridae": "sauropod_robust",
    "Camarasauridae": "sauropod_robust",
    "Gspsauridae": "sauropod_robust",
    "Nemegtosauridae": "sauropod_robust",
    "Pakisauridae": "sauropod_robust",
    "Saltasauridae": "sauropod_robust",
    "Vitakrisauridae": "sauropod_robust",
    "Ankylosauridae": "armored_ankylosaur",
    "Nodosauridae": "armored_nodosaur",
    "Scelidosauridae": "armored_nodosaur",
    "Huayangosauridae": "stegosaur_plated",
    "Stegosauridae": "stegosaur_plated",
    "Ceratopsidae": "ceratopsian_horned",
    "Chaoyangsauridae": "ceratopsian_small",
    "Leptoceratopsidae": "ceratopsian_small",
    "Protoceratopsidae": "ceratopsian_small",
    "Psittacosauridae": "psittacosaur_beaked",
    "Hadrosauridae": "hadrosaur_duckbill",
    "Iguanodontidae": "iguanodont_ornithopod",
    "Tenontosauridae": "iguanodont_ornithopod",
    "Dryosauridae": "small_ornithopod",
    "Fabrosauridae": "small_ornithopod",
    "Hypsilophodontidae": "small_ornithopod",
    "Jeholosauridae": "small_ornithopod",
    "Parksosauridae": "small_ornithopod",
    "Rhabdodontidae": "small_ornithopod",
    "Thescelosauridae": "small_ornithopod",
    "Heterodontosauridae": "heterodontosaur_small",
    "Pachycephalosauridae": "pachycephalosaur_dome",
    "Alethoalaornithidae": "early_bird_perching",
    "Alexornithidae": "early_bird_perching",
    "Avisauridae": "early_bird_perching",
    "Bohaiornithidae": "early_bird_perching",
    "Cathayornithidae": "early_bird_perching",
    "Enantiornithidae": "early_bird_perching",
    "Eoenantiornithidae": "early_bird_perching",
    "Hongshanornithidae": "early_bird_perching",
    "Pengornithidae": "early_bird_perching",
    "Longipterygidae": "shoreline_bird",
    "Schizoouridae": "shoreline_bird",
    "Yanornithidae": "shoreline_bird",
    "Baptornithidae": "diving_bird",
    "Brodavidae": "diving_bird",
    "Colymbidae": "diving_bird",
    "Hesperornithidae": "diving_bird",
    "Cracidae": "ground_bird",
    "Gallinuloididae": "ground_bird",
    "Megapodiidae": "ground_bird",
    "Meleagridae": "ground_bird",
    "Numididae": "ground_bird",
    "Odontophoridae": "ground_bird",
    "Paraortygidae": "ground_bird",
    "Phasianidae": "ground_bird",
    "Quercymegapodiidae": "ground_bird",
    "Tetraonidae": "ground_bird",
    "Waltonortygidae": "ground_bird",
    "Gargantuaviidae": "large_flightless_bird",
    "Laevisoolithidae": "ootaxon_review",
    "Ornithomimipodidae": "ootaxon_review",
}


EXTANT_BIRD_ORDERS = {
    "Galliformes": "ground_bird",
    "Colymbiformes": "diving_bird",
    "Hesperornithiformes": "diving_bird",
    "Cathayornithiformes": "early_bird_perching",
    "Alexornithiformes": "early_bird_perching",
    "Eoenantiornithiformes": "early_bird_perching",
    "Yanornithiformes": "shoreline_bird",
}


def load_manifest() -> list[dict[str, str]]:
    with MANIFEST_PATH.open() as handle:
        return list(csv.DictReader(handle))


def load_family_context() -> dict[str, dict[str, str]]:
    data = json.loads(DATABASE_PATH.read_text())
    species = data["species"]
    by_family: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in species:
        family = row.get("family")
        if family:
            by_family[str(family)].append(row)

    context: dict[str, dict[str, str]] = {}
    for family, rows in by_family.items():
        major_clade = Counter(
            str(row.get("majorClade")) for row in rows if row.get("majorClade")
        ).most_common(1)
        order = Counter(str(row.get("order")) for row in rows if row.get("order")).most_common(1)
        genus = Counter(str(row.get("genus")) for row in rows if row.get("genus")).most_common(3)
        context[family] = {
            "major_clade": major_clade[0][0] if major_clade else "",
            "dominant_order": order[0][0] if order else "",
            "representative_genus": ", ".join(genus_name for genus_name, _ in genus),
        }
    return context


def infer_group(row: dict[str, str], context: dict[str, str]) -> str:
    taxon = row["taxon"]
    if row["level"] == "major_clade":
        return f"fallback_{taxon.lower()}"

    if taxon in FAMILY_TO_GROUP:
        return FAMILY_TO_GROUP[taxon]

    dominant_order = context.get("dominant_order", "")
    if dominant_order in EXTANT_BIRD_ORDERS:
        return EXTANT_BIRD_ORDERS[dominant_order]

    major_clade = context.get("major_clade", "")
    if major_clade == "Ornithischia":
        return "small_ornithopod"
    if major_clade == "Saurischia":
        return "large_theropod_predator"
    return "fallback_reptilia"


def review_status_for(group_id: str, row: dict[str, str]) -> str:
    if group_id in {"ootaxon_review", "fallback_reptilia"}:
        return "manual_review_required"
    if GROUP_SPECS[group_id].confidence == "low":
        return "needs_scientific_review"
    if int(row["species_count"] or "0") <= 2:
        return "needs_light_review"
    return "draft_ready"


def review_notes_for(group_id: str, row: dict[str, str], context: dict[str, str]) -> str:
    notes: list[str] = []
    spec = GROUP_SPECS[group_id]
    if spec.review_note:
        notes.append(spec.review_note)
    if not context.get("representative_genus"):
        notes.append("No representative genus found in the current atlas export.")
    if int(row["species_count"] or "0") <= 2:
        notes.append("Low species count; choose a representative body plan carefully.")
    if row.get("notes"):
        notes.append(row["notes"])
    return " ".join(notes).strip()


def build_prompt(row: dict[str, str], context: dict[str, str], group_id: str) -> str:
    spec = GROUP_SPECS[group_id]
    taxon = row["taxon"]
    level = row["level"].replace("_", " ")
    return (
        f"Create a square illustrated dinosaur family card for {taxon}, a {level} from the Dinosaur Atlas project. "
        f"Show one featured adult animal as the clear focal subject using {spec.composition_archetype}. "
        f"Emphasize the defining anatomy: {spec.key_traits}. The animal must read instantly at thumbnail size. "
        f"Visual style: premium natural-history illustration card, crisp black linework, soft cel-shaded color, subtle grain texture, muted realistic palette, museum-compendium aesthetic, simplified but believable prehistoric habitat, polished digital illustration rather than photoreal painting. "
        f"Environment: {spec.habitat}. Lighting: {spec.lighting}. Color direction: {spec.palette}. Mood: {spec.mood}. "
        f"Layout constraints: square composition, rounded card border area, reserved blank title band at the bottom for later typography, optional reserved badge space in the lower-right corner, no rendered text, no logo, no watermark."
    )


def build_rows() -> list[dict[str, str]]:
    manifest_rows = load_manifest()
    family_context = load_family_context()
    output_rows: list[dict[str, str]] = []
    for row in manifest_rows:
        taxon = row["taxon"]
        context = family_context.get(taxon, {})
        group_id = infer_group(row, context)
        spec = GROUP_SPECS[group_id]
        output_rows.append(
            {
                "image_id": row["image_id"],
                "level": row["level"],
                "taxon": taxon,
                "species_count": row["species_count"],
                "major_clade": context.get("major_clade", taxon if row["level"] == "major_clade" else ""),
                "dominant_order": context.get("dominant_order", ""),
                "representative_genus": context.get("representative_genus", ""),
                "prompt_group": group_id,
                "composition_archetype": spec.composition_archetype,
                "key_traits": spec.key_traits,
                "habitat": spec.habitat,
                "lighting": spec.lighting,
                "palette": spec.palette,
                "mood": spec.mood,
                "confidence": spec.confidence,
                "review_status": review_status_for(group_id, row),
                "review_notes": review_notes_for(group_id, row, context),
                "draft_prompt": build_prompt(row, context, group_id),
            }
        )
    return output_rows


def write_csv(rows: list[dict[str, str]]) -> None:
    fieldnames = list(rows[0].keys())
    with OUTPUT_CSV_PATH.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_summary(rows: list[dict[str, str]]) -> None:
    group_counts = Counter(row["prompt_group"] for row in rows)
    review_counts = Counter(row["review_status"] for row in rows)
    flagged = [row for row in rows if row["review_status"] != "draft_ready"]

    lines = [
        "# Family Card Prompt Plan",
        "",
        f"- Rows generated: `{len(rows)}`",
        f"- Draft-ready prompts: `{review_counts.get('draft_ready', 0)}`",
        f"- Needs light review: `{review_counts.get('needs_light_review', 0)}`",
        f"- Needs scientific review: `{review_counts.get('needs_scientific_review', 0)}`",
        f"- Manual review required: `{review_counts.get('manual_review_required', 0)}`",
        "",
        "## Prompt groups",
        "",
    ]

    for group_id, count in sorted(group_counts.items()):
        lines.append(f"- `{group_id}`: `{count}`")

    lines.extend(["", "## Flagged rows", ""])
    for row in flagged:
        lines.append(
            f"- `{row['taxon']}` (`{row['image_id']}`): {row['review_status']}"
            + (f" — {row['review_notes']}" if row["review_notes"] else "")
        )

    OUTPUT_SUMMARY_PATH.write_text("\n".join(lines) + "\n")


def main() -> None:
    rows = build_rows()
    write_csv(rows)
    write_summary(rows)
    print(f"Wrote {len(rows)} rows to {OUTPUT_CSV_PATH}")
    print(f"Wrote summary to {OUTPUT_SUMMARY_PATH}")


if __name__ == "__main__":
    main()
