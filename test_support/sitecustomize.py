"""Portable test environment only; never included in the add-on installer."""
import os
try:
    from playwright.sync_api import BrowserType, Page
    from pathlib import Path
    import re
    _launch = BrowserType.launch
    def launch(self, *args, **kwargs):
        if kwargs.get('executable_path') == '/usr/bin/chromium':
            kwargs['executable_path'] = os.environ.get('ATELIER_TEST_BROWSER') or self.executable_path
        return _launch(self, *args, **kwargs)
    BrowserType.launch = launch
    _set_content=Page.set_content
    def set_content(self, html, *args, **kwargs):
        # Fixtures resolve the same local Anki media routes as the native host.
        # Large bitmaps must not be embedded in CSS custom properties: Chromium
        # rejects oversized variable values. No public server is contacted.
        root=Path(os.environ.get('ATELIER_FIXTURE_SRC',Path(__file__).resolve().parents[1]/'src'))/'web/world-art'
        def scene(route):
            name=route.request.url.rsplit('/',1)[-1]
            if re.fullmatch(r'[a-z0-9.-]+\.png',name) and (root/name).is_file():
                route.fulfill(path=str(root/name),content_type='image/png')
            else:route.abort()
        if 'atelier-asset-route.invalid' not in html:
            html=html.replace('<head>','<head><base href="http://atelier-asset-route.invalid/">',1)
        if not getattr(self,'_atelier_scene_route',False):
            self.route('http://atelier-asset-route.invalid/**/world-art/*.png',scene)
            self._atelier_scene_route=True
        return _set_content(self,html,*args,**kwargs)
    Page.set_content=set_content
except ImportError:
    pass
