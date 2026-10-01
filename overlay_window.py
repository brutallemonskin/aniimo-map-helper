"""Non-activating, layered Windows map window; no game hooks or keyboard logging."""
import base64
import ctypes as C
from ctypes import wintypes as W
import io
import json
import queue
import sys
import os
import threading
import time
import urllib.request
from functools import lru_cache
from pathlib import Path
from PIL import Image, ImageChops, ImageDraw, ImageFont, ImageOps

WIDTH, HEIGHT = 520, 420
DISPLAY_SCALE = 2.1
WINDOW_WIDTH, WINDOW_HEIGHT = round(WIDTH * DISPLAY_SCALE), round(HEIGHT * DISPLAY_SCALE)
BAR = 36
FONT_PATH = 'C:/Windows/Fonts/msyh.ttc'
SETTINGS = Path(__file__).resolve().parent/'overlay-settings.json'


def resize_rect(rect, delta, edges, maximum=2080, aspect=HEIGHT/WIDTH):
    x,y,w,h=rect; dx,dy=delta
    changes=[]
    if 'l' in edges: changes.append(-dx/w)
    if 'r' in edges: changes.append(dx/w)
    if 't' in edges: changes.append(-dy/h)
    if 'b' in edges: changes.append(dy/h)
    change=max(changes,key=abs) if changes else 0
    width=round(max(min(364,maximum),min(maximum,w*(1+change))))
    height=round(width*aspect)
    return (x+w-width if 'l' in edges else x,y+h-height if 't' in edges else y,width,height)


def hit_edges(x,y,w,h):
    return ('l' if x<12 else 'r' if x>=w-12 else '')+('t' if y<8 else 'b' if y>=h-12 else '')


def crop_map(source):
    source = source.convert('RGBA')
    # The browser frame includes both transparent padding and opaque black atlas margins.
    r, g, b, alpha = source.split()
    visible = ImageChops.multiply(ImageChops.lighter(ImageChops.lighter(r, g), b), alpha)
    bounds = visible.point(lambda v: 255 if v > 38 else 0).getbbox()
    if bounds:
        left, top, right, bottom = bounds
        source = source.crop((max(0,left-2),max(0,top-2),min(source.width,right+2),min(source.height,bottom+2)))
    return source


def fit_map(source, size):
    return ImageOps.contain(crop_map(source), size, Image.Resampling.LANCZOS)


@lru_cache(maxsize=2)
def prepared_map(raw):
    with Image.open(io.BytesIO(base64.b64decode(raw))) as source:
        source = crop_map(source)
    height = max(1, round(WIDTH * source.height / source.width))
    return source.resize((WIDTH, height), Image.Resampling.LANCZOS)


def layout_height(state):
    return BAR + 28 + prepared_map(state['image']).height if state.get('image') else HEIGHT


def window_size(width, height, screen_width, screen_height):
    # Keep the complete map visible when a taller map replaces a wider one.
    maximum = max(1, min(2080, screen_width, int(max(1, screen_height-60)*WIDTH/height)))
    width = max(min(364, maximum), min(maximum, width))
    return width, round(width*height/WIDTH), maximum


