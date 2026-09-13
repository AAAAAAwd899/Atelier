"""Document landscape provenance; does not transform any image."""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[1]
assets=sorted((ROOT/'src/web/world-art').glob('*-1.0.3.png'))
records=[{'file':p.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size,'origin':'OpenAI image generation, this implementation session; original local output copied without modification'} for p in assets]
(ROOT/'ASSET-PROVENANCE-1.0.3.json').write_text(json.dumps(records,indent=2)+'\n')
(ROOT/'ASSET-PROVENANCE-1.0.3.md').write_text('''# Atelier 1.0.3 landscape provenance

The twelve `src/web/world-art/*-1.0.3.png` files are AI-generated landscape assets created in this implementation session through OpenAI image generation. They are scenery, not application screenshots or evidence. They were copied from the generated local outputs without image modification. No user source image, mask original, logo, font or third-party screenshot was used to create them.

Art direction: original, calm 16:9 landscapes with atmospheric depth, quiet central space and more detail at the bottom and edges. Prompts expressly excluded interface panels, controls, labels, devices, promotional layouts and text. Each asset follows the existing stored world: amethyst mountains (Obsidian), alpine ice (Glacier), rose garden (Rose), botanical glasshouse (Bloom), warm courtyard reading room (Linen), tea pavilion (Matcha), night mountains (Midnight), terracotta sunset (Peach), evergreen lake (Forest), sea-glass coast (Tidal), copper highlands (Ember), and starry observatory (Celestial).

Original SVG landscapes remain byte-identical to 1.0.2 as compatibility fallbacks. Existing licenses and notices are retained. The supplied promotional reference remains an art-direction document, not a claim of shipped functionality. Generated asset provenance does not establish exclusive copyright or trademark clearance; public marketing questions belong in the professional review record.

Exact file sizes and SHA-256 hashes are recorded in `ASSET-PROVENANCE-1.0.3.json`. Actual UI captures are produced separately by browser and native Anki capture tools.
''',encoding='utf8')
