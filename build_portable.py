"""Build an explicit-allowlist, relocatable Windows portable folder and ZIP."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

ROOT=Path(__file__).resolve().parent
SOURCE_RUNTIME=Path(sys.executable).parent
OUTPUT=ROOT/'portable'/'aniimo_map_helper_v0.4.1'
if OUTPUT.exists(): raise SystemExit('Output exists; choose a new version before rebuilding.')
APP=OUTPUT/'app'; RUNTIME=OUTPUT/'runtime'
APP.mkdir(parents=True); (RUNTIME/'Lib/site-packages').mkdir(parents=True)
for name in ('hotkeys.py','hotkey-settings.js','native_capture.py','capture_process.py','server.py','image_io.py','matcher.py','loot_detector.py','door_matcher.py','player.py','minimap.py','relocalizer.py','route_planner.py','overlay_bridge.py','overlay_window.py','index.html','app.js','assist.js','i18n.js','style.css'):
    shutil.copy2(ROOT/name,APP/name)
(APP/'data').mkdir()
catalog=json.loads((ROOT/'data/catalog.json').read_text(encoding='utf-8'))
for name in ['catalog.json','player-egg-template.png']+[m['id']+ext for m in catalog for ext in ('.json','.webp')]:
    shutil.copy2(ROOT/'data'/name,APP/'data'/name)
(APP/'data/icons').mkdir()
icon_manifest=json.loads((ROOT/'data/icons/manifest.json').read_text(encoding='utf8'))
for name in {'manifest.json'}|{Path(v['file']).name for v in [*icon_manifest['categories'].values(),*icon_manifest.get('creatures',{}).values()]}:
    shutil.copy2(ROOT/'data/icons'/name,APP/'data/icons'/name)
for file in SOURCE_RUNTIME.iterdir():
    if file.is_file() and (file.suffix.lower() in ('.exe','.dll','.pyd','.zip','.cat') or file.name=='LICENSE.txt'):
        shutil.copy2(file,RUNTIME/file.name)
(RUNTIME/'python313._pth').write_text('python313.zip\n.\nLib/site-packages\n../app\nimport site\n',encoding='utf-8')
packages=SOURCE_RUNTIME/'Lib/site-packages'
for item in packages.iterdir():
    if item.name in ('numpy','numpy.libs','cv2','PIL') or (item.name.endswith('.dist-info') and item.name.startswith(('numpy-','opencv_','pillow-'))):
        shutil.copytree(item,RUNTIME/'Lib/site-packages'/item.name,ignore=shutil.ignore_patterns('__pycache__','tests','test','*.pyc'))
for item in (ROOT/'vendor').iterdir():
    if item.is_dir():shutil.copytree(item,RUNTIME/'Lib/site-packages'/item.name,ignore=shutil.ignore_patterns('__pycache__','tests','test','*.pyc'))
compiler=Path('C:/Windows/Microsoft.NET/Framework64/v4.0.30319/csc.exe')
for output,defines in [('启动助手.exe',[]),('退出助手.exe',['/define:STOP'])]:
    subprocess.run([str(compiler),'/nologo','/target:winexe','/reference:System.Windows.Forms.dll','/reference:System.Management.dll','/out:'+str(OUTPUT/output),*defines,str(ROOT/'portable_launcher.cs'),str(ROOT/'exit_all.cs')],check=True)
(OUTPUT/'使用说明.txt').write_text('''伊莫 · 地宫领航 便携版 v0.4.1（Windows 10/11 x64）

启动时若有其他版本正在运行，会询问是否切换；同意后需重新选择游戏窗口。
首次打开默认中文。可在右上角切换 English，手动选择的语言偏好自动保存。

1. 解压整个文件夹到可写目录，例如桌面。不要在压缩包内直接运行。
2. 双击“启动助手.exe”，浏览器会打开 http://127.0.0.1:18731。
3. 建议使用 Chrome 或 Edge。点击“本地采集”，选择伊莫窗口并连接。实时画面统一使用本地采集，仍可导入截图；图像只在本机处理。
4. 进入地宫后打开大地图，确认地图和角色位置；关闭后由小地图继续追踪。
5. 点击“游戏悬浮窗”可在游戏上方显示地图。保持网页与本地采集开启。
6. 拖动悬浮窗标题栏移动，拖动边缘或右下角等比例缩放，大小和位置自动记忆；− / + 调整透明度；Alt+Shift+M 切换鼠标穿透；Alt+Shift+H 隐藏/显示。
   Alt+Shift+↑ 增加不透明度，Alt+Shift+↓ 增加透明度。“游戏悬浮窗”下展开“快捷键设置”，可修改四项组合，保存后实时生效并记忆。组合被占用时提示冲突并保留原来的可用快捷键；支持恢复默认。
7. 用完后双击“退出助手.exe”，退出本机当前桌面会话内所有目录、所有版本的助手后台、本地采集与悬浮窗，释放相关端口；无需从原目录退出。不批量结束其他 Python 程序。使用旧版浏览器分享时，请同时关闭旧版标签页或点“停止共享”。

地图点位中的“图标大小”可选 50%、70%、85%、100%、125%；默认 85%，网页与悬浮窗同步，选择自动保存。
特殊房间使用怪物图标；限时挑战使用独立的游戏图标，默认显示，可在“地图点位”中关闭。已收录 21 张地宫的 35 个参考位置，来自小队模式资料；多个候选位置不代表同时出现，以当前对局为准。未取得资料的地图不推测挑战点位。两类图标的显示开关与大小均实时同步到悬浮窗。
“实时定位”开关可暂停小地图追踪和彩虹掉落检测，保留当前位置；关闭时最快每秒检查一次大地图。重新开启请打开大地图校准。
跑图时优先读取小地图，打开大地图时自动恢复完整画面识别；约每 5 秒随识别周期核对完整画面。彩虹掉落检测使用最长边 800 像素的场景预览。无需额外设置，本地采集仍读取完整游戏窗口。
识别与同步改进：补强主门入口识别；小地图失去位置后尝试重新搜索，连续确认后恢复；地图底图缓存，人物位置单独更新。不能确认时仍保留上次位置。
新功能：
悬浮窗补上拖动、缩放中断后的鼠标捕获释放，以及松键检查、隐藏和关闭时的释放保护；通过模拟消息回归，Alt+Tab / Windows 键反馈仍需原反馈设备复测。
海岛仅保留普通抢蛋模式，不再提供小队海岛选择。识别间隔默认 0.5 秒；旧自动性能偏好首次更新时迁移到 0.5 秒，其他手动间隔保留。仍可手动选择“自动性能”，按近期处理耗时调整，并在确认静止后降低频率；手动设置保留。该档估算处理负担，不直接读取 CPU 占用率。
位置状态明确区分确认、保留、重新定位和关闭，并显示距上次确认的时间。
跑图辅助改为蛋巢遍历：点击“规划 / 重新规划路线”，从当前位置出发遍历全部未完成蛋巢，不必返回起点。红色路线和编号表示顺序，深蓝色记录已走轨迹。隐藏图标不影响规划；标记拾取后重算剩余路线，沿路线移动仅消退走完的红线，保留深蓝轨迹；连续多次确认明显偏航后自动重新规划，自动重算至少间隔 10 秒。背包遮挡或定位跳变不会直接抹掉未观察路段。当前地图库使用精确最短顺序计算，最优性仅针对可连通的底图网格；无法确认通道的蛋巢单独提示，不画穿墙连线。
参考路线仅按底图通道计算，无法确认连通时不画路线；门锁、高低差、机关仍需游戏内核对。海岛暂不提供参考路线。
“标记已拾取”由玩家手动确认，可撤销；不会因为经过附近自动标记。默认隐藏完成点位，网页与悬浮窗同步。
深蓝色轨迹显示已确认位置附近，最多保留最近 600 个轨迹点，不代表游戏全部探索范围。定位丢失时不延伸，恢复后不跨越未知段连线。
确认识别到不同地图（或手动确认另一张地图）后，自动清空旧轨迹、拾取、掉落和路线记录，再使用新位置。候选预览、遮挡、同一张地图重新校准不会清空。下一局恰好为同一张图时仍请点“新一局”；重新连接采集或刷新也会清空。个人显示与采集设置保留。不会保存在云端。
本版通过已有截图、移动回放、模拟慢速处理、地图通道和界面回归验证；尚未进行新的游戏实测。
悬浮窗底色优化：纯黑空白透明，深灰背景减淡；地形亮部与点位图标保留，逐像素处理结果缓存。
高清悬浮窗：底图按原始像素传递（最长边上限 2048），直接按实际窗口像素绘制，移除了 700 → 520 → 放大的模糊流程。图标显示比例保持不变，已有图标大小设置仍同步生效。底图与按窗口尺寸缩放的图像会缓存，移动仍只同步人物与路线数据；未变化的画面跳过重绘。不增加截图或识别频率，但高清缓存会增加部分内存占用。原素材本身的细节仍是清晰度上限。
本地采集按所选识别间隔处理画面；无新帧时保留位置，画面恢复后自动继续。识别请求等待 15 秒后中断等待并重试，服务端不堆积识别任务。
移动恢复保留原有地形阈值和歧义检查；较长间隔下接受更大移动前，还需两帧地形运动一致。重复房间、遮挡或高台缺少素材时仍可能暂停定位。
采集兼容策略：Win10 / Win11 均先尝试正常参数，仅当接口明确报告不支持时，分别停用最小更新间隔或改用系统默认光标设置；保留原生读回跳帧。记录采集库加载、对象创建、跳帧设置和 Windows 捕获线程启动阶段。部分 Win10 设备的 0xC0000409 启动崩溃仍未解决；本版保留进程隔离和详细报错，不包含尚未完成的 DXGI 采集。
本地采集在独立进程运行：普通错误直接显示采集库返回的信息；采集进程异常退出时显示发生阶段和退出码，网页服务继续运行。退出码不能单独确定具体驱动或根因。启动或读取超过 10 秒无响应时终止该采集进程，允许重新连接。网页遇到连接错误时自动检查后台是否可达，并保留原始错误。画面通过本机共享内存传递，识别前复制一份稳定图像，增加少量内存和复制开销。
本地采集使用 Windows Graphics Capture / windows-capture 2.0.1，不需要浏览器屏幕共享。原始图像直接交给本地识别，网页仅接收结果和每秒最多一次的小预览。本版包含原生采集节流补丁，多余帧在 GPU 读回、内存映射和 Python 回调之前跳过。保留帧仍读取整个窗口，尚非纯 GPU 小区域采集；性能收益取决于设备和驱动。如果系统不支持最小更新间隔，将自动使用兼容模式，仍按所选间隔识别，并使用原生跳帧减少读回开销；切换间隔无需重启兼容采集。兼容模式不能限制 Windows 底层出帧。其他采集错误仍会提示，请停止后重新连接。
本地模式的读取节奏由服务端控制，避免普通后台网页定时器降频；仍需保持网页运行。关闭网页、标签页被系统冻结或丢弃后约 20 秒自动释放，需要重新连接。最小化、窗口关闭或无新帧时保留位置，不使用旧画面确认新位置。采集仅在手动选择窗口并连接后开始。停止按钮立即结束采集。
本版已用独立 Windows 窗口回放真实截图，验证大地图校准转小地图追踪、DPI 裁剪和间隔切换；尚需真实游戏全屏、不同显卡和低配置电脑实测，不能承诺所有设备都更快或解决所有丢失。
整个文件夹均需保留；无需安装 Python、无需管理员权限、不写入开机启动。
首次启动会索引 32 张地图，请等待“本地识别就绪”。可选择 0.25 秒、0.5 秒、1 秒、2 秒或 3 秒识别间隔，自动保存；首次使用默认 0.5 秒，已有手动选择会保留；实际速度取决于机器。
彩虹掉落提示（试用）：连续识别到疑似光柱且小地图定位有效时，记录发现时玩家所在位置附近；非掉落物精确坐标，可能误报。网页地图与悬浮窗同步显示，可移除或清空，新一局清空。刷新页面也会清空。
海岛普通模式已有截图校准，小队海岛和不同分辨率仍需更多实测。
图片在本机处理，不上传云端；日志和进程号可能写在 app 目录。
这是未签名的便携版。如出现系统发布者提示，请先确认文件来源。

地图及点位来源：Wikily /《伊莫》。相关素材的权利归原权利人所有。
第三方运行库许可保留在 runtime/LICENSE.txt 及 runtime/Lib/site-packages 下的 *.dist-info 目录。
''',encoding='utf-8-sig')
shutil.copy2(ROOT/'README_EN.md',OUTPUT/'README_EN.md')
shutil.copy2(ROOT/'THIRD_PARTY_NOTICES.md',OUTPUT/'THIRD_PARTY_NOTICES.md')
archive=Path(str(OUTPUT)+'.zip')
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for file in OUTPUT.rglob('*'):
        if file.is_file(): z.write(file,file.relative_to(OUTPUT.parent))
print(json.dumps({'folder':str(OUTPUT),'zip':str(archive),'bytes':archive.stat().st_size},ensure_ascii=False),flush=True)