def render(state, opacity=190, locked=False, hotkeys=True):
    en = state.get('language') == 'en'
    height = layout_height(state)
    image = Image.new('RGBA', (WIDTH, height), (9, 18, 25, opacity))
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype(FONT_PATH, 14)
    small = ImageFont.truetype(FONT_PATH, 12)
    draw.rectangle((0, 0, WIDTH, BAR), fill=(17, 32, 39, 235))
    title = state.get('title', 'Waiting for dungeon' if en else '等待识别地宫')
    if state.get('image') and state.get('updated') and time.time() - state['updated'] > 4:
        title = 'Paused · Last position' if en else '画面暂停 · 上次位置'
    while draw.textlength(title, font=font) > WIDTH-175 and title:
        title=title[:-1]
    draw.text((12, 9), title, font=font, fill='#e4f4ef')
    for x, text in [(WIDTH-148, '−'), (WIDTH-117, '+'), (WIDTH-87, 'Lock' if en else '穿透'), (WIDTH-29, '×')]:
        draw.text((x, 8), text, font=font, fill='#86e4c4')
    raw = state.get('image')
    if raw:
        source = prepared_map(raw).copy()
        # Uniform translucency preserves the contrast of the map and its icons.
        source.putalpha(source.getchannel('A').point(lambda a: a * opacity // 255))
        image.paste(source, (0, BAR))
    else:
        draw.text((90, 174), ('Open the full game map to begin' if en else '打开游戏大地图，识别后自动显示'), font=font, fill='#d1e1e3')
        draw.text((98, 207), ('Keep the helper and screen sharing open' if en else '请保持助手页面和窗口共享开启'), font=small, fill='#9db1ba')
    hint = 'Alt+Shift+M 解锁调整' if locked else '标题栏移动 · 拖动边角缩放'
    hint += ' · Alt+Shift+H 隐藏' if hotkeys else ' · 快捷键被占用，穿透未开启'
    if en:
        hint = 'Alt+Shift+M: unlock' if locked else 'Drag title: move / edges: resize'
        hint += ' | Alt+Shift+H: hide' if hotkeys else ' | Hotkeys unavailable'
    draw.text((10, height-24), hint, font=small, fill='#b1d7cb')
    if not locked:
        for offset in (7,12,17):
            draw.line((WIDTH-offset,height-4,WIDTH-4,height-offset),fill='#86e4c4',width=1)
    return image


def main(smoke=False):
    user = C.WinDLL('user32', use_last_error=True)
    gdi = C.WinDLL('gdi32', use_last_error=True)
    kernel = C.WinDLL('kernel32', use_last_error=True)
    LRESULT = C.c_ssize_t
    WNDPROC = C.WINFUNCTYPE(LRESULT, W.HWND, W.UINT, W.WPARAM, W.LPARAM)

    class WC(C.Structure):
        _fields_ = [('style', W.UINT), ('proc', WNDPROC), ('clsExtra', C.c_int), ('wndExtra', C.c_int),
                    ('instance', W.HINSTANCE), ('icon', W.HANDLE), ('cursor', W.HANDLE),
                    ('background', W.HBRUSH), ('menu', W.LPCWSTR), ('name', W.LPCWSTR)]

    class BIHEADER(C.Structure):
        _fields_ = [('size', W.DWORD), ('width', W.LONG), ('height', W.LONG), ('planes', W.WORD),
                    ('bits', W.WORD), ('compression', W.DWORD), ('sizeImage', W.DWORD),
                    ('xppm', W.LONG), ('yppm', W.LONG), ('used', W.DWORD), ('important', W.DWORD)]

    class BLEND(C.Structure):
        _fields_ = [('op', C.c_ubyte), ('flags', C.c_ubyte), ('alpha', C.c_ubyte), ('format', C.c_ubyte)]

    def api(dll, name, restype, args):
        fn = getattr(dll, name); fn.restype = restype; fn.argtypes = args; return fn

    api(kernel, 'GetModuleHandleW', W.HMODULE, [W.LPCWSTR])
    api(user, 'RegisterClassW', W.ATOM, [C.POINTER(WC)])
    api(user, 'CreateWindowExW', W.HWND, [W.DWORD, W.LPCWSTR, W.LPCWSTR, W.DWORD, C.c_int, C.c_int, C.c_int, C.c_int, W.HWND, W.HMENU, W.HINSTANCE, W.LPVOID])
    api(user, 'DefWindowProcW', LRESULT, [W.HWND, W.UINT, W.WPARAM, W.LPARAM])
    api(user, 'GetWindowLongPtrW', C.c_ssize_t, [W.HWND, C.c_int])
    api(user, 'SetWindowLongPtrW', C.c_ssize_t, [W.HWND, C.c_int, C.c_ssize_t])
    api(user, 'SetWindowPos', W.BOOL, [W.HWND, W.HWND, C.c_int, C.c_int, C.c_int, C.c_int, W.UINT])
    api(user, 'GetDC', W.HDC, [W.HWND])
    api(user, 'ReleaseDC', C.c_int, [W.HWND, W.HDC])
    api(user, 'UpdateLayeredWindow', W.BOOL, [W.HWND, W.HDC, C.POINTER(W.POINT), C.POINTER(W.SIZE), W.HDC, C.POINTER(W.POINT), W.DWORD, C.POINTER(BLEND), W.DWORD])
    api(user, 'GetWindowRect', W.BOOL, [W.HWND, C.POINTER(W.RECT)])
    api(user, 'GetCursorPos', W.BOOL, [C.POINTER(W.POINT)])
    api(user, 'LoadCursorW', W.HANDLE, [W.HINSTANCE, W.LPVOID])
    api(user, 'SetCursor', W.HANDLE, [W.HANDLE])
    api(user, 'SetCapture', W.HWND, [W.HWND])
    api(user, 'ReleaseCapture', W.BOOL, [])
    api(user, 'DestroyWindow', W.BOOL, [W.HWND])
    api(user, 'ShowWindow', W.BOOL, [W.HWND, C.c_int])
    api(user, 'RegisterHotKey', W.BOOL, [W.HWND, C.c_int, W.UINT, W.UINT])
    api(user, 'UnregisterHotKey', W.BOOL, [W.HWND, C.c_int])
    api(user, 'SetTimer', C.c_size_t, [W.HWND, C.c_size_t, W.UINT, W.LPVOID])
    api(user, 'GetMessageW', W.BOOL, [C.POINTER(W.MSG), W.HWND, W.UINT, W.UINT])
    api(user, 'TranslateMessage', W.BOOL, [C.POINTER(W.MSG)])
    api(user, 'DispatchMessageW', LRESULT, [C.POINTER(W.MSG)])
    api(gdi, 'CreateCompatibleDC', W.HDC, [W.HDC])
    api(gdi, 'CreateDIBSection', W.HBITMAP, [W.HDC, C.POINTER(BIHEADER), W.UINT, C.POINTER(W.LPVOID), W.HANDLE, W.DWORD])
    api(gdi, 'SelectObject', W.HANDLE, [W.HDC, W.HANDLE])
    api(gdi, 'DeleteObject', W.BOOL, [W.HANDLE])
    api(gdi, 'DeleteDC', W.BOOL, [W.HDC])
    try: user.SetProcessDPIAware()
    except OSError: pass
    updates = queue.Queue(maxsize=1)
    finished = threading.Event()
    state = {'title': '等待识别地宫', 'image': None}
    opacity, locked, hidden, hotkeys = 190, False, False, False
    window_width,window_height=WINDOW_WIDTH,WINDOW_HEIGHT
    logical_height=HEIGHT
    maximum_width=max(364,min(2080,user.GetSystemMetrics(0),round((user.GetSystemMetrics(1)-60)*WIDTH/HEIGHT)))
    saved={}
    if not smoke:
        try:
            saved=json.loads(SETTINGS.read_text(encoding='utf-8'))
            if not isinstance(saved,dict): saved={}
        except (OSError,ValueError): pass
    def setting(key,default):
        value=saved.get(key,default)
        return value if isinstance(value,int) and not isinstance(value,bool) else default
    window_width=max(364,min(maximum_width,setting('width',WINDOW_WIDTH)))
    window_height=round(window_width*HEIGHT/WIDTH)
    opacity=max(80,min(245,setting('opacity',190)))
    drag = None
    hwnd = None

    def save_settings():
        if smoke or not hwnd:return
        rect=W.RECT();user.GetWindowRect(hwnd,C.byref(rect))
        try:
            temporary=SETTINGS.with_suffix('.tmp')
            temporary.write_text(json.dumps({'x':rect.left,'y':rect.top,'width':window_width,'opacity':opacity}),encoding='utf-8')
            temporary.replace(SETTINGS)
        except OSError:pass

    def paint():
        im = render(state, opacity, locked, hotkeys).resize((window_width, window_height), Image.Resampling.LANCZOS)
        # Layered windows require premultiplied BGRA pixels.
        pixels = im.convert('RGBa').tobytes('raw', 'BGRa')
        dc = user.GetDC(None)
        mem = gdi.CreateCompatibleDC(dc)
        header = BIHEADER(C.sizeof(BIHEADER), window_width, -window_height, 1, 32, 0, len(pixels), 0, 0, 0, 0)
        bits = W.LPVOID()
        bmp = gdi.CreateDIBSection(dc, C.byref(header), 0, C.byref(bits), None, 0)
        if not bmp:
            gdi.DeleteDC(mem); user.ReleaseDC(None, dc)
            raise C.WinError(C.get_last_error())
        old = gdi.SelectObject(mem, bmp)
        try:
            C.memmove(bits, pixels, len(pixels))
            rect = W.RECT(); user.GetWindowRect(hwnd, C.byref(rect))
            ok = user.UpdateLayeredWindow(hwnd, dc, C.byref(W.POINT(rect.left, rect.top)), C.byref(W.SIZE(window_width, window_height)), mem, C.byref(W.POINT(0, 0)), 0, C.byref(BLEND(0, 0, 255, 1)), 2)
            if not ok: raise C.WinError(C.get_last_error())
        finally:
            gdi.SelectObject(mem, old); gdi.DeleteObject(bmp); gdi.DeleteDC(mem); user.ReleaseDC(None, dc)

    def toggle_lock():
        nonlocal locked
        if not hotkeys: return
        locked = not locked
        style = user.GetWindowLongPtrW(hwnd, -20)
        user.SetWindowLongPtrW(hwnd, -20, style | 0x20 if locked else style & ~0x20)
        paint()

    @WNDPROC
    def proc(handle, msg, wp, lp):
        nonlocal opacity, drag, hidden, state, window_width, window_height, logical_height, maximum_width
        try:
            if msg == 0x21: return 3  # MA_NOACTIVATE: do not steal focus from the game.
            if msg == 0x201:
                if locked:return 0
                px,py=lp&0xffff,(lp>>16)&0xffff
                edges=hit_edges(px,py,window_width,window_height)
                p,r=W.POINT(),W.RECT()
                user.GetCursorPos(C.byref(p));user.GetWindowRect(handle,C.byref(r))
                if edges:
                    drag=(edges,p.x,p.y,(r.left,r.top,window_width,window_height));user.SetCapture(handle);return 0
                x,y=px*WIDTH/window_width,py*logical_height/window_height
                if y < BAR:
                    if x > WIDTH-42: user.DestroyWindow(handle)
                    elif x > WIDTH-100: toggle_lock()
                    elif x > WIDTH-132: opacity = min(245, opacity+20); paint();save_settings()
                    elif x > WIDTH-162: opacity = max(80, opacity-20); paint();save_settings()
                    else:
                        p, r = W.POINT(), W.RECT()
                        user.GetCursorPos(C.byref(p)); user.GetWindowRect(handle, C.byref(r))
                        drag = ('move',p.x,p.y,(r.left,r.top,window_width,window_height)); user.SetCapture(handle)
                return 0
            if msg == 0x200 and drag:
                p = W.POINT(); user.GetCursorPos(C.byref(p))
                edges,sx,sy,rect=drag
                if edges=='move':
                    user.SetWindowPos(handle,W.HWND(-1),rect[0]+p.x-sx,rect[1]+p.y-sy,0,0,0x11)
                else:
                    x,y,window_width,window_height=resize_rect(rect,(p.x-sx,p.y-sy),edges,maximum_width,logical_height/WIDTH)
                    user.SetWindowPos(handle,W.HWND(-1),x,y,window_width,window_height,0x10);paint()
                return 0
            if msg == 0x20 and not locked:
                p,r=W.POINT(),W.RECT();user.GetCursorPos(C.byref(p));user.GetWindowRect(handle,C.byref(r))
                edges=hit_edges(p.x-r.left,p.y-r.top,window_width,window_height)
                cursor=32642 if edges in ('lt','rb') else 32643 if edges in ('rt','lb') else 32644 if edges in ('l','r') else 32645 if edges in ('t','b') else 32512
                user.SetCursor(user.LoadCursorW(None,C.c_void_p(cursor)));return 1
            if msg in (0x202, 0x215):
                if drag:drag=None;save_settings()
                if msg==0x202:user.ReleaseCapture()
                return 0
            if msg == 0x312:
                if wp == 1: toggle_lock()
                if wp == 2:
                    hidden = not hidden; user.ShowWindow(handle, 0 if hidden else 4)
                return 0
            if msg == 0x113:
                if smoke: user.DestroyWindow(handle); return 0
                if not drag:
                    try: state = updates.get_nowait()
                    except queue.Empty: pass
                    next_height=layout_height(state)
                    if next_height != logical_height:
                        logical_height=next_height
                        window_width,window_height,maximum_width=window_size(window_width,logical_height,user.GetSystemMetrics(0),user.GetSystemMetrics(1))
                        rect=W.RECT();user.GetWindowRect(handle,C.byref(rect))
                        vx,vy,vw,vh=[user.GetSystemMetrics(i) for i in (76,77,78,79)]
                        x=max(vx,min(vx+vw-window_width,rect.left))
                        y=max(vy,min(vy+vh-window_height,rect.top))
                        user.SetWindowPos(handle,W.HWND(-1),x,y,window_width,window_height,0x10)
                if not hidden: paint()
                return 0
            if msg == 2:
                save_settings();finished.set(); user.PostQuitMessage(0); return 0
        except Exception:
            import traceback; traceback.print_exc()
        return user.DefWindowProcW(handle, msg, wp, lp)

    instance = kernel.GetModuleHandleW(None)
    name = 'AniimoLocalMapOverlay'
    wc = WC(0, proc, 0, 0, instance, None, None, None, None, name)
    if not user.RegisterClassW(C.byref(wc)): raise C.WinError(C.get_last_error())
    vx,vy,vw,vh=[user.GetSystemMetrics(i) for i in (76,77,78,79)]
    x=max(vx,min(vx+vw-window_width,setting('x',user.GetSystemMetrics(0)-window_width-40)))
    y=max(vy,min(vy+vh-window_height,setting('y',80)))
    # Layered, topmost and non-activating; taskbar entry provides another recovery path.
    hwnd = user.CreateWindowExW(0x80000 | 0x8 | 0x40000 | 0x8000000, name, '伊莫地图悬浮窗', 0x80000000, x, y, window_width, window_height, None, None, instance, None)
    if not hwnd: raise C.WinError(C.get_last_error())
    hk1 = user.RegisterHotKey(hwnd, 1, 0x4005, ord('M'))  # Alt + Shift, no repeat
    hk2 = user.RegisterHotKey(hwnd, 2, 0x4005, ord('H'))
    hotkeys = bool(hk1 and hk2)
    paint()
    user.ShowWindow(hwnd, 4)
    user.SetWindowPos(hwnd, W.HWND(-1), 0, 0, 0, 0, 0x13)
    if smoke:
        style = user.GetWindowLongPtrW(hwnd, -20)
        assert style & 0x80000 and style & 0x8 and style & 0x8000000
        if hotkeys:
            toggle_lock(); assert user.GetWindowLongPtrW(hwnd, -20) & 0x20
            toggle_lock(); assert not user.GetWindowLongPtrW(hwnd, -20) & 0x20

    def poll():
        while not finished.is_set():
            try:
                with urllib.request.urlopen('http://127.0.0.1:'+os.environ.get('ANIIMO_PORT','18731')+'/api/overlay/frame', timeout=2) as reply:
                    value = json.load(reply)
            except Exception:
                value = {'title': 'Helper disconnected' if state.get('language') == 'en' else '助手连接中断 · 请检查本地页面', 'language': state.get('language','zh-CN'), 'image': None}
            try: updates.get_nowait()
            except queue.Empty: pass
            updates.put_nowait(value)
            finished.wait(.25)

    if not smoke: threading.Thread(target=poll, daemon=True).start()
    user.SetTimer(hwnd, 1, 1000 if smoke else 250, None)
    message = W.MSG()
    while True:
        code = user.GetMessageW(C.byref(message), None, 0, 0)
        if code <= 0: break
        user.TranslateMessage(C.byref(message)); user.DispatchMessageW(C.byref(message))
    user.UnregisterHotKey(hwnd, 1); user.UnregisterHotKey(hwnd, 2)
    if smoke: print('PASS: native layered/topmost/non-activating window, paint, click-through style, close')


if __name__ == '__main__':
    main('--smoke-test' in sys.argv)
