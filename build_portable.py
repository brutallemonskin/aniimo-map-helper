"""Build an explicit-allowlist, relocatable Windows portable folder and ZIP."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

ROOT=Path(__file__).resolve().parent
SOURCE_RUNTIME=Path(sys.executable).parent
OUTPUT=ROOT/'portable'/'AniimoNavigator-Portable-v0.3.1'
if OUTPUT.exists(): raise SystemExit('Output exists; choose a new version before rebuilding.')
APP=OUTPUT/'app'; RUNTIME=OUTPUT/'runtime'
APP.mkdir(parents=True); (RUNTIME/'Lib/site-packages').mkdir(parents=True)
for name in ('server.py','image_io.py','matcher.py','door_matcher.py','player.py','minimap.py','overlay_bridge.py','overlay_window.py','index.html','app.js','i18n.js','style.css'):
    shutil.copy2(ROOT/name,APP/name)
(APP/'data').mkdir()
catalog=json.loads((ROOT/'data/catalog.json').read_text(encoding='utf-8'))
for name in ['catalog.json','player-egg-template.png']+[m['id']+ext for m in catalog for ext in ('.json','.webp')]:
    shutil.copy2(ROOT/'data'/name,APP/'data'/name)
for file in SOURCE_RUNTIME.iterdir():
    if file.is_file() and (file.suffix.lower() in ('.exe','.dll','.pyd','.zip','.cat') or file.name=='LICENSE.txt'):
        shutil.copy2(file,RUNTIME/file.name)
(RUNTIME/'python313._pth').write_text('python313.zip\n.\nLib/site-packages\n../app\nimport site\n',encoding='utf-8')
packages=SOURCE_RUNTIME/'Lib/site-packages'
for item in packages.iterdir():
    if item.name in ('numpy','numpy.libs','cv2','PIL') or (item.name.endswith('.dist-info') and item.name.startswith(('numpy-','opencv_','pillow-'))):
        shutil.copytree(item,RUNTIME/'Lib/site-packages'/item.name,ignore=shutil.ignore_patterns('__pycache__','tests','test','*.pyc'))
compiler=Path('C:/Windows/Microsoft.NET/Framework64/v4.0.30319/csc.exe')
for output,defines in [('启动助手.exe',[]),('退出助手.exe',['/define:STOP'])]:
    subprocess.run([str(compiler),'/nologo','/target:winexe','/reference:System.Windows.Forms.dll','/out:'+str(OUTPUT/output),*defines,str(ROOT/'portable_launcher.cs')],check=True)
(OUTPUT/'使用说明.txt').write_text('''伊莫 · 地宫领航 便携版 v0.3.1（Windows 10/11 x64）

可在右上角选择中文或 English，语言偏好自动保存。

1. 解压整个文件夹到可写目录，例如桌面。不要在压缩包内直接运行。
2. 双击“启动助手.exe”，浏览器会打开 http://127.0.0.1:18731。
3. 建议使用 Chrome 或 Edge。点击“选择游戏窗口”，选择完整游戏窗口。
4. 进入地宫后打开大地图，确认地图和角色位置；关闭后由小地图继续追踪。
5. 点击“游戏悬浮窗”可在游戏上方显示地图。保持网页与共享开启。
6. 拖动悬浮窗标题栏移动，拖动边缘或右下角等比例缩放，大小和位置自动记忆；− / + 调整透明度；Alt+Shift+M 切换鼠标穿透；Alt+Shift+H 隐藏/显示。
7. 用完后双击“退出助手.exe”。仅关闭网页不会退出本地识别服务。

整个文件夹均需保留；无需安装 Python、无需管理员权限、不写入开机启动。
首次启动会索引 33 张地图，请等待“本地识别就绪”。默认读取间隔 0.25 秒，实际速度取决于机器。
海岛普通模式已有截图校准，小队海岛和不同分辨率仍需更多实测。
图片在本机处理，不上传云端；日志和进程号可能写在 app 目录。
这是未签名的测试版。如出现系统发布者提示，请先确认文件来源。

地图及点位来源：Wikily /《伊莫》。相关素材的权利归原权利人所有。
第三方运行库许可保留在 runtime/LICENSE.txt 及 runtime/Lib/site-packages 下的 *.dist-info 目录。
''',encoding='utf-8-sig')
shutil.copy2(OUTPUT/'启动助手.exe',OUTPUT/'Start Navigator.exe')
shutil.copy2(OUTPUT/'退出助手.exe',OUTPUT/'Exit Navigator.exe')
shutil.copy2(ROOT/'README_EN.md',OUTPUT/'README_EN.md')
shutil.copy2(ROOT/'THIRD_PARTY_NOTICES.md',OUTPUT/'THIRD_PARTY_NOTICES.md')
archive=Path(str(OUTPUT)+'.zip')
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for file in OUTPUT.rglob('*'):
        if file.is_file(): z.write(file,file.relative_to(OUTPUT.parent))
print(json.dumps({'folder':str(OUTPUT),'zip':str(archive),'bytes':archive.stat().st_size},ensure_ascii=False),flush=True)
