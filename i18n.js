/* Presentation-only localization: map IDs, coordinates and matching stay unchanged. */
const I18N = (() => {
 const pairs = {
 '伊莫 · 地宫领航':'Aniimo · Map Navigator','地宫领航':'Map Navigator','准备识别…':'Preparing…','新一局':'New run','专注地图':'Focus map','显示控制台':'Show controls',
 '可缩放地宫地图':'Zoomable dungeon map','地宫地图':'Dungeon map','领航控制台':'Navigator controls','本地地图':'Local map','全图浏览':'Map overview','自动跟随所在分区':'Follow current region','全岛总览':'Island overview','当前分区':'Current region','放大地图':'Zoom in','缩小地图':'Zoom out','全岛':'Entire island','全图':'Fit map',
 '画面范围':'Visible area','角色位置':'Player position','滚轮缩放 · 拖动平移':'Scroll to zoom · Drag to pan','地图加载中':'Loading map','素材：Wikily /《伊莫》':'Maps: Wikily / Aniimo','探索领航':'Navigator','未连接画面':'Not connected','当前识别':'CURRENT MATCH','自动追踪黄色角色箭头':'Tracks the yellow player arrow','等待游戏画面':'Waiting for game capture',
 '选择游戏窗口并打开地图。请保留黄门、蓝门，迷雾无需裁掉。':'Select the game window and open its map. Keep both doors visible; no need to crop the fog.',
 '游戏画面':'Game capture','仅在本机处理':'Processed locally','选择游戏窗口':'Select game window','停止':'Stop','游戏悬浮窗':'Game overlay','关闭悬浮窗':'Close overlay','置顶半透明地图 · 识别地宫后同步显示':'Transparent overlay · Syncs after dungeon recognition','Alt+Shift+M 切换鼠标穿透 · Alt+Shift+H 隐藏/显示':'Alt+Shift+M: click-through · Alt+Shift+H: show/hide','等待连接游戏窗口':'Waiting for game window','也可直接 Ctrl+V 粘贴截图':'Or paste a screenshot with Ctrl+V','导入截图':'Import screenshot','立即识别':'Identify now','间隔越长，识别次数越少；笔记本可选 0.5 秒或 1 秒。':'Longer intervals reduce scan frequency. Try 0.5s or 1s on laptops.','识别间隔':'Scan interval','海岛模式':'Island mode','普通抢蛋':'Egg Heist','小队模式':'Team mode','地图点位':'Map markers','按需显示':'Choose what to show','地图在本地 · 探索由你决定':'Local maps · Explore your way',
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
 try { const saved=localStorage.getItem('aniimo-language'); language=saved==='en'?'en':saved==='zh-CN'?'zh-CN':navigator.language?.startsWith('zh')?'zh-CN':'en'; } catch {}
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
