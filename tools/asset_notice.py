"""Document generated visual-asset provenance; does not transform any image."""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[1]
assets=sorted([*(ROOT/'src/web/world-art').glob('*-1.0.3.png'),ROOT/'src/web/atelier-mark-1.0.3.png',*(ROOT/'src/sprout/web/pip').glob('companion-*-1.0.3.png')])
generated={'atelier-mark','obsidian','glacier','rose','bloom','linen','matcha','midnight','peach','forest','tidal','ember','celestial','castle','underworld','mythic','cabin','sunset-beach'}
companions={'companion-cutesy','companion-green','companion-water','companion-orbit','companion-ember','companion-linen'}
def origin(p):
    stem=p.stem.removesuffix('-1.0.3')
    if stem in generated:return 'OpenAI image generation, this implementation session; original local output copied without modification'
    if stem in companions:return 'OpenAI image generation, this implementation session; locally normalized and composition-cropped to a 512 px application portrait'
    return 'Deterministic local rasterization of the bundled authored SVG; no external request'
records=[{'file':p.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size,'origin':origin(p)} for p in assets]
(ROOT/'ASSET-PROVENANCE-1.0.3.json').write_text(json.dumps(records,indent=2)+'\n',newline='\n')
(ROOT/'ASSET-PROVENANCE-1.0.3.md').write_text('''# Atelier 1.0.3 visual asset provenance

Atelier ships seventeen local world plates (`obsidian`, `glacier`, `rose`, `bloom`, `linen`, `matcha`, `midnight`, `peach`, `forest`, `tidal`, `ember`, `celestial`, `castle`, `underworld`, `mythic`, `cabin`, and `sunset-beach`). They are scenery generated through OpenAI image generation during the implementation session and copied from local output without image modification. All are scenery, never application screenshots or evidence. No user source image, mask original, logo, font, or third-party screenshot was used to create them.

The local `atelier-mark-1.0.3.png` is a separately generated transparent brand emblem. It replaces the generic circled-letter placeholder in the shipped navigation and loading state. The unpublished information page carries an exact copy.

Six local companion portraits give the world families distinct characters: a moon-crowned cat for cutesy worlds, leaf-cloaked Pip for green worlds, a pearl-wearing tide otter, constellation owl, ember fox, and folded-paper crane. They were generated through OpenAI image generation during the implementation session, then locally normalized and cropped to 512×512 application portraits. They contain no interface controls, evidence, user media, or third-party characters. The shared progress model, study actions, saved settings, and tiny native reviewer animation remain unchanged.

Art direction: original, calm 16:9 landscapes with atmospheric depth, quiet central space, and more detail at the bottom and edges. Prompts and SVG source expressly exclude interface panels, controls, labels, devices, promotional layouts, and text.

Original SVG landscapes remain byte-identical to 1.0.2 as compatibility fallbacks. Existing licenses and notices are retained. The supplied promotional reference remains an art-direction document, not a claim of shipped functionality. Generated asset provenance does not establish exclusive copyright or trademark clearance; public marketing questions belong in the professional review record.

Exact file sizes, SHA-256 hashes, and per-file origin are recorded in `ASSET-PROVENANCE-1.0.3.json`. Actual UI captures are produced separately by browser and native Anki capture tools.
'''.replace('\r\n','\n'),encoding='utf8',newline='\n')
