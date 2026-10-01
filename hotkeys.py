"""Validated overlay shortcuts, persistence, and transactional Win32 registration."""
import copy
import json
import threading
from pathlib import Path

ACTIONS=('toggle_lock','toggle_hidden','opacity_up','opacity_down')
LABELS=dict(zip(ACTIONS,('鼠标穿透','隐藏 / 显示','增加不透明度','增加透明度')))
DEFAULTS=dict(zip(ACTIONS,('Alt+Shift+M','Alt+Shift+H','Alt+Shift+Up','Alt+Shift+Down')))
MODIFIERS={'Alt':1,'Ctrl':2,'Shift':4}
KEYS={**{chr(k):k for k in range(65,91)},**{str(k):48+k for k in range(10)},
      **{'F'+str(k):111+k for k in range(1,12)},'Up':38,'Down':40,'Left':37,'Right':39,
      'PageUp':33,'PageDown':34,'Home':36,'End':35,'Insert':45,'Delete':46}

def parse_binding(text):
    if not isinstance(text,str) or len(text)>40:raise ValueError('无效快捷键')
    parts=text.split('+');mods=parts[:-1];key=parts[-1]
    if not mods or len(set(mods))!=len(mods) or any(m not in MODIFIERS for m in mods) or key not in KEYS:
        raise ValueError('请选择 Ctrl 或 Alt 配合字母、数字、方向键或 F1–F11')
    bits=sum(MODIFIERS[m] for m in mods)
    if not bits&3:raise ValueError('快捷键至少需要 Ctrl 或 Alt')
    if bits==1 and key=='F4':raise ValueError('Alt+F4 是系统关闭快捷键，请换一个组合')
    canonical='+'.join(m for m in ('Ctrl','Alt','Shift') if m in mods)+'+'+key
    return canonical,bits,KEYS[key]

def validate(bindings):
    if not isinstance(bindings,dict) or set(bindings)!=set(ACTIONS):raise ValueError('请设置全部四项快捷键')
    result={action:parse_binding(bindings[action])[0] for action in ACTIONS}
    if len(set(result.values()))!=len(ACTIONS):raise ValueError('快捷键不能重复，请为每项选择不同组合')
    return result

class HotkeyBindings:
    def __init__(self,register,unregister):
        self.register=register;self.unregister=unregister;self.active={}

    def release(self):
        for action in list(self.active):self.unregister(ACTIONS.index(action)+1)
        self.active={}

    def apply(self,bindings):
        desired=validate(bindings);previous=dict(self.active)
        if desired==previous:return {'ok':True,'active':previous,'error':''}
        self.release();failed=[]
        for action,value in desired.items():
            _,mods,key=parse_binding(value)
            if self.register(ACTIONS.index(action)+1,mods|0x4000,key):self.active[action]=value
            else:failed.append(action)
        if not failed:return {'ok':True,'active':dict(self.active),'error':''}
        error='快捷键被占用或不可用：'+'、'.join(LABELS[a]+' ('+desired[a]+')' for a in failed)
        if previous:
            self.release();missing=[]
            for action,value in previous.items():
                _,mods,key=parse_binding(value)
                if self.register(ACTIONS.index(action)+1,mods|0x4000,key):self.active[action]=value
                else:missing.append(action)
            error+='；已保留原来的可用快捷键'
            if missing:error+='；部分原快捷键也已被占用，请重新设置'
        else:error+='；其他可用快捷键已启用'
        return {'ok':False,'active':dict(self.active),'error':error}

class HotkeySettings:
    def __init__(self,root):
        self.path=Path(root)/'overlay-hotkeys.json';self.lock=threading.RLock()
        try:self.value=validate(json.loads(self.path.read_text(encoding='utf8')))
        except (OSError,ValueError,TypeError):self.value=dict(DEFAULTS)
        self.target=dict(self.value);self.revision=0;self.pending=False;self.active=None;self.error=''

    def _save(self,value):
        temporary=self.path.with_suffix('.tmp')
        temporary.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf8')
        temporary.replace(self.path)

    def status(self):
        with self.lock:return copy.deepcopy({'bindings':self.target if self.pending else self.value,'defaults':DEFAULTS,
            'active':self.active,'pending':self.pending,'error':self.error,'revision':self.revision})

    def config(self):
        with self.lock:return {'revision':self.revision,'bindings':dict(self.target)}

    def started(self):
        with self.lock:self.revision+=1;self.target=dict(self.value);self.pending=True;self.active=None;self.error=''

    def stopped(self):
        with self.lock:self.revision+=1;self.target=dict(self.value);self.pending=False;self.active=None

    def configure(self,bindings,running):
        value=validate(bindings)
        with self.lock:
            if running and self.pending:raise ValueError('正在应用快捷键，请稍后再试')
            if not running:self._save(value);self.value=dict(value)
            self.revision+=1;self.target=value;self.pending=running;self.error=''
            return self.status()

    def report(self,data):
        with self.lock:
            if type(data.get('revision')) is not int or data['revision']!=self.revision:return self.status()
            active=data.get('active');error=data.get('error','');ok=data.get('ok')
            if (not isinstance(active,dict) or not set(active)<=set(ACTIONS) or type(ok) is not bool or
                not isinstance(error,str) or len(error)>600):raise ValueError('无效快捷键状态')
            active={k:parse_binding(v)[0] for k,v in active.items()}
            if len(set(active.values()))!=len(active) or (ok and active!=self.target):raise ValueError('无效快捷键状态')
            self.active=active;self.pending=False;self.error=error
            if ok:
                self.value=dict(self.target)
                try:self._save(self.value)
                except OSError:self.error='快捷键已应用，但保存失败；请检查助手目录是否可写'
            else:self.target=dict(self.value)
            return self.status()
