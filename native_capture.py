"""Opt-in WGC window capture. Raw pixels stay in this process; no recording."""
import ctypes as C
from ctypes import wintypes as W
import secrets, sys, threading, time
from pathlib import Path
import cv2

ROOT=Path(__file__).resolve().parent
if (ROOT/'vendor').is_dir():sys.path.insert(0,str(ROOT/'vendor'))


def unsupported_update_interval(error):
    message=str(error).casefold()
    return (any(name in message for name in ('minimum update interval','minimum_update_interval','minupdateinterval'))
            and any(reason in message for reason in ('not supported','unsupported')))


def unsupported_cursor_capture(error):
    message=str(error).casefold()
    return ('cursor capture' in message
            and any(reason in message for reason in ('not supported','unsupported')))

def window_api():
    api=C.WinDLL('user32',use_last_error=True)
    # HTTP handler threads otherwise see DPI-virtualized client coordinates.
    api.SetThreadDpiAwarenessContext.argtypes=[C.c_void_p]
    api.SetThreadDpiAwarenessContext.restype=C.c_void_p
    api.SetThreadDpiAwarenessContext(C.c_void_p(-4))
    api.IsWindow.argtypes=[W.HWND];api.IsWindow.restype=W.BOOL
    api.IsWindowVisible.argtypes=[W.HWND];api.IsWindowVisible.restype=W.BOOL
    api.IsIconic.argtypes=[W.HWND];api.IsIconic.restype=W.BOOL
    api.GetWindowTextLengthW.argtypes=[W.HWND];api.GetWindowTextLengthW.restype=C.c_int
    api.GetWindowTextW.argtypes=[W.HWND,W.LPWSTR,C.c_int];api.GetWindowTextW.restype=C.c_int
    api.GetClientRect.argtypes=[W.HWND,C.POINTER(W.RECT)]
    api.ClientToScreen.argtypes=[W.HWND,C.POINTER(W.POINT)]
    api.GetWindowThreadProcessId.argtypes=[W.HWND,C.POINTER(W.DWORD)]
    return api

def windows():
    api=window_api();items=[]
    callback=C.WINFUNCTYPE(W.BOOL,W.HWND,W.LPARAM)
    api.EnumWindows.argtypes=[callback,W.LPARAM]
    @callback
    def visit(hwnd,_):
        if not api.IsWindowVisible(hwnd):return True
        size=api.GetWindowTextLengthW(hwnd)
        if not size:return True
        title=C.create_unicode_buffer(size+1);api.GetWindowTextW(hwnd,title,size+1)
        rect=W.RECT();api.GetClientRect(hwnd,C.byref(rect))
        if rect.right<320 or rect.bottom<200:return True
        pid=W.DWORD();api.GetWindowThreadProcessId(hwnd,C.byref(pid))
        items.append({'id':str(hwnd),'title':title.value,'pid':pid.value})
        return True
    api.EnumWindows(visit,0)
    return items

def client_image(image,hwnd):
    """WGC normally includes the non-client frame. Keep HUD coordinates client-relative."""
    api=window_api();rect=W.RECT();point=W.POINT(0,0)
    if not api.GetClientRect(hwnd,C.byref(rect)) or not api.ClientToScreen(hwnd,C.byref(point)):return image
    h,w=image.shape[:2]
    if abs(w-rect.right)<=2 and abs(h-rect.bottom)<=2:return image
    bounds=W.RECT();dwm=C.WinDLL('dwmapi')
    dwm.DwmGetWindowAttribute.argtypes=[W.HWND,W.DWORD,C.c_void_p,W.DWORD]
    if dwm.DwmGetWindowAttribute(hwnd,9,C.byref(bounds),C.sizeof(bounds))!=0:return image
    if abs(w-(bounds.right-bounds.left))>3 or abs(h-(bounds.bottom-bounds.top))>3:return image
    x,y=point.x-bounds.left,point.y-bounds.top
    if 0<=x<w and 0<=y<h and x+rect.right<=w and y+rect.bottom<=h:
        return image[y:y+rect.bottom,x:x+rect.right]
    return image

