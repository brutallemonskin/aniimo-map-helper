"""Local, in-memory bridge between the browser renderer and the desktop overlay."""
import base64
import io
import subprocess
import sys
import threading
import time
from pathlib import Path
from PIL import Image


class OverlayBridge:
    def __init__(self, root):
        self.root = Path(root)
        self.lock = threading.RLock()
        self.process = None
        self.image = None
        self.title = '等待识别地宫'
        self.language = 'zh-CN'
        self.updated = 0
        self.version = 0

    def status(self):
        with self.lock:
            return {'enabled': self.process is not None and self.process.poll() is None,
                    'title': self.title, 'language': self.language, 'updated': self.updated, 'version': self.version}

    def start(self):
        with self.lock:
            if self.status()['enabled']:
                return self.status()
            if sys.platform != 'win32':
                raise ValueError('悬浮窗需要 Windows')
            self.image = None
            self.title = '等待识别地宫'
            self.updated = 0
            self.version += 1
            with (self.root / 'overlay.log').open('ab') as log:
                self.process = subprocess.Popen(
                    [sys.executable, '-X', 'utf8', str(self.root / 'overlay_window.py')],
                    cwd=self.root, stdout=log, stderr=log,
                    creationflags=subprocess.CREATE_NO_WINDOW)
            return self.status()

    def stop(self):
        with self.lock:
            if self.status()['enabled']:
                self.process.terminate()
                self.process.wait(timeout=3)
            self.process = None
            self.image = None
            self.updated = 0
            return self.status()

    def publish(self, payload):
        # Validate and decode before replacing the last usable frame.
        title = payload.get('title', '等待识别地宫')
        if not isinstance(title, str) or len(title) > 120:
            raise ValueError('无效悬浮窗标题')
        raw = None
        if payload.get('image'):
            raw = base64.b64decode(payload['image'].split(',')[-1], validate=True)
            with Image.open(io.BytesIO(raw)) as im:
                if im.format != 'PNG' or not (1 <= im.width <= 960 and 1 <= im.height <= 960):
                    raise ValueError('无效悬浮窗地图尺寸')
                im.load()
        with self.lock:
            if self.status()['enabled']:
                self.image = raw
                self.title = title
                self.language = 'en' if payload.get('language') == 'en' else 'zh-CN'
                self.updated = time.time()
                self.version += 1
            return self.status()

    def snapshot(self):
        with self.lock:
            return {**self.status(), 'image': base64.b64encode(self.image).decode() if self.image else None}
