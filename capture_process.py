"""Keep WGC failures outside the HTTP service; exchange frames through shared memory."""
import logging
import multiprocessing as mp
from multiprocessing import shared_memory
from pathlib import Path
import sys
import threading
import time

import numpy as np

LOG = logging.getLogger('aniimo.capture')


def exit_reason(code, stage):
    value = '未知' if code is None else f'0x{code & 0xffffffff:08X}'
    known = {0xc0000005: '发生内存访问异常', 0xc000001d: '执行了不支持的指令',
             0xc0000409: '触发系统快速失败保护', 0xc0000135: '缺少运行库或依赖 DLL'}
    detail = known.get((code or 0) & 0xffffffff, '具体原因未确认')
    return f'本地采集进程在{stage}时异常退出（退出码 {value}，{detail}）。助手仍在运行，可重新连接。'


def capture_worker(connection, log_root):
    # Imported only in the isolated process. No native capture DLL loads in the server.
    import faulthandler
    import os
    from native_capture import NativeCapture
    memory = None
    crash_output = None
    try:
        crash_path = Path(log_root) / 'capture-worker-crash.log'
        if crash_path.exists() and crash_path.stat().st_size > 262144:
            crash_path.replace(crash_path.with_name('capture-worker-crash.previous.log'))
        crash_output = crash_path.open('a', encoding='utf8')
        faulthandler.enable(file=crash_output, all_threads=True)
    except OSError:
        pass
    def report(stage):
        if crash_output:
            try:
                crash_output.write(time.strftime('%Y-%m-%d %H:%M:%S')+' stage: '+stage+'\n')
                crash_output.flush()
            except OSError:
                pass
        connection.send({'progress': stage})
    capture = NativeCapture(report=report)

    parent = mp.parent_process()
    def watch_parent():
        while parent and parent.is_alive():
            time.sleep(1)
        if parent:
            os._exit(0)  # Also stop an orphan after forced ExitAll/server termination.
    threading.Thread(target=watch_parent, daemon=True).start()
    try:
        while connection.poll(20):
            request = connection.recv()
            action = request['action']
            try:
                if action == 'start':
                    value = capture.start(request['window'], request['interval'], request.get('window_pid'))
                elif action == 'take':
                    frame, message = capture.take(request['session'], request['after'], request['interval'])
                    if frame is None:
                        value = {'wait': message}
                    else:
                        image, sequence, at = frame
                        if image.dtype != np.uint8 or image.ndim != 3 or image.shape[2] != 3 or max(image.shape[:2]) > 5000:
                            raise ValueError('采集画面尺寸或格式无效（最大支持 5000 像素边长）')
                        if memory is None or memory.size < image.nbytes:
                            if memory:
                                memory.close(); memory.unlink()
                            memory = shared_memory.SharedMemory(create=True, size=image.nbytes)
                        shared = np.ndarray(image.shape, dtype=np.uint8, buffer=memory.buf)
                        shared[:] = image
                        del shared
                        value = {'memory': memory.name, 'shape': image.shape, 'sequence': sequence, 'at': at}
                elif action == 'stop':
                    capture.stop()
                    connection.send({'ok': True, 'value': {'stopped': True}})
                    break
                else:
                    raise ValueError('无效采集操作')
                connection.send({'ok': True, 'value': value})
            except Exception as error:
                # Preserve the original system/library message in the HTTP response.
                connection.send({'ok': False, 'error': f'{type(error).__name__}: {error}'})
    except (EOFError, BrokenPipeError, OSError):
        pass
    finally:
        if memory:
            memory.close(); memory.unlink()
        capture.stop()
        connection.close()
        if crash_output:
            faulthandler.disable(); crash_output.close()


class IsolatedCapture:
    def __init__(self, root, worker=capture_worker):
        self.root = str(root)
        self.worker = worker
        self.operations = threading.RLock()
        self.scan_condition = threading.Condition()
        self.process = None
        self.connection = None
        self.session = None
        self.next_scan = 0

    def _dispose(self):
        self.session = None
        with self.scan_condition:
            self.scan_condition.notify_all()
        process, self.process = self.process, None
        connection, self.connection = self.connection, None
        if connection:
            connection.close()
        if process and process.pid is not None:
            process.join(.1)
            if process.is_alive():
                process.terminate(); process.join(2)
            if not process.is_alive():
                process.close()

    def _rpc(self, request, stage, timeout=10):
        process, connection = self.process, self.connection
        if process is None:
            raise ValueError('本地采集已停止，请重新连接。')
        deadline = time.monotonic() + timeout
        try:
            if not process.is_alive():
                raise EOFError()
            connection.send(request)
            while time.monotonic() < deadline:
                if connection.poll(.05):
                    answer = connection.recv()
                    if 'progress' in answer:
                        stage=answer['progress']
                        continue
                    if not answer['ok']:
                        raise ValueError('本地采集失败（' + stage + '）：' + answer['error'])
                    return answer['value']
                if not process.is_alive():
                    raise EOFError()
            message = f'本地采集在{stage}时超过 {timeout:g} 秒未响应，已结束采集进程。助手仍在运行，请重新连接。'
        except (EOFError, BrokenPipeError, OSError):
            process.join(.2)
            message = exit_reason(process.exitcode, stage)
        LOG.error(message)
        self._dispose()
        raise ValueError(message)

    def start(self, hwnd, interval, expected_pid=None):
        with self.operations:
            self.stop()
            context = mp.get_context('spawn')
            # Keep the capture helper invisible when launched from python.exe too.
            pythonw = Path(sys.executable).with_name('pythonw.exe')
            if sys.platform == 'win32' and pythonw.exists():
                mp.set_executable(str(pythonw))
            self.connection, child = context.Pipe()
            self.process = context.Process(target=self.worker, args=(child, self.root), daemon=True)
            try:
                self.process.start()
                child.close()
                result = self._rpc({'action': 'start', 'window': hwnd, 'window_pid': expected_pid, 'interval': interval}, '启动采集')
                self.session = result['session']; self.next_scan = 0
                return result
            except Exception:
                child.close()
                self._dispose()
                raise

    def stop(self, session=None):
        with self.operations:
            if session is not None and session != self.session:
                return {'stopped': False}
            try:
                if self.process and self.process.is_alive():
                    self._rpc({'action': 'stop'}, '停止采集', timeout=1)
            except (ValueError, OSError):
                pass
            finally:
                self._dispose()
            return {'stopped': True}

    def wait_next(self, session, interval):
        with self.scan_condition:
            while True:
                if not self.session or session != self.session:
                    raise ValueError('本地采集已停止，请重新连接。')
                delay = self.next_scan - time.monotonic()
                if delay <= 0:
                    break
                self.scan_condition.wait(min(delay, 3))
            self.next_scan = time.monotonic() + interval / 1000

    def take(self, session, after, interval):
        with self.operations:
            if not self.session or session != self.session:
                raise ValueError('本地采集已停止，请重新连接。')
            value = self._rpc({'action': 'take', 'session': session, 'after': after, 'interval': interval}, '读取画面')
            if 'wait' in value:
                return None, value['wait']
            shape = tuple(value['shape'])
            if len(shape) != 3 or shape[2] != 3 or not all(type(v) is int and 0 < v <= 5000 for v in shape):
                raise ValueError('采集进程返回了无效画面尺寸')
            memory = shared_memory.SharedMemory(name=value['memory'])
            try:
                # A stable copy lets Stop/reconnect safely release the worker mapping.
                image = np.ndarray(shape, dtype=np.uint8, buffer=memory.buf).copy()
            finally:
                memory.close()
            return (image, value['sequence'], value['at']), None