class NativeCapture:
    def __init__(self, report=None):
        self.report=report or (lambda stage:None)
        self.lock=threading.Lock();self.operations=threading.RLock()
        self.control=None;self.capture=None;self.session=None;self.epoch=0
        self.latest=None;self.sequence=0;self.interval=500;self.hwnd=None
        self.last_poll=0;self.closed=False;self.started=0;self.changed=0
        self.next_scan=0;self.scan_condition=threading.Condition()
        self.minimum_interval_supported=None
        self.cursor_settings_supported=None
        self.readback_pacing=False

    def stop(self,session=None):
        with self.operations:
            if session is not None and session!=self.session:return {'stopped':False}
            self.epoch+=1
            control=self.control;self.control=None;self.capture=None;self.session=None
            with self.scan_condition:self.scan_condition.notify_all()
            with self.lock:self.latest=None
            if control:
                # WGC can wait for its callback on stop; never hold the frame lock.
                control.stop()
            return {'stopped':True}

    def _start_stream(self,interval):
        self.report('加载原生采集库')
        from windows_capture import WindowsCapture
        self.epoch+=1;old=self.control;self.control=None
        if old:old.stop()
        with self.lock:self.latest=None
        self.interval=interval;self.changed=time.monotonic();self.capture=None
        def launch(limited):
            # Separate generations also invalidate callbacks from a failed attempt.
            self.epoch+=1;epoch=self.epoch;self.closed=False;last_retained=None
            options={'cursor_capture':None if self.cursor_settings_supported is False else False,'window_hwnd':self.hwnd}
            if limited:options['minimum_update_interval']=max(125,int(interval/2))
            self.report('创建采集对象')
            capture=WindowsCapture(**options)
            pace=getattr(capture,'set_readback_interval',None)
            native_pacing=callable(pace)
            if native_pacing:
                self.report('设置原生跳帧间隔')
                pace(max(125,int(interval/2)))
            self.readback_pacing=native_pacing
            @capture.event
            def on_frame_arrived(frame,control):
                nonlocal last_retained
                now=time.monotonic()
                if epoch!=self.epoch or now-self.last_poll>20:
                    control.stop();return
                # Older unpatched libraries still need a post-readback fallback.
                # The bundled native gate skips surplus frames before copy/map.
                with self.lock:
                    if epoch!=self.epoch:return
                    if not native_pacing and not limited and last_retained is not None and now-last_retained<max(.125,self.interval/2000):return
                    last_retained=now;self.sequence+=1
                    self.latest=(frame,self.sequence,time.time()*1000,now)
            @capture.event
            def on_closed():
                if epoch==self.epoch:self.closed=True
            self.capture=capture
            self.report('启动 Windows 捕获线程')
            self.control=capture.start_free_threaded()
            self.report('采集线程已连接')
        # Capability errors disable only the unsupported option, independent of OS name.
        # At most three attempts: each optional feature can be disabled only once.
        for _ in range(3):
            limited=self.minimum_interval_supported is not False
            try:launch(limited)
            except Exception as error:
                self.epoch+=1;self.capture=None
                with self.lock:self.latest=None
                if limited and unsupported_update_interval(error):
                    self.minimum_interval_supported=False
                    self.report('系统不支持最小更新间隔，改用原生跳帧')
                elif self.cursor_settings_supported is not False and unsupported_cursor_capture(error):
                    self.cursor_settings_supported=False
                    self.report('系统不支持光标设置，使用系统默认值')
                else:raise
            else:
                if limited:self.minimum_interval_supported=True
                if self.cursor_settings_supported is not False:self.cursor_settings_supported=True
                break

    def start(self,hwnd,interval):
        with self.operations:
            self.report('检查目标窗口')
            selected=next((w for w in windows() if w['id']==str(hwnd)),None)
            if selected is None:raise ValueError('窗口已关闭或不可见，请重新选择。')
            self.stop();self.hwnd=int(hwnd);self.sequence=0
            self.session=secrets.token_hex(16);self.last_poll=self.started=time.monotonic()
            self.next_scan=0
            try:self._start_stream(interval)
            except Exception:
                self.stop();raise
            session=self.session
            def expire():
                while session==self.session:
                    time.sleep(2)
                    with self.operations:
                        if session==self.session and time.monotonic()-self.last_poll>20:self.stop(session)
            threading.Thread(target=expire,daemon=True).start()
            return {'session':self.session,'title':selected['title'],
                    'capture_mode':'compatible' if self.minimum_interval_supported is False or self.cursor_settings_supported is False else 'system_interval',
                    'readback_pacing':self.readback_pacing}

    def wait_next(self,session,interval):
        """Pace long-poll requests here, not in background browser timers."""
        with self.scan_condition:
            while True:
                if session!=self.session or not self.session:raise ValueError('本地采集已停止，请重新连接。')
                self.last_poll=time.monotonic()
                delay=self.next_scan-self.last_poll
                if delay<=0:break
                self.scan_condition.wait(min(delay,3))
            self.next_scan=time.monotonic()+interval/1000

    def take(self,session,after,interval):
        with self.operations:
            if not self.session or session!=self.session:raise ValueError('本地采集已停止，请重新选择窗口。')
            self.last_poll=time.monotonic();api=window_api()
            if not api.IsWindow(self.hwnd) or self.closed:raise ValueError('游戏窗口已关闭或采集已结束，请重新连接。')
            if api.IsIconic(self.hwnd):return None,'窗口已最小化 · 保留位置'
            if interval!=self.interval and self.last_poll-self.changed>=3:
                if self.minimum_interval_supported is False:
                    # A software pacing change needs no capture restart or frame loss.
                    if self.readback_pacing:self.capture.set_readback_interval(max(125,int(interval/2)))
                    self.interval=interval;self.changed=self.last_poll
                else:self._start_stream(interval)
            with self.lock:latest=self.latest
            if latest is None:return None,'等待本地画面'
            frame,sequence,at,arrived=latest
            if sequence<=after or time.monotonic()-arrived>max(5,interval/1000*3):
                return None,'本地画面未更新 · 等待恢复'
            image=client_image(frame.frame_buffer[:,:,:3],self.hwnd)
            # This binding maps the full GPU frame; only needed regions are copied later.
            return (image,sequence,at),None

def small_preview(image):
    h,w=image.shape[:2];factor=min(1,800/max(h,w))
    return cv2.resize(image,(round(w*factor),round(h*factor)))
