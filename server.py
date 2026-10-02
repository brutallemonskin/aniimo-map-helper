import base64, json, threading, urllib.parse, webbrowser, sys, os, time
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
import cv2, numpy as np
import logging, logging.handlers, faulthandler
sys.path.insert(0,str(Path(__file__).resolve().parent))
from matcher import Matcher
from overlay_bridge import OverlayBridge
from route_planner import RoutePlanner
from native_capture import windows, small_preview
from capture_process import IsolatedCapture

ROOT=Path(__file__).resolve().parent
PORT=int(os.environ.get('ANIIMO_PORT','18731'))
matcher=Matcher()
overlay=OverlayBridge(ROOT)
route_planner=RoutePlanner(ROOT)
native=IsolatedCapture(ROOT)
match_slot=threading.Lock()
capture_log=logging.getLogger('aniimo.capture')
capture_log.addHandler(logging.NullHandler())

def enable_capture_diagnostics():
    # Local diagnostics only: no screenshots, window titles or session tokens.
    try:
        handler=logging.handlers.RotatingFileHandler(ROOT/'capture-error.log',maxBytes=262144,backupCount=1,encoding='utf-8')
        handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
        capture_log.addHandler(handler);capture_log.setLevel(logging.INFO)
        crash=ROOT/'capture-crash.log'
        if crash.exists() and crash.stat().st_size>262144:crash.replace(ROOT/'capture-crash.previous.log')
        output=crash.open('a',encoding='utf-8')
        faulthandler.enable(file=output,all_threads=True)
        return output  # Keep the descriptor alive for the entire service lifetime.
    except OSError:
        return None

