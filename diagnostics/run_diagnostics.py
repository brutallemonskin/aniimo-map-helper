"""Optional, bounded WGC comparisons. Captures only our own fixture; never uploads."""
import ctypes
import faulthandler
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parent
PACKAGE = ROOT.parent
NAMES = {'direct-item': 'Windows 原生捕获对象', 'upstream': '官方原版采集库',
         'patched-unpaced': '当前采集库（关闭跳帧）', 'patched-paced': '当前采集库（0.5 秒跳帧）'}

def sanitize(text):
    text = str(text)
    for value, label in ((str(PACKAGE), '<助手目录>'), (str(Path.home()), '<用户目录>')):
        text = text.replace(value, label).replace(value.replace('\\', '/'), label)
    return text

def child(variant, hwnd):
    faulthandler.enable()
    if variant == 'upstream':
        sys.path.insert(0, str(ROOT / 'upstream'))
    report = {'variant': variant, 'cycles': [], 'ok': False}
    try:
        print('stage: load capture library', file=sys.stderr, flush=True)
        from windows_capture import WindowsCapture
        report['library_sha256'] = hashlib.sha256(
            (Path(sys.modules['windows_capture'].__file__).parent/'windows_capture.pyd').read_bytes()).hexdigest()
        for _ in range(3):
            frames = []; control = None
            cap = WindowsCapture(window_hwnd=hwnd, cursor_capture=None, draw_border=None)
            if variant != 'upstream':
                cap.set_readback_interval(500 if variant == 'patched-paced' else 0)
            @cap.event
            def on_frame_arrived(frame, capture_control):
                frames.append({'time': time.monotonic(), 'size': [frame.width, frame.height],
                               'hash': hashlib.sha256(frame.frame_buffer[::16, ::16].tobytes()).hexdigest()})
            @cap.event
            def on_closed():
                pass
            try:
                started = time.monotonic()
                print('stage: start WGC capture thread', file=sys.stderr, flush=True)
                control = cap.start_free_threaded()
                time.sleep(5)
            finally:
                if control is not None:
                    control.stop()
            row = {'frames': len(frames), 'sizes': sorted(set(tuple(f['size']) for f in frames)),
                   'distinct_frames': len(set(f['hash'] for f in frames)),
                   'first_frame_ms': round(1000*(frames[0]['time']-started), 1) if frames else None}
            row['ok'] = row['frames'] >= 3 and row['distinct_frames'] >= 2
            if variant != 'upstream':
                row['readback_stats'] = cap.readback_stats()
            report['cycles'].append(row)
        report['ok'] = all(c['ok'] for c in report['cycles'])
    except BaseException:
        report['error'] = sanitize(traceback.format_exc())
    print(json.dumps(report, ensure_ascii=False), flush=True)
    return 0 if report['ok'] else 1

def hwnd_for_pid(pid):
    user32 = ctypes.WinDLL('user32', use_last_error=True)
    user32.IsWindowVisible.argtypes = [ctypes.c_void_p]
    user32.GetWindowThreadProcessId.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_ulong)]
    callback_type = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    found = []
    @callback_type
    def callback(hwnd, _):
        owner = ctypes.c_ulong()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
        if owner.value == pid and user32.IsWindowVisible(hwnd):
            found.append(hwnd)
        return True
    user32.EnumWindows.argtypes = [callback_type, ctypes.c_void_p]
    user32.EnumWindows(callback, None)
    return found[0] if found else None

def interpretation(cases):
    if not cases: return '测试未完成，请查看启动错误。'
    passed = lambda name: cases.get(name, {}).get('ok', False)
    if all(passed(k) for k in NAMES):
        return '四组样例测试通过。只证明当前桌面测试窗口可采集，不能排除游戏窗口、驱动、权限或间歇性故障。'
    if not passed('direct-item'):
        return '直接调用 Windows 创建捕获对象也未成功。请检查原始错误码；不能仅据此断定系统损坏。'
    if passed('upstream') and (not passed('patched-unpaced') or not passed('patched-paced')):
        return '官方库通过而当前库未全部通过，请将本报告反馈给开发者，优先比较补丁和构建差异。'
    return '捕获对象可以创建，但部分收帧测试未通过。可能与图形设备、采集会话或库有关，请保留各组错误。'

