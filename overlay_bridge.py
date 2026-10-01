"""Local, in-memory bridge between the browser renderer and the desktop overlay."""
import base64
import io
import subprocess
import sys
import threading
import time
import math
import copy
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
        self.map_key = ''
        self.player = None
        self.navigation = None

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
            self.map_key = ''
            self.player = None
            self.navigation = None
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
            self.map_key = ''
            self.player = None
            self.updated = 0
            return self.status()

    def publish(self, payload):
        # Validate and decode before replacing the last usable frame.
        title = payload.get('title', '等待识别地宫')
        if not isinstance(title, str) or len(title) > 120:
            raise ValueError('无效悬浮窗标题')
        raw = None
        key=payload.get('map_key','legacy-'+str(self.version+1))
        if not isinstance(key,str) or not 1<=len(key)<=120:raise ValueError('无效地图版本')
        player=payload.get('player')
        def coord(v):return type(v) in (int,float) and math.isfinite(v) and -4<=v<=5
        navigation=payload.get('navigation')
        if navigation is not None:
            if not isinstance(navigation,dict) or type(navigation.get('held')) is not bool:raise ValueError('无效导航标记')
            for field,limit in (('trail',600),('path',4096),('stops',32)):
                points=navigation.get(field,[])
                if not isinstance(points,list) or len(points)>limit:raise ValueError('导航轨迹过大')
                for p in points:
                    if p is None and field=='trail':continue
                    if not isinstance(p,list) or len(p)!=2 or not all(coord(v) for v in p):raise ValueError('无效导航坐标')
            target=navigation.get('target')
            if target is not None and (not isinstance(target,list) or len(target)!=2 or not all(coord(v) for v in target)):raise ValueError('无效导航目标')
        if player is not None:
            def coord(v):return type(v) in (int,float) and math.isfinite(v) and -4<=v<=5
            if not isinstance(player,dict) or not coord(player.get('x')) or not coord(player.get('y')):raise ValueError('无效人物位置')
            if type(player.get('held')) is not bool or not isinstance(player.get('label'),str) or len(player['label'])>24:raise ValueError('无效人物标记')
            poly=player.get('polygon',[])
            if not isinstance(poly,list) or len(poly)>8 or any(not isinstance(p,list) or len(p)!=2 or not all(coord(v) for v in p) for p in poly):raise ValueError('无效定位范围')
        if payload.get('image'):
            raw = base64.b64decode(payload['image'].split(',')[-1], validate=True)
            with Image.open(io.BytesIO(raw)) as im:
                if im.format != 'PNG' or not (1 <= im.width <= 2048 and 1 <= im.height <= 2048):
                    raise ValueError('无效悬浮窗地图尺寸')
                im.load()
        with self.lock:
            if self.status()['enabled']:
                if 'image' not in payload and (not self.image or key!=self.map_key):raise ValueError('请重新同步地图底图')
                if 'image' in payload:self.image = raw
                self.map_key = key
                self.player = copy.deepcopy(player) if self.image else None
                self.navigation = copy.deepcopy(navigation) if self.image else None
                self.title = title
                self.language = 'en' if payload.get('language') == 'en' else 'zh-CN'
                self.updated = time.time()
                self.version += 1
            return self.status()

    def snapshot(self, image_key=None):
        with self.lock:
            state={**self.status(),'map_key':self.map_key,'player':copy.deepcopy(self.player),'navigation':copy.deepcopy(self.navigation)}
            if image_key and image_key==self.map_key and self.image:
                state['image_unchanged']=True
            else:state['image']=base64.b64encode(self.image).decode() if self.image else None
            return state