class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*a,**kw): super().__init__(*a,directory=str(ROOT),**kw)
    def log_message(self,*a): pass
    def json(self,obj,status=200):
        b=json.dumps(obj,ensure_ascii=False).encode(); self.send_response(status)
        self.send_header('Content-Type','application/json; charset=utf-8'); self.send_header('Content-Length',str(len(b)));self.end_headers();self.wfile.write(b)
    def do_GET(self):
        path=urllib.parse.urlparse(self.path).path
        if path=='/api/status': return self.json({'ready':matcher.ready,'indexed':len(matcher.maps),'error':matcher.error,'version':'0.4.1'})
        if path=='/api/overlay': return self.json(overlay.status())
        if path=='/api/overlay/hotkeys': return self.json(overlay.status()['hotkeys'])
        if path=='/api/overlay/frame':
            query=urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            return self.json(overlay.snapshot(query.get('image_key',[None])[0]))
        if path=='/': self.path='/index.html'
        elif path not in ('/index.html','/app.js','/assist.js','/hotkey-settings.js','/style.css','/i18n.js') and not (path.startswith('/data/') and '..' not in urllib.parse.unquote(path)):
            return self.send_error(404)
        return super().do_GET()
    def do_POST(self):
        if self.headers.get('Host') not in (f'127.0.0.1:{self.server.server_port}',f'localhost:{self.server.server_port}'):return self.json({'error':'Host rejected'},403)
        origin=self.headers.get('Origin','')
        if origin not in ('',f'http://127.0.0.1:{PORT}',f'http://localhost:{PORT}'):
            return self.json({'error':'Origin rejected'},403)
        if self.path=='/api/shutdown':
            native.stop()
            overlay.stop()
            self.json({'stopped':True})
            threading.Thread(target=self.server.shutdown,daemon=True).start()
            return
        if self.path=='/api/native':
            try:
                n=int(self.headers.get('Content-Length','0'))
                if not 0<n<4096:raise ValueError('无效采集请求')
                d=json.loads(self.rfile.read(n));action=d.get('action')
                if action=='list':return self.json({'windows':windows()})
                if action=='stop':return self.json(native.stop(d.get('session','')))
                if action=='start':
                    interval=d.get('interval',500)
                    if type(interval) is not int or interval not in (250,500,1000,2000,3000):raise ValueError('无效间隔')
                    return self.json(native.start(d.get('window'),interval))
                raise ValueError('无效采集操作')
            except Exception as e:
                capture_log.exception('Native capture request failed')
                return self.json({'error':str(e)},400)
        if self.path in ('/api/overlay/hotkeys','/api/overlay/hotkeys/report'):
            try:
                n=int(self.headers.get('Content-Length','0'))
                if not 0<n<4096:raise ValueError('无效快捷键设置')
                data=json.loads(self.rfile.read(n))
                if not isinstance(data,dict):raise ValueError('无效快捷键设置')
                if self.path.endswith('/report'):return self.json(overlay.hotkeys.report(data))
                return self.json(overlay.hotkeys.configure(data.get('bindings'),overlay.status()['enabled']))
            except (ValueError,OSError,TypeError) as error:return self.json({'error':str(error)},400)
        if self.path in ('/api/overlay','/api/overlay/frame'):
            try:
                n=int(self.headers.get('Content-Length','0'))
                if not 0<n<16_000_000: return self.json({'error':'无效悬浮窗数据'},413)
                payload=json.loads(self.rfile.read(n))
                if self.path=='/api/overlay/frame': return self.json(overlay.publish(payload))
                if payload.get('action')=='start': return self.json(overlay.start())
                if payload.get('action')=='stop': return self.json(overlay.stop())
                return self.json({'error':'无效悬浮窗操作'},400)
            except Exception as e: return self.json({'error':str(e)},400)
        if self.path=='/api/route':
            try:
                n=int(self.headers.get('Content-Length','0'))
                if not 0<n<32768:return self.json({'error':'路线请求过大'},413)
                return self.json(route_planner.plan(json.loads(self.rfile.read(n))))
            except Exception as e:return self.json({'error':str(e)},400)
        if self.path!='/api/match': return self.send_error(404)
        inference_locked=False
        native_request=False
        try:
            n=int(self.headers.get('Content-Length','0'))
            if not 0<n<12_000_000: return self.json({'error':'图片过大'},413)
            d=json.loads(self.rfile.read(n))
            native_request=isinstance(d,dict) and bool(d.get('native_session'))
            if d.get('native_session'):
                interval=d.get('interval',500)
                if type(interval) is not int or interval not in (250,500,1000,2000,3000):raise ValueError('无效本地采集参数')
                native.wait_next(d['native_session'],interval)
            inference_locked=match_slot.acquire(blocking=False)
            if not inference_locked:return self.json({'error':'上一帧仍在处理，稍后自动重试'},429)
            inference_started=time.perf_counter()
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
            # Old pages may still send a team-mode selection or tracking state.
            outdoor_mode='egg-heist'
            if tracking and tracking.get('id')=='egg-heist-team-mode':tracking=None
            realtime_tracking=d.get('realtime_tracking',True)
            if not isinstance(realtime_tracking,bool):raise ValueError('无效实时定位选项')
            observation=d.get('observation')
            if observation is not None:
                import math,re
                if (not isinstance(observation,dict) or not re.fullmatch(r'[a-zA-Z0-9-]{1,80}',str(observation.get('session','')))
                    or type(observation.get('sequence')) is not int or not 0<observation['sequence']<2**53
                    or type(observation.get('captured_at')) not in (int,float) or not math.isfinite(observation['captured_at']) or observation['captured_at']<=0):
                    raise ValueError('无效画面序号')
            native_meta=None
            if d.get('native_session'):
                interval=d.get('interval',500);after=d.get('after',0)
                if type(interval) is not int or interval not in (250,500,1000,2000,3000) or type(after) is not int or after<0:raise ValueError('无效本地采集参数')
                captured,message=native.take(d['native_session'],after,interval)
                if captured is None:return self.json({'capture_wait':True,'reason':message})
                im,sequence,at=captured
                native_meta={'sequence':sequence,'captured_at':at}
                if observation:observation=dict(observation,sequence=sequence,captured_at=at)
                scene=small_preview(im) if d.get('loot') or d.get('preview') else None
                if d.get('preview'):
                    native_meta['preview']='data:image/jpeg;base64,'+base64.b64encode(cv2.imencode('.jpg',scene,[cv2.IMWRITE_JPEG_QUALITY,70])[1]).decode()
                if not d.get('force_full'):
                    h,w=im.shape[:2];r=round(h*.089);x,y=round(w*.0945),round(h*.132)
                    if 1.45<=w/h<=2.1 and 64<=r*2<=1024:
                        answer=matcher.match_crop(im[y-r:y+r,x-r:x+r],tracking,realtime_tracking,scene if d.get('loot') else None,observation)
                        if not answer.get('requires_full_frame'):
                            native_meta['processing_ms']=round((time.perf_counter()-inference_started)*1000,2)
                            answer['native_capture']=native_meta;return self.json(answer)
                answer=matcher.match(im,anchor,tracking,outdoor_mode,realtime_tracking=realtime_tracking,observation=observation)
                native_meta['signature']=np.rint(cv2.resize(im,(32,32)).sum(axis=2)/24).astype(int).ravel().tolist()
                native_meta['processing_ms']=round((time.perf_counter()-inference_started)*1000,2)
                answer['native_capture']=native_meta;return self.json(answer)
            raw=base64.b64decode(d['image'].split(',')[-1],validate=True)
            im=cv2.imdecode(np.frombuffer(raw,np.uint8),cv2.IMREAD_COLOR)
            if im is None or max(im.shape[:2])>5000:raise ValueError('无效图片或图片过大')
            capture_kind=d.get('capture_kind','full')
            if capture_kind not in ('full','minimap'):raise ValueError('无效画面类型')
            if capture_kind=='minimap':
                if im.shape[0]!=im.shape[1] or not 64<=im.shape[0]<=1024:raise ValueError('无效小地图截图')
                scene=None
                if d.get('scene') is not None:
                    scene_raw=base64.b64decode(d['scene'].split(',')[-1],validate=True)
                    scene=cv2.imdecode(np.frombuffer(scene_raw,np.uint8),cv2.IMREAD_COLOR)
                    if scene is None or max(scene.shape[:2])>800:raise ValueError('无效掉落预览')
                answer=matcher.match_crop(im,tracking,realtime_tracking,scene,observation)
            else:
                answer=matcher.match(im,anchor,tracking,outdoor_mode,realtime_tracking=realtime_tracking,observation=observation)
            self.json(answer)
        except Exception as e:
            if native_request:
                capture_log.exception('Native capture/match failed')
            self.json({'error':str(e)},400)
        finally:
            if inference_locked:match_slot.release()

if __name__=='__main__':
    capture_crash_output=enable_capture_diagnostics()
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
        native.stop()
        overlay.stop()
        server.server_close()
