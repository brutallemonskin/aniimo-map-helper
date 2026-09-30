import base64, json, threading, urllib.parse, webbrowser, sys, os
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
import cv2, numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent))
from matcher import Matcher
from overlay_bridge import OverlayBridge

ROOT=Path(__file__).resolve().parent
PORT=int(os.environ.get('ANIIMO_PORT','18731'))
matcher=Matcher()
overlay=OverlayBridge(ROOT)

class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*a,**kw): super().__init__(*a,directory=str(ROOT),**kw)
    def log_message(self,*a): pass
    def json(self,obj,status=200):
        b=json.dumps(obj,ensure_ascii=False).encode(); self.send_response(status)
        self.send_header('Content-Type','application/json; charset=utf-8'); self.send_header('Content-Length',str(len(b)));self.end_headers();self.wfile.write(b)
    def do_GET(self):
        path=urllib.parse.urlparse(self.path).path
        if path=='/api/status': return self.json({'ready':matcher.ready,'indexed':len(matcher.maps),'error':matcher.error,'version':'overlay-v1'})
        if path=='/api/overlay': return self.json(overlay.status())
        if path=='/api/overlay/frame': return self.json(overlay.snapshot())
        if path=='/': self.path='/index.html'
        elif path not in ('/index.html','/app.js','/style.css') and not (path.startswith('/data/') and '..' not in urllib.parse.unquote(path)):
            return self.send_error(404)
        return super().do_GET()
    def do_POST(self):
        origin=self.headers.get('Origin','')
        if origin not in ('',f'http://127.0.0.1:{PORT}',f'http://localhost:{PORT}'):
            return self.json({'error':'Origin rejected'},403)
        if self.path=='/api/shutdown':
            overlay.stop()
            self.json({'stopped':True})
            threading.Thread(target=self.server.shutdown,daemon=True).start()
            return
        if self.path in ('/api/overlay','/api/overlay/frame'):
            try:
                n=int(self.headers.get('Content-Length','0'))
                if not 0<n<4_000_000: return self.json({'error':'无效悬浮窗数据'},413)
                payload=json.loads(self.rfile.read(n))
                if self.path=='/api/overlay/frame': return self.json(overlay.publish(payload))
                if payload.get('action')=='start': return self.json(overlay.start())
                if payload.get('action')=='stop': return self.json(overlay.stop())
                return self.json({'error':'无效悬浮窗操作'},400)
            except Exception as e: return self.json({'error':str(e)},400)
        if self.path!='/api/match': return self.send_error(404)
        try:
            n=int(self.headers.get('Content-Length','0'))
            if not 0<n<12_000_000: return self.json({'error':'图片过大'},413)
            d=json.loads(self.rfile.read(n)); raw=base64.b64decode(d['image'].split(',')[-1],validate=True)
            im=cv2.imdecode(np.frombuffer(raw,np.uint8),cv2.IMREAD_COLOR)
            if im is None or max(im.shape[:2])>5000: raise ValueError('无效图片或图片过大')
            anchor=d.get('anchor')
            if anchor is not None and (len(anchor)!=2 or not all(isinstance(v,(int,float)) and 0<=v<=1 for v in anchor)): raise ValueError('无效位置')
            tracking=d.get('tracking')
            if tracking is not None:
                import re,math
                if not isinstance(tracking,dict) or not re.fullmatch(r'(?:sanctum-[a-z0-9-]+|egg-heist(?:-team-mode)?)',str(tracking.get('id',''))):raise ValueError('无效追踪地图')
                p=tracking.get('position')
                if not isinstance(p,list) or len(p)!=2 or not all(isinstance(v,(int,float)) and math.isfinite(v) and 0<=v<=10000 for v in p):raise ValueError('无效追踪位置')
                s=tracking.get('scale')
                if s is not None and (not isinstance(s,(int,float)) or not math.isfinite(s) or not .3<=s<=3):raise ValueError('无效小地图比例')
            outdoor_mode=d.get('outdoor_mode','egg-heist')
            if outdoor_mode not in ('egg-heist','egg-heist-team-mode'):raise ValueError('无效海岛模式')
            answer=matcher.match(im,anchor,tracking,outdoor_mode)
            self.json(answer)
        except Exception as e: self.json({'error':str(e)},400)

if __name__=='__main__':
    ThreadingHTTPServer.allow_reuse_address=False
    try: server=ThreadingHTTPServer(('127.0.0.1',PORT),Handler)
    except OSError:
        print('Port 18731 is already in use. Existing assistant may be running.');sys.exit(1)
    (ROOT/'server.pid').write_text(str(__import__('os').getpid()))
    threading.Thread(target=matcher.build,daemon=True).start()
    print(f'Local map helper: http://127.0.0.1:{PORT}',flush=True)
    if '--no-browser' not in sys.argv: webbrowser.open(f'http://127.0.0.1:{PORT}')
    try: server.serve_forever()
    finally:
        overlay.stop()
        server.server_close()
