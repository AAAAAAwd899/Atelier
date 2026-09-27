"""Serve shipped world artwork to local browser captures at Anki's asset URLs."""
from pathlib import Path
from urllib.parse import unquote, urlparse
import json

ROOT = Path(__file__).resolve().parents[1]
SCENES = {world['id']: world.get('scene') for world in json.loads((ROOT/'src/web/worlds.json').read_text(encoding='utf8'))}

def with_artwork_base(html: str) -> str:
    if '<base ' in html:
        return html
    return html.replace('<head>', '<head><base href="http://atelier.test/">', 1)

def install_artwork_route(page) -> None:
    def serve(route):
        name = Path(unquote(urlparse(route.request.url).path)).name
        file = ROOT / 'src' / 'web' / 'world-art' / name
        if file.is_file() and file.suffix == '.png':
            route.fulfill(path=str(file), content_type='image/png')
        else:
            route.abort()
    page.route('**/_addons/daedalus_atelier/web/world-art/*.png', serve)

def wait_for_world_art(page, world: str) -> None:
    scene = SCENES.get(world)
    if not scene:
        return
    loaded = page.evaluate('''async path => {
        const image = new Image();
        image.src = '/_addons/daedalus_atelier/web/' + path;
        await image.decode();
        return image.naturalWidth > 1000;
    }''', scene)
    if not loaded:
        raise AssertionError(f'World artwork did not load: {world}')
