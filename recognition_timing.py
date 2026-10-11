"""记录识别阶段耗时；仅保存数字和状态，不保存截图或窗口信息。"""
from collections import deque
from contextvars import ContextVar
from functools import wraps
import threading
import time

_current=ContextVar('recognition_timing',default=None)
_recent=deque(maxlen=40)
_lock=threading.Lock()


def stage(name):
    def decorate(function):
        @wraps(function)
        def wrapped(*args,**kwargs):
            trace=_current.get()
            if trace is None:return function(*args,**kwargs)
            frame=[time.perf_counter(),0.]
            trace['stack'].append(frame)
            try:return function(*args,**kwargs)
            finally:
                elapsed=(time.perf_counter()-frame[0])*1000
                trace['stack'].pop()
                trace['stages'][name]=trace['stages'].get(name,0.)+max(0.,elapsed-frame[1])
                if trace['stack']:trace['stack'][-1][1]+=elapsed
        return wrapped
    return decorate


def recognition(function):
    @wraps(function)
    def wrapped(*args,**kwargs):
        if _current.get() is not None:return function(*args,**kwargs)
        trace={'stages':{},'stack':[]};token=_current.set(trace);start=time.perf_counter()
        try:
            result=function(*args,**kwargs)
            elapsed=(time.perf_counter()-start)*1000
            trace['stages']['其他识别处理']=max(0.,elapsed-sum(trace['stages'].values()))
            result['performance']={'recognition_ms':round(elapsed,2),
                                   'stages_ms':{key:round(value,2) for key,value in trace['stages'].items()}}
            return result
        finally:_current.reset(token)
    return wrapped


def record_result(result):
    timing=result.get('performance')
    if not timing:return
    total=result.get('native_capture',{}).get('processing_ms',result.get('processing_ms'))
    row=dict(timing,at=round(time.time()*1000),status=result.get('status'),
             path=result.get('recognition_path',result.get('method','unknown')))
    row['stages_ms']=dict(timing['stages_ms'])
    if total is not None:
        row['processing_ms']=total
        row['stages_ms']['采集与预处理']=round(max(0.,total-timing['recognition_ms']),2)
    with _lock:_recent.append(row)


def snapshot():
    with _lock:return {'frames':list(_recent)}
