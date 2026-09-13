"""Disposable, profile-local in-memory image previews. Never changes source/media blobs.

QImageReader/QPdfDocument are created and destroyed by each worker. No QPixmap,
widget or shared Qt document crosses a worker boundary. Only bytes/dicts are cached.
"""
from __future__ import annotations
from collections import OrderedDict
from copy import deepcopy
from threading import RLock
from base64 import b64encode
import json


class PreviewCache:
    def __init__(self, max_bytes=48*1024*1024, max_entries=64):
        self.max_bytes, self.max_entries = max_bytes, max_entries
        self._items = OrderedDict()
        self._lock = RLock()
        self.bytes = self.hits = self.misses = 0
        self.generation = 0

    def clear(self):
        with self._lock:
            self._items.clear(); self.bytes=0; self.generation+=1

    def get_or_create(self, key, build):
        # Serializes preview work only, NOT collection or UI actions. Simultaneous
        # requests for the same page decode it once; failed builds are not cached.
        with self._lock:
            if key in self._items:
                self.hits+=1
                value,size=self._items.pop(key);self._items[key]=(value,size)
                return deepcopy(value)
            self.misses+=1
            value=build()
            size=len(json.dumps(value,ensure_ascii=False).encode('utf8'))
            if size<=self.max_bytes:
                while self._items and (self.bytes+size>self.max_bytes or len(self._items)>=self.max_entries):
                    _,(_,old)=self._items.popitem(last=False);self.bytes-=old
                self._items[key]=(deepcopy(value),size);self.bytes+=size
            return value

    def diagnostics(self):
        with self._lock:
            return {'cached_items':len(self._items),'encoded_bytes':self.bytes,
                    'byte_limit':self.max_bytes,'hits':self.hits,'misses':self.misses}


class FigurePreviews:
    def __init__(self, store):
        self.store=store;self.cache=PreviewCache()

    def page(self, version_id, page, width=1600):
        from .workshop import documents
        from .workshop.core import integer
        v=self.store.get('version',version_id)
        page=integer(page,1,len(v['pages']),'Page');width=integer(width,320,2200,'Image width')
        record=v['pages'][page-1]
        # Source revision invalidates even when a PDF layout is attached to the
        # SAME version id. Never key by title or page number alone.
        key=('page',version_id,v.get('revision'),v.get('updated'),width,page,
             v.get('metadata',{}).get('visual_pdf',''),v.get('blob',''),record.get('image',''))
        def build():
            out=documents._render_page(self.store,version_id,page,width)
            out.update(notes=record.get('notes',''),hidden_slide=bool(record.get('hidden_slide',False)),
                       asset_count=len(record.get('assets',[])),
                       assets=[{**a,'image':'','preview_pending':True} for a in record.get('assets',[])[:40]])
            return out
        return self.cache.get_or_create(key,build)

    def image(self, blob, width=None):
        from .workshop import documents
        from .workshop.core import integer
        p=self.store.blob_path(blob)  # original path allowlist / existence checks
        if width is not None:width=integer(width,160,1000,'Preview width')
        stat=p.stat();key=('image',blob,stat.st_size,stat.st_mtime_ns,width)
        def build():
            if width is not None:
                try:
                    from PyQt6.QtGui import QImageReader
                    from PyQt6.QtCore import QSize,QByteArray,QBuffer,QIODevice
                    reader=QImageReader(str(p))
                    size=reader.size()
                    if size.width()>0 and size.height()>0 and not reader.supportsAnimation():
                        # Preview only. Masks/attachments always request width=None.
                        ratio=min(1.,width/size.width(),1000/size.height())
                        reader.setScaledSize(QSize(max(1,round(size.width()*ratio)),max(1,round(size.height()*ratio))))
                        image=reader.read()
                        if not image.isNull():
                            data=QByteArray();buffer=QBuffer(data)
                            buffer.open(QIODevice.OpenModeFlag.WriteOnly)
                            try:
                                if image.save(buffer,'PNG'):
                                    return {'image':'data:image/png;base64,'+b64encode(bytes(data)).decode(),
                                            'preview':True,'width':image.width(),'height':image.height()}
                            finally:buffer.close()
                except ImportError:
                    pass  # same full-fidelity fallback as the original renderer
            return {'image':documents.data_url(p),'preview':False}
        return self.cache.get_or_create(key,build)
