"""Document landscape provenance; does not transform any image."""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[1]
assets=sorted((ROOT/'src/web/world-art').glob('*-1.0.3.png'))
generated={'obsidian','glacier','rose','bloom','linen','matcha','midnight','peach','forest','tidal','ember','celestial'}
records=[{'file':p.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size,'origin':'OpenAI image generation, this implementation session; original local output copied without modification' if p.stem.removesuffix('-1.0.3') in generated else 'Deterministic local rasterization of the bundled authored SVG; no external request'} for p in assets]
(ROOT/'ASSET-PROVENANCE-1.0.3.json').write_text(json.dumps(records,indent=2)+'\n')
(ROOT/'ASSET-PROVENANCE-1.0.3.md').write_text('''# Atelier 1.0.3 landscape provenance

Atelier ships seventeen local world plates. Twelve inherited plates (`obsidian`, `glacier`, `rose`, `bloom`, `linen`, `matcha`, `midnight`, `peach`, `forest`, `tidal`, `ember`, and `celestial`) are scenery generated through OpenAI image generation during the implementation session and copied from local output without image modification. Five new plates (`castle`, `underworld`, `mythic`, `cabin`, and `sunset`) are authored SVG scenes rasterized deterministically by `tools/rasterize_new_worlds.py`. All are scenery, never application screenshots or evidence. No user source image, mask original, logo, font, or third-party screenshot was used to create them.

Art direction: original, calm 16:9 landscapes with atmospheric depth, quiet central space, and more detail at the bottom and edges. Prompts and SVG source expressly exclude interface panels, controls, labels, devices, promotional layouts, and text. The five authored additions cover a moonlit keep, ember gate, oracle engine, quiet cabin, and golden shore while retaining the existing twelve worlds.

Original SVG landscapes remain byte-identical to 1.0.2 as compatibility fallbacks. Existing licenses and notices are retained. The supplied promotional reference remains an art-direction document, not a claim of shipped functionality. Generated asset provenance does not establish exclusive copyright or trademark clearance; public marketing questions belong in the professional review record.

Exact file sizes, SHA-256 hashes, and per-file origin are recorded in `ASSET-PROVENANCE-1.0.3.json`. Actual UI captures are produced separately by browser and native Anki capture tools.
''',encoding='utf8')