def run():
    stamp = time.strftime('%Y%m%d-%H%M%S') + '-' + str(os.getpid())
    output = PACKAGE / '诊断报告' / stamp
    try:
        output.mkdir(parents=True)
    except OSError as error:
        print('无法写入报告，请将整个助手解压到可写目录后重试：' + str(error), flush=True)
        return 1
    version = sys.getwindowsversion()
    result = {'helper_version': '0.4.2', 'created_local': time.strftime('%Y-%m-%dT%H:%M:%S%z'),
              'windows': {'major': version.major, 'minor': version.minor, 'build': version.build},
              'python': sys.version, 'cases': {}}
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\Microsoft\Windows NT\CurrentVersion') as key:
            for name in ('UBR', 'DisplayVersion', 'EditionID'):
                try: result['windows'][name] = winreg.QueryValueEx(key, name)[0]
                except OSError: pass
        result['remote_desktop_session'] = bool(ctypes.windll.user32.GetSystemMetrics(0x1000))
    except OSError:
        pass
    fixture = None
    try:
        fixture = subprocess.Popen([str(ROOT/'Fixture.exe')])
        hwnd = None
        for _ in range(60):
            hwnd = hwnd_for_pid(fixture.pid)
            if hwnd: break
            if fixture.poll() is not None: break
            time.sleep(.1)
        if not hwnd: raise RuntimeError('测试窗口没有打开，请在已解锁的 Windows 桌面重试。')
        tasks = [('direct-item', [str(ROOT/'ItemProbe.exe'), str(hwnd)])]
        tasks += [(v, [sys.executable, '-X', 'utf8', str(__file__), '--child', v, str(hwnd)])
                  for v in ('upstream', 'patched-unpaced', 'patched-paced')]
        for name, cmd in tasks:
            print('正在测试：' + NAMES[name], flush=True)
            try:
                p = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace',
                                   timeout=35, creationflags=subprocess.CREATE_NO_WINDOW)
                case = {'ok': p.returncode == 0, 'exit': p.returncode,
                        'exit_hex': f'0x{p.returncode & 0xffffffff:08X}',
                        'stdout': sanitize(p.stdout), 'stderr': sanitize(p.stderr)}
                if name != 'direct-item':
                    try:
                        case['details'] = json.loads(p.stdout)
                        case['ok'] = case['ok'] and case['details'].get('ok', False)
                    except ValueError:
                        case['ok'] = False
            except subprocess.TimeoutExpired as error:
                def decoded(value):
                    return value.decode('utf-8', 'replace') if isinstance(value, bytes) else value or ''
                case = {'ok': False, 'timeout': True, 'error': '超过 35 秒，已终止本组测试进程。',
                        'stdout': sanitize(decoded(error.stdout)), 'stderr': sanitize(decoded(error.stderr))}
            except OSError as error:
                case = {'ok': False, 'error': sanitize(error)}
            result['cases'][name] = case
            (output/'report.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
            print('通过' if case['ok'] else '未通过，已记录原因', flush=True)
    except BaseException:
        result['error'] = sanitize(traceback.format_exc())
    finally:
        if fixture is not None and fixture.poll() is None:
            fixture.terminate()
            try: fixture.wait(timeout=5)
            except subprocess.TimeoutExpired: fixture.kill(); fixture.wait(timeout=5)
        result['summary'] = interpretation(result['cases'])
        (output/'report.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
        lines = ['伊莫地图助手 v0.4.2 · WGC 兼容性诊断', '',
                 'Windows build: ' + str(version.build), result['summary'], '',
                 '仅采集本工具的动态测试窗口。未保存或上传游戏截图，不收集账号、窗口标题列表、IP 或机器序列号。',
                 '以下原始错误可能包含系统组件名称；报告不会自动发送。', '']
        if result.get('error'): lines.append(result['error'])
        for name, case in result['cases'].items():
            lines += [NAMES[name] + ('：通过' if case['ok'] else '：未通过'),
                      json.dumps(case, ensure_ascii=False, indent=2), '']
        (output/'诊断结果.txt').write_text('\n'.join(lines), encoding='utf-8-sig')
        print('\n' + result['summary'] + '\n报告已保存：' + str(output), flush=True)
    return 0 if len(result['cases']) == 4 and all(c['ok'] for c in result['cases'].values()) else 1

if __name__ == '__main__':
    sys.exit(child(sys.argv[2], int(sys.argv[3])) if len(sys.argv) > 1 and sys.argv[1] == '--child' else run())
