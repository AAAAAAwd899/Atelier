# Atelier 1.0.3 landscape provenance

Atelier ships seventeen local world plates. Twelve inherited plates (`obsidian`, `glacier`, `rose`, `bloom`, `linen`, `matcha`, `midnight`, `peach`, `forest`, `tidal`, `ember`, and `celestial`) are scenery generated through OpenAI image generation during the implementation session and copied from local output without image modification. Five new plates (`castle`, `underworld`, `mythic`, `cabin`, and `sunset`) are authored SVG scenes rasterized deterministically by `tools/rasterize_new_worlds.py`. All are scenery, never application screenshots or evidence. No user source image, mask original, logo, font, or third-party screenshot was used to create them.

Art direction: original, calm 16:9 landscapes with atmospheric depth, quiet central space, and more detail at the bottom and edges. Prompts and SVG source expressly exclude interface panels, controls, labels, devices, promotional layouts, and text. The five authored additions cover a moonlit keep, ember gate, oracle engine, quiet cabin, and golden shore while retaining the existing twelve worlds.

Original SVG landscapes remain byte-identical to 1.0.2 as compatibility fallbacks. Existing licenses and notices are retained. The supplied promotional reference remains an art-direction document, not a claim of shipped functionality. Generated asset provenance does not establish exclusive copyright or trademark clearance; public marketing questions belong in the professional review record.

Exact file sizes, SHA-256 hashes, and per-file origin are recorded in `ASSET-PROVENANCE-1.0.3.json`. Actual UI captures are produced separately by browser and native Anki capture tools.
