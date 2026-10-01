/* Presentation-only localization: map IDs, coordinates and matching stay unchanged. */
const I18N = (() => {
 const pairs = {
 '本地采集（试用）':'Local capture (trial)','本地低开销采集':'Local low-overhead capture',
 '请选择游戏窗口':'Select the game window','游戏窗口':'Game window','刷新列表':'Refresh list','连接':'Connect','取消':'Cancel',
 '正在读取可用窗口…':'Loading available windows…',
 '请选择伊莫游戏窗口。仅在本机读取，停止后立即结束采集。':'Select the Aniimo window. Frames stay on this computer; Stop ends capture.',
 '没有可用窗口，请先打开游戏。':'No available windows. Open the game first.',
 '无需浏览器屏幕共享。首次连接后请打开大地图校准；不兼容时可继续使用浏览器分享。':'Browser screen sharing is not required. Open the full map to calibrate after connecting. Browser sharing remains available for compatibility.',
 '正在连接本地采集…':'Connecting local capture…','本地采集中':'Local capture active',
 '本地采集已连接，请打开游戏大地图校准。':'Local capture connected. Open the game map to calibrate.',
 '等待本地画面':'Waiting for local frames','本地画面未更新 · 等待恢复':'Local frames paused · Waiting to resume',
 '窗口已最小化 · 保留位置':'Window minimized · Position held','画面未更新 · 等待恢复':'Frames paused · Waiting to resume',
 '本地采集暂未收到新画面，请保持游戏窗口打开；持续无画面可改用浏览器分享。':'No new local frames. Keep the game window open; use browser sharing if this persists.',
 '视频帧暂未更新，已保留位置。请确认游戏未最小化；画面恢复后会自动继续，持续无画面时请重新选择窗口。':'No new video frames; position held. Keep the game visible. Tracking resumes when frames arrive; select the window again if needed.',
 '识别等待超时或已停止，下一次读取会自动重试':'Recognition timed out or stopped; the next scan retries automatically',

 "已确认偏航，正在重新规划":"Deviation confirmed; replanning",
"蛋巢遍历路线":"Egg nest tour",
"规划 / 重新规划路线":"Plan / replan tour",
"点击地图点位可标记已拾取":"Click a marker to mark it collected",
"开启后规划全部蛋巢路线":"Enable to plan a tour of all egg nests",
"本图蛋巢已全部完成或暂无蛋巢":"All nests completed, or no nests on this map",
"底图最短遍历路线":"Shortest atlas tour",
"底图优化遍历路线":"Optimized atlas tour",
"路线覆盖蛋巢":"Nests covered",
"无法确认连通":"Connection unconfirmed",
"当前位置无法接入底图通道，请移动后重新规划。":"Cannot connect this position to atlas passages. Move and replan.",
"显示已走过路线":"Show traveled route",
"从当前位置出发，遍历全部未完成蛋巢，不必返回起点。按红色编号依次前往；隐藏图标不影响规划。已走完的红线路段自动消退，深蓝轨迹保留；持续偏航后自动重算，避免频繁跳线。蛋巢仍需手动确认拾取。门锁、高低差和机关需游戏内核对。":"Visit all unfinished nests from your position without returning to the start. Follow the red numbers. Hidden markers are included. Traveled red segments fade; the blue trail stays. Sustained deviations replan with a cooldown. Confirm collection manually. Check locks, elevation and mechanisms in game.",
"红色为规划路线，深蓝色为已走轨迹。轨迹只记录已确认的位置，不代表游戏迷雾已全部探索。最多保留最近 600 个轨迹点；本局标记在新一局、重新共享或刷新后清空。":"Red is the planned tour; deep blue is your confirmed trail, not all explored fog. Up to 600 recent points are retained. A new run, new capture or reload clears this session.",
 '自动性能':'Automatic performance','自动调节':'Adaptive interval','手动间隔':'Manual interval','最近处理耗时':'Recent processing time',
 '定位已关闭':'Tracking off','位置已确认':'Position confirmed','正在重新定位':'Reacquiring position','等待地图校准':'Awaiting calibration',
 '仅根据已确认画面更新位置':'Updated from confirmed frames only','距上次确认':'Since last confirmation','打开游戏大地图以确认本局起点':'Open the game map to calibrate this run',
 '跑图辅助':'Expedition guide','下一目标与参考路线':'Next target and reference route','优先目标':'Target preference','宝箱与蛋巢':'Chests and egg nests','黄门与蓝门':'Yellow and blue doors',
 '推荐下一目标':'Recommend next target','参考路线仅按底图通道计算，门锁、高低差和机关需游戏内核对。仅从可见筛选点位中推荐，定位丢失时暂停。':'Routes follow atlas passages only. Check locks, elevation and mechanisms in game. Recommendations use visible markers and pause when position is lost.',
 '点击地图点位可选择目标或标记已拾取':'Click a map marker to choose a target or mark it collected','设为目标':'Set target','标记已拾取':'Mark collected','撤销上次标记':'Undo last mark','隐藏已完成点位':'Hide completed markers','显示已走过区域':'Show visited areas',
 '绿色轨迹只记录已确认的位置附近，不代表游戏迷雾已全部探索。最多保留最近 600 个轨迹点；本局标记在新一局、重新共享或刷新后清空。':'The green trail records confirmed positions, not all explored game fog. Up to 600 recent trail points are retained. A new run, new capture or page reload clears this session.',
 '当前筛选下暂无未完成目标':'No unfinished targets in the current filters','正在计算参考路线':'Calculating a reference route','路线暂不可用，请稍后重试':'Route unavailable; try again later','开启后推荐未完成目标':'Enable to recommend unfinished targets',
 '参考路线暂仅支持地宫':'Reference routes currently support dungeons only','定位未确认，路线暂停':'Position unconfirmed; route paused','等待当前位置':'Waiting for position','已接近目标，请自行确认拾取':'Near the target; confirm collection yourself','选中点位':'Selected marker','当前目标':'Current target','尚未选择目标':'No target selected','本图已完成':'Completed on this map',
 '底图暂不能确认连通路线，请在游戏内核对。':'The atlas cannot confirm a connected route. Check in game.','底图参考路线 · 门锁和高低差需游戏内核对':'Atlas reference route · Check locks and elevation in game',
 '已连续确认新位置，小地图追踪已恢复。':'Position confirmed across frames; minimap tracking resumed.',
 '已找到可能位置，等待下一帧确认。':'Possible position found; waiting for the next frame to confirm.',
 '起点超出地图，正在尝试重新定位。':'The previous position is outside the map; trying to locate you again.',
 '小地图比例不匹配，正在尝试重新定位。':'Minimap scale mismatch; trying to locate you again.',
 '小地图地形暂不明确，保留上次位置；正在尝试重新定位。':'Terrain is unclear. Keeping the last position while trying to locate you again.',
 '大地图位置已更新 · 实时定位已关闭':'Full-map position updated · Live tracking off',
 '实时定位':'Live tracking','70% · 较小':'70% · Smaller','85% · 默认':'85% · Default','125% · 更大':'125% · Larger',
 '关闭可降低持续计算：保留位置，只检查大地图（最快每秒一次），暂停小地图追踪和彩虹掉落标记。重新开启后请打开大地图校准。选择自动保存。':'Turn off to reduce ongoing processing: keep the last position and check only for the full map, at most once per second. Minimap tracking and loot marking pause. Reopen the full map to recalibrate after enabling. Your choice is saved.',
 '实时定位已关闭 · 仅识别大地图':'Live tracking off · Full map only',
 '当前位置已保留。打开大地图仍可识别地图和位置；彩虹掉落自动标记暂停。':'Last position retained. Full-map recognition remains available; automatic loot marking is paused.',
 '实时定位关闭，自动掉落标记暂停':'Live tracking off · Loot marking paused',
 '实时定位已开启 · 请打开大地图校准':'Live tracking on · Open the full map to calibrate',
 '请重新打开大地图确认当前位置，再继续小地图追踪。':'Reopen the full map to confirm your position before resuming minimap tracking.',
 '实时定位已关闭；打开大地图仍可识别地图和位置。':'Live tracking is off; open the full map to identify your map and position.',
 '无效实时定位选项':'Invalid live-tracking option',

 '图标大小':'Icon size','50% · 更小':'50% · Smallest','70% · 默认':'70% · Default','85% · 适中':'85% · Medium','100% · 原大小':'100% · Original',
 '网页与悬浮窗同步，选择自动保存。':'Applies to the web map and overlay. Your choice is saved.',

"彩虹掉落提示":"Rainbow loot hints",
"试用":"Experimental",
"自动标记疑似光柱":"Mark suspected loot beams automatically",
"等待光柱出现":"Watching for loot beams",
"看到疑似光柱，等待当前位置确认":"Suspected beam seen; waiting for a fresh player position",
"此处已记录，靠近后请自行核对":"Discovery recorded; approach to verify",
"看到疑似光柱，正在连续确认":"Suspected beam seen; confirming across frames",
"已标记发现位置附近 · 非精确坐标":"Discovery vicinity marked · Approximate location",
"当前地图暂无记录":"No discoveries on this map",
"疑似彩虹·附近":"Possible rainbow · Nearby",
"移除":"Remove",
"已拾取或误报时移除":"Remove collected loot or false detections",
"自动标记已暂停":"Automatic marking paused",
"清空本局掉落标记":"Clear this run’s loot markers",
"记录发现时玩家位置附近，非物品精确坐标。可能误报；拾取后请手动移除。新一局自动清空。":"Records the player’s discovery location, not exact loot coordinates. False detections are possible; remove collected loot manually. New run clears all markers.",

 '地图预览 · 尚未确认':'Map preview · Unconfirmed',
 '请选择要共享的游戏窗口':'Choose the game window to share',
 '已授权，正在等待游戏画面':'Permission granted · Waiting for game frames',
 '请切回游戏并保持窗口打开；收到画面后会自动开始识别。':'Return to the game and keep its window open. Recognition starts when frames arrive.',
 '所选窗口的共享已经结束，请重新选择。':'The selected stream has ended. Choose the window again.',
 '共享已取消或未获授权，请重新选择游戏窗口。':'Sharing was cancelled or not permitted. Choose the game window again.',
 '画面播放失败：':'Video playback failed: ',
 '已收到游戏画面，正在识别。':'Game frames received. Recognizing now.',
 '画面暂时暂停，请切回游戏':'Capture paused · Return to the game',
 '读取画面失败：':'Could not read the frame: ',
 '已授权，但 12 秒内未收到游戏画面。请保持游戏窗口打开且不要最小化；仍无画面时，可在共享框中尝试“整个屏幕”。':'Permission granted, but no frames arrived within 12 seconds. Keep the game window open and not minimized. If needed, try sharing the entire screen.',

 '伊莫 · 地宫领航':'Aniimo · Map Navigator','地宫领航':'Map Navigator','准备识别…':'Preparing…','新一局':'New run','专注地图':'Focus map','显示控制台':'Show controls',
 '可缩放地宫地图':'Zoomable dungeon map','地宫地图':'Dungeon map','领航控制台':'Navigator controls','本地地图':'Local map','全图浏览':'Map overview','自动跟随所在分区':'Follow current region','全岛总览':'Island overview','当前分区':'Current region','放大地图':'Zoom in','缩小地图':'Zoom out','全岛':'Entire island','全图':'Fit map',
 '画面范围':'Visible area','角色位置':'Player position','滚轮缩放 · 拖动平移':'Scroll to zoom · Drag to pan','地图加载中':'Loading map','素材：伊莫 / Wikily / AniimoTools / 官方图鉴':'Art: Aniimo / Wikily / AniimoTools / Official wiki','探索领航':'Navigator','未连接画面':'Not connected','当前识别':'CURRENT MATCH','自动追踪黄色角色箭头':'Tracks the yellow player arrow','等待游戏画面':'Waiting for game capture',
 '选择游戏窗口并打开地图。请保留黄门、蓝门，迷雾无需裁掉。':'Select the game window and open its map. Keep both doors visible; no need to crop the fog.',
 '游戏画面':'Game capture','仅在本机处理':'Processed locally','选择游戏窗口':'Select game window','停止':'Stop','游戏悬浮窗':'Game overlay','关闭悬浮窗':'Close overlay','置顶半透明地图 · 识别地宫后同步显示':'Transparent overlay · Syncs after dungeon recognition','Alt+Shift+M 切换鼠标穿透 · Alt+Shift+H 隐藏/显示':'Alt+Shift+M: click-through · Alt+Shift+H: show/hide','等待连接游戏窗口':'Waiting for game window','也可直接 Ctrl+V 粘贴截图':'Or paste a screenshot with Ctrl+V','导入截图':'Import screenshot','立即识别':'Identify now','间隔越长，平均 CPU 占用通常越低，位置更新也越慢；低性能电脑可选 2 秒或 3 秒。':'Longer intervals usually reduce average CPU use but update your position less often. Try 2s or 3s on slower computers.','识别间隔':'Scan interval','海岛模式':'Island mode','普通抢蛋':'Egg Heist','小队模式':'Team mode','地图点位':'Map markers','按需显示':'Choose what to show','地图在本地 · 探索由你决定':'Local maps · Explore your way',
 '等待识别地宫':'Waiting for dungeon','保留上次位置':'Last known position','你的位置':'Your position','等待角色定位':'Locating player','悬浮窗同步失败':'Overlay sync failed','悬浮窗暂未同步，请检查本地服务。':'Overlay is not syncing. Check the local service.','悬浮窗未启动：':'Could not start overlay: ',
 '古代港口':'Ancient Port','东北岛区':'Northeast Island','北部岛区':'North Island','中央岛区':'Central Island','东南岛区':'Southeast Island','西南岛区':'Southwest Island','南部粉色岛区':'South Pink Island','分区地图':'Region map',
 '位置暂未更新':'Position not updated','位置保留':'Position held','画面暂时无法定位，按仍在原处显示。上次定位 ':'Cannot locate the player. Showing the last position from ',' 秒前；地图恢复后自动继续。':' seconds ago; tracking resumes when the map returns.',
 '黄门':'Yellow door','蓝门':'Blue door','先开大地图校准，再用小地图追踪':'Open the full map to calibrate, then track via the minimap','等待主门附近地图':'Waiting for the entrance map','从黄门进入后打开地图，探索更多房间以缩小候选。':'Open the map after entering the yellow door. Explore more rooms to narrow the matches.',
 '你·上次':'You (last)','你':'You','手动':'Manual','匹配范围':'Matched area','截图模式':'Screenshot','持续识别中':'Live scanning','已停止读取游戏画面。':'Game capture stopped.','当前浏览器不支持窗口读取，请用 Chrome 或 Edge 打开本地地址。':'Window capture is unavailable. Open the local page in Chrome or Edge.','窗口共享已结束。':'Window sharing ended.','未开始读取：':'Capture could not start: ','海岛模式已更换，请打开大地图重新校准。':'Island mode changed. Open the full map to recalibrate.',
 '识别失败':'Recognition failed','小地图追踪中 · 每帧重新定位':'Minimap tracking · Updating position','小地图定位暂停':'Minimap tracking paused','实时位置':'Live position','已锁定地图 · 暂未定位':'Map locked · Position unavailable','请先打开大地图':'Open the full map first','正在确认地图与位置':'Confirming map and position','地图索引仍在准备，稍后再识别。':'Map index is still loading. Please try again shortly.',
 '手动位置 · 点重置恢复自动追踪':'Manual position · Reset to resume tracking','已定位角色 · 可关闭大地图继续追踪':'Player located · Close the full map to continue tracking','已看到箭头，但尚未确认地图位置':'Arrow detected; map position not confirmed','当前画面无法定位角色':'Cannot locate the player in this frame','探索推测':'Exploration estimate','当前匹配':'Current match','仍有多个候选':'Multiple possible matches','当前画面无法确认':'No confirmed match','连续探索更支持这张地图，仍请核对主门和岔路。':'Exploration suggests this map. Check the entrance and junctions.',
 '地形分是相对匹配指标，不代表正确概率。':'Terrain scores compare matches; they are not probabilities.','已手动确认':'Manually confirmed','已确认地图，请在大地图上标记角色位置':'Map confirmed. Open the full game map to locate the player.','候选预览':'Candidate preview',' 当前仅预览候选，确认该地图可点击候选卡片开始追踪。':' Preview only. Select a candidate to confirm it and start tracking.','识别暂不可用：':'Recognition unavailable: ','请先打开游戏大地图定位；也可以在分区列表手动选择。':'Open the full game map to locate yourself, or choose a region from the list.','识别引擎异常：':'Recognition engine error: ','识别引擎异常':'Recognition engine error','本地服务未连接':'Local service disconnected','地图加载失败：':'Map failed to load: ',
 '已结合两门位置和可见地形匹配。':'Matched using both doors and visible terrain.','已检测两门；起始房间仍可能重复，请继续探索。':'Both doors detected. Starting rooms may repeat; keep exploring.','画面信息不足，请打开地图并扩大可见区域。':'Not enough detail. Open the map and reveal a larger area.','局部房间可能重复；请走到岔路或扩大地图范围。':'Rooms may repeat. Move to a junction or show more of the map.','已匹配地图形状；请结合入口与房间核对。':'Map shape matched. Check the entrance and rooms.',
 '已看到小地图，请先打开大地图确认本局地图。':'Minimap detected. Open the full map to confirm this run.','小地图遮挡较多，暂时无法确认位置。':'Minimap obstructed; position unavailable.','请先确认地图。':'Confirm the map first.','请打开大地图校准角色起点。':'Open the full map to calibrate the starting position.','起点超出地图，请重新打开大地图校准。':'Starting position is out of bounds. Reopen the full map.','小地图比例不匹配，请打开大地图校准。':'Minimap scale mismatch. Open the full map to recalibrate.','小地图地形暂不明确，位置已隐藏；可打开大地图重新校准。':'Minimap terrain is unclear. Open the full map to recalibrate.','正在用小地图地形更新位置；打开大地图可重新校准。':'Updating from minimap terrain. Open the full map to recalibrate.',
 '地宫外 · 抢蛋海岛':'Island · Egg Heist','地宫外 · 小队海岛':'Island · Team mode','6钥匙奖励房':'6-key reward room','失落地宫':'Sanctum ',
 '侧入口':'Side entrance','入口':'Entrance','极巨黯虹蛋':'Giant egg','伊莫出生点':'Aniimo spawns','撤离传送阵':'Extraction portal','绿色宝箱':'Uncommon chests','蓝钥匙房':'Blue key rooms','蛋巢':'Egg nests','金色宝箱':'Legendary chests','蓝色宝箱':'Rare chests','传送器':'Teleporters','独特房间':'Unique rooms','金钥匙房':'Gold key rooms','紫色宝箱':'Epic chests','紫钥匙房':'Purple key rooms','商人':'Merchants','蛋船':'Egg boats','金币怪出没':'Coin creature spawns','可收集物':'Collectibles','宝箱':'Chests','房间':'Rooms','伊莫':'Aniimo',
 '悬浮窗需要 Windows':'The overlay requires Windows','无效悬浮窗数据':'Invalid overlay data','无效悬浮窗操作':'Invalid overlay action','图片过大':'Image too large','无效图片或图片过大':'Invalid image or image too large','无效位置':'Invalid position','无效追踪地图':'Invalid tracking map','无效追踪位置':'Invalid tracking position','无效小地图比例':'Invalid minimap scale','无效海岛模式':'Invalid island mode'
 };
 const sorted=Object.keys(pairs).sort((a,b)=>b.length-a.length);
 const pattern=new RegExp(sorted.map(s=>s.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')).join('|'),'g');
 let language='zh-CN';
 try { const saved=localStorage.getItem('aniimo-language'); language=saved==='en'?'en':'zh-CN'; } catch {}
 function t(value){
  if(language!=='en'||typeof value!=='string')return value;
  return value.replace(/每 ([\d.]+) 秒/g,'Every $1 s').replace(/(\d+) 张地图 · 本地识别就绪/g,'$1 maps · Ready').replace(/正在索引 (\d+) 张地图…/g,'Indexing $1 maps…').replace(/(\d+) 条点位/g,'$1 markers').replace(/ 已记录 (\d+) 个有变化的探索画面。/g,' $1 distinct exploration frames recorded.').replace(/两门＋地形 (\d+)分/g,'Doors + terrain: $1').replace(/(\d+) 个吻合特征/g,'$1 matching features').replace(/历史首选 (\d+) 次/g,'Top match in $1 frames').replace(/其余 (\d+) 个候选/g,'$1 more candidates').replace(pattern,key=>pairs[key]);
 }
 const originals=new WeakMap(), attrs=new WeakMap();
 function text(node){const old=originals.get(node);const source=old&&node.nodeValue===old.output?old.source:node.nodeValue;const output=t(source);originals.set(node,{source,output});if(node.nodeValue!==output)node.nodeValue=output;}
 function translate(root){
  if(root.nodeType===3){if(!root.parentElement?.closest('script,style,#language'))text(root);return;}
  if(root.nodeType!==1||root.matches('script,style,#language'))return;
  for(const name of ['title','aria-label'])if(root.hasAttribute(name)){const state=attrs.get(root)||{};const value=root.getAttribute(name),old=state[name],source=old&&value===old.output?old.source:value,output=t(source);state[name]={source,output};attrs.set(root,state);if(output!==value)root.setAttribute(name,output);}
  for(const child of root.childNodes)translate(child);
 }
 let observer;
 function observe(){observer.observe(document.documentElement,{childList:true,subtree:true,characterData:true,attributes:true,attributeFilter:['title','aria-label']});}
 function start(){
  observer=new MutationObserver(records=>{observer.disconnect();for(const record of records){if(record.type==='childList'){for(const node of record.addedNodes)translate(node);}else translate(record.target);}observe();});
  const select=document.getElementById('language');select.value=language;
  select.onchange=()=>{language=select.value;try{localStorage.setItem('aniimo-language',language);}catch{}observer.disconnect();document.documentElement.lang=language;translate(document.documentElement);observe();window.dispatchEvent(new Event('languagechange'));};
  document.documentElement.lang=language;translate(document.documentElement);observe();
 }
 return {t,start,get language(){return language;}};
})();
const t=value=>I18N.t(value);
I18N.start();
