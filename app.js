const $=id=>document.getElementById(id), cap=$('capture'), cc=cap.getContext('2d'), canvas=$('map'), ctx=canvas.getContext('2d');
let catalog=[], current=null, bitmap=null, zoom=1, ox=0, oy=0, enabled=new Set(), result=null, mapBounds=null, mapLoadVersion=0;
let frame=null, busy=false, timer=null, running=false, history=[], lastSignature=null, generation=0;
let tracking=null, trackedAt=0, lastKnown=null, confirmedMapId=null;
let lastFullFrameAt=-Infinity,previewFrameAt=0;
let observationSession=Date.now().toString(36)+'-'+Math.random().toString(36).slice(2);
const cadence=new NavigatorTools.AdaptiveCadence(),journal=new NavigatorTools.RunJournal(),routeFollower=new NavigatorTools.RouteFollower();
let recoveryActive=false,navEnabled=false,navTarget=null,selectedPoint=null,navPath=[],navRequest=0,navBusy=false,navAt=0,navOrigin=null,navMessage='',navStops=[],navUnreachable=[];
let navPending=false,navRetryAt=0,navController=null;
function writeText(id,value){const el=$(id);if(el.textContent!==value)el.textContent=value;}
function effectiveInterval(){return $('interval').value==='auto'?cadence.interval:Number($('interval').value)||500;}
function resetNavigation(){clearRoute();journal.reset();cadence.reset();selectedPoint=null;recoveryActive=false;}
function syncQuality(){
 const active=result?.position&&result.id===current?.id&&!result.held;
 const state=!realtimeTracking?'off':active?'tracking':lastKnown?(recoveryActive?'recovering':'held'):'uncalibrated';
 const labels={off:'定位已关闭',tracking:'位置已确认',held:'保留上次位置',recovering:'正在重新定位',uncalibrated:'等待地图校准'};
 const el=$('tracking-quality');writeText('tracking-quality',t(labels[state]));if(el.getAttribute?.('data-state')!==state)el.setAttribute('data-state',state);
 writeText('quality-detail',state==='tracking'?t('仅根据已确认画面更新位置'):lastKnown?t('距上次确认')+' '+Math.max(0,Math.floor((Date.now()-trackedAt)/1000))+' s':t('打开游戏大地图以确认本局起点'));
 writeText('performance-status',($('interval').value==='auto'?t('自动调节')+': '+(effectiveInterval()/1000)+' s · ':t('手动间隔')+' · ')+t('最近处理耗时')+' '+Math.round(cadence.cost)+' ms');
}
function clearRoute(message=''){routeFollower.reset();navRequest++;navController?.abort();navPending=false;navRetryAt=0;navTarget=null;navPath=[];navStops=[];navUnreachable=[];navOrigin=null;navAt=0;navMessage=message;}
function refreshRoute(){
 // Keep the last valid remainder until a replacement has been confirmed.
 navRequest++;navController?.abort();navPending=navEnabled;navRetryAt=0;navAt=0;
 const targets=selectableTargets(),keys=new Set(targets.map(NavigatorTools.pointKey));
 navStops=navStops.filter(s=>keys.has(s.key));navUnreachable=navUnreachable.filter(k=>keys.has(k));
 if(navTarget&&!keys.has(NavigatorTools.pointKey(navTarget)))navTarget=targets.find(p=>NavigatorTools.pointKey(p)===navStops[0]?.key)||null;
 draw();updateRoute(true);
}
function selectableTargets(){
 if(!current)return [];
 const points=typeof RouteGoals!=='undefined'?RouteGoals.targets(current):(current.displayPoints||current.points).filter(p=>p.category==='egg-nests');
 return points.filter(p=>!journal.picked(current.id,p));
}
function unresolvedNestPositions(){
 const keys=new Set(navUnreachable);
 return selectableTargets().filter(p=>keys.has(NavigatorTools.pointKey(p))).map(p=>[p.x,p.y]);
}
async function updateRoute(force=false){
 if(force&&navEnabled){navPending=true;navRetryAt=0;}
 if(!navEnabled||navBusy||!current?.id.startsWith('sanctum-')||!result?.position||result.id!==current.id||result.held)return;
 const now=Date.now(),position=[...result.position];
 if(!force&&(now-navAt<2000||now<navRetryAt))return;
 const reroute=!!navOrigin;
 if(!force&&reroute&&!navPending&&!routeFollower.shouldReplan(position,now))return;
 const targets=selectableTargets();
 if(!targets.length){clearRoute('所选目标已完成或尚未选择目标');navOrigin=position;navAt=now;renderNavigation();return;}
 navBusy=true;navPending=true;navAt=now;routeFollower.attempt(position,now);const token=++navRequest,map=current.id,run=generation;
 const controller=new AbortController();navController=controller;const timeout=setTimeout(()=>controller.abort(),15000);
 navMessage=reroute?'正在更新剩余目标路线':'正在计算参考路线';renderNavigation();
 try{
   const response=await fetch('/api/route',{method:'POST',signal:controller.signal,headers:{'Content-Type':'application/json'},body:JSON.stringify({map,position,mode:'egg-tour',targets:targets.map(p=>({key:NavigatorTools.pointKey(p),position:[p.x,p.y]}))})});
  const out=await response.json();if(!response.ok)throw Error(out.error||'路线暂不可用');
  if(token!==navRequest||run!==generation||map!==current?.id||!navEnabled||result?.held)return;
  const liveKeys=new Set(targets.map(NavigatorTools.pointKey)),nextKeys=new Set((out.stops||[]).map(s=>s.key));
  const losesRemainder=navPath.length>1&&navStops.some(s=>liveKeys.has(s.key)&&!nextKeys.has(s.key));
  const unresolvedKeys=new Set(out.unreachable||[]),accountedKeys=new Set([...nextKeys,...unresolvedKeys]);
  const completeAccounting=accountedKeys.size===liveKeys.size&&[...liveKeys].every(k=>accountedKeys.has(k))&&[...nextKeys].every(k=>!unresolvedKeys.has(k));
  // A confirmed move into a disconnected region may expose previously unreachable nests.
  // Accept only complete accounting; preserve the old tail on malformed partial responses.
  const enteredNewRegion=completeAccounting&&navUnreachable.some(k=>nextKeys.has(k));
  if(!navPath.length&&out.status==='unavailable')navUnreachable=(out.unreachable||[]).filter(k=>liveKeys.has(k));
  if(out.status!=='ok'||!out.path?.length||!completeAccounting||(losesRemainder&&!enteredNewRegion))throw Error(out.reason||'路线暂不可用');
  navPending=false;navRetryAt=0;navOrigin=position;routeFollower.set(out.path,position,Date.now());
  if(result?.position)routeFollower.observe(result.position,Date.now());navPath=routeFollower.remaining();navStops=out.stops||[];navUnreachable=out.unreachable||[];
  navMessage=navUnreachable.length?'部分目标参考路线':out.exact?'底图最短遍历路线':'底图优化遍历路线';
  navTarget=out.status==='ok'?targets.find(p=>NavigatorTools.pointKey(p)===out.target)||null:null;
 }catch(e){if(token===navRequest&&run===generation&&map===current?.id){navPending=true;navRetryAt=Date.now()+5000;navMessage=navPath.length?'新路线暂不可用，保留原路线并自动重试':'路线暂不可用，将自动重试';}}
 finally{clearTimeout(timeout);if(navController===controller)navController=null;navBusy=false;draw();}
}
function renderNavigation(){
 const data=current?journal.map(current.id):{picked:new Map()},picked=data.picked.size;
 const selected=selectedPoint&&selectedPoint.map===current?.id?selectedPoint.point:navTarget;
 const eligible=selected&&!journal.picked(current?.id,selected);
 $('nav-pick').disabled=!eligible;$('nav-undo').disabled=!picked;
 writeText('nav-selected',selected?t('选中点位')+': '+pointName(selected):t('点击地图点位可标记已拾取'));
 const held=result?.held||!result?.position||result.id!==current?.id;
 let message=!navEnabled?'开启后规划所选目标路线':!current?.id.startsWith('sanctum-')?'参考路线暂仅支持地宫':held?'定位未确认，路线暂停':navMessage||'等待当前位置';
 if(navEnabled&&!held&&navTarget&&Math.hypot(navTarget.x-result.position[0],navTarget.y-result.position[1])<30)message='已接近目标，请自行确认拾取';
 const unresolved=unresolvedNestPositions().length;
 if(navEnabled&&unresolved)message+=' · '+t('仍有未覆盖目标，请查看黄色问号')+' '+unresolved;
 writeText('nav-status',t(message));writeText('nav-target',t('路线覆盖目标')+' '+navStops.length+' / '+selectableTargets().length+(unresolved?' · '+t('无法确认连通')+' '+unresolved:''));
 writeText('nav-count',t('本图已完成')+' '+picked);
}
function navigationLayer(project=p=>p){
 if(!current||result?.id!==current.id)return {trail:[],path:[],target:null,stops:[],held:true};
 const trail=$('trail-enabled').checked?journal.map(current.id).trail.map(p=>p?project(p):null):[];
 return {trail,stops:navEnabled?navStops.map(s=>project(s.position)):[],unreachable:navEnabled?unresolvedNestPositions().map(project):[],path:navEnabled?navPath.map(project):[],target:navEnabled&&navTarget?project([navTarget.x,navTarget.y]):null,held:!!result.held};
}
function paintNavigation(context,z){
 const layer=navigationLayer();context.save();context.lineCap='round';context.lineJoin='round';
 context.strokeStyle=layer.held?'#a8323899':'#d63840';context.lineWidth=3/z;context.beginPath();layer.path.forEach((p,i)=>i?context.lineTo(...p):context.moveTo(...p));context.stroke();
 context.strokeStyle='#2459bddd';context.lineWidth=5/z;context.beginPath();let next=true;
 for(const p of layer.trail){if(!p){next=true;continue;}if(next){context.moveTo(...p);context.lineTo(p[0]+.01,p[1]);next=false;}else context.lineTo(...p);}context.stroke();
 context.font=`bold ${11/z}px sans-serif`;context.textAlign='center';context.textBaseline='middle';
 layer.stops.forEach((p,i)=>{const x=p[0]+12/z,y=p[1]-12/z;context.fillStyle='#ba252f';context.beginPath();context.arc(x,y,8/z,0,Math.PI*2);context.fill();context.fillStyle='#fff';context.fillText(String(i+1),x,y);});
 (layer.unreachable||[]).forEach(p=>{context.strokeStyle='#ffcd48';context.lineWidth=3/z;context.beginPath();context.arc(p[0],p[1],17/z,0,Math.PI*2);context.stroke();const x=p[0]+15/z,y=p[1]-15/z;context.fillStyle='#ffcd48';context.beginPath();context.arc(x,y,9/z,0,Math.PI*2);context.fill();context.fillStyle='#302300';context.fillText('?',x,y);});

 context.restore();
}
function choosePoint(point){selectedPoint={map:current.id,point};renderNavigation();}
$('route-enabled').onchange=()=>{navEnabled=$('route-enabled').checked;clearRoute();draw();if(navEnabled)updateRoute(true);};
$('nav-next').onclick=()=>{navEnabled=true;$('route-enabled').checked=true;selectedPoint=null;refreshRoute();};
$('nav-pick').onclick=()=>{const p=selectedPoint&&selectedPoint.map===current?.id?selectedPoint.point:navTarget;if(!p||!current)return;journal.pick(current.id,p);selectedPoint=null;refreshRoute();};
$('nav-undo').onclick=()=>{if(current)journal.undo(current.id);refreshRoute();};
$('trail-enabled').onchange=()=>{draw();publishOverlay(true);};
$('hide-picked').onchange=()=>{draw();publishOverlay(true);};

function readPointVisibility(){
 try{
   const saved=JSON.parse(localStorage.getItem('aniimo-point-visibility')||'{}');
   if(saved&&typeof saved==='object'&&!Array.isArray(saved))return new Map(Object.entries(saved).filter(([key,value])=>typeof value==='boolean'));
 }catch(e){}
 return new Map();
}
let pointVisibility=readPointVisibility();
function setPointVisibility(category,visible){
 pointVisibility.set(category,visible);
 try{localStorage.setItem('aniimo-point-visibility',JSON.stringify(Object.fromEntries(pointVisibility)));}catch(e){}
 visible?enabled.add(category):enabled.delete(category);
 draw();publishOverlay(true);
 if(visible&&(category==='aniimo'||category==='aniimo-spawns'))loadMapCreatures(current).then(()=>{draw();publishOverlay(true);});
}
let pointIconScale=.85;
try{
 const saved=localStorage.getItem('aniimo-point-size');
 if(['50','70','85','100','125'].includes(saved))pointIconScale=Number(saved)/100;
 if(localStorage.getItem('aniimo-point-size-version')!=='2'&&saved==='70')pointIconScale=.85;
 localStorage.setItem('aniimo-point-size-version','2');localStorage.setItem('aniimo-point-size',String(Math.round(pointIconScale*100)));
}catch(e){}
$('point-size').value=String(Math.round(pointIconScale*100));
$('point-size').onchange=()=>{
 const value=$('point-size').value;if(!['50','70','85','100','125'].includes(value))return;
 pointIconScale=Number(value)/100;
 try{localStorage.setItem('aniimo-point-size',value);}catch(e){}
 draw();publishOverlay(true);
};
let overlayEnabled=false,overlaySending=false,overlayLastSent=0,overlayPending=false,overlayTimer=null;
let overlayBaseCache=null,overlaySentKey='',overlayBaseSerial=0,webBaseKey='';
const webBase=document.createElement('canvas');
function mapContentKey(){return JSON.stringify([current?.id,mapLoadVersion,pointImages.size,pointIconScale,[...enabled].sort(),I18N.language,regionBounds(),journal.pickedRevision,$('hide-picked').checked,lootMarks.filter(m=>m.map===current?.id)]);}
let realtimeTracking=true;
try{realtimeTracking=localStorage.getItem('aniimo-realtime-tracking')!=='off';}catch(e){}
$('realtime-tracking').checked=realtimeTracking;
function showTrackingPaused(){
 if(lastKnown)holdPosition();
 $('position-status').textContent='实时定位已关闭 · 仅识别大地图';
 $('reason').textContent='当前位置已保留。打开大地图仍可识别地图和位置；彩虹掉落自动标记暂停。';
}
$('realtime-tracking').onchange=()=>{
 realtimeTracking=$('realtime-tracking').checked;generation++;lootEpisode=null;
 try{localStorage.setItem('aniimo-realtime-tracking',realtimeTracking?'on':'off');}catch(e){}
 if(!realtimeTracking){showTrackingPaused();$('loot-status').textContent='实时定位关闭，自动掉落标记暂停';}
 else{tracking=null;if(lastKnown)holdPosition();$('position-status').textContent='实时定位已开启 · 请打开大地图校准';$('reason').textContent='请重新打开大地图确认当前位置，再继续小地图追踪。';$('loot-status').textContent='等待光柱出现';}
 draw();publishOverlay(true);
};
// Session discoveries are observation locations, never inferred loot coordinates.
let lootMarks=[],lootEpisode=null,lootSerial=0,lootPanelKey='';
function resetLoot(){lootMarks=[];lootEpisode=null;lootSerial=0;lootPanelKey='';$('loot-status').textContent='等待光柱出现';}
function updateLoot(out,now=Date.now()){
 if(!realtimeTracking){lootEpisode=null;$('loot-status').textContent='实时定位关闭，自动掉落标记暂停';return;}
 if(!$('loot-enabled').checked||!running){lootEpisode=null;return;}
 const beams=out.loot_observations||[],candidate=out.candidates?.[0];
 const fresh=out.method==='minimap'&&out.status==='matched'&&!candidate?.held&&candidate?.position?.length===2&&candidate.position.every(v=>Number.isFinite(v)&&v>=0);
 const ttl=Math.max(10000,effectiveInterval()*4);
 if(lootEpisode&&now-lootEpisode.last>ttl)lootEpisode=null;
 if(!beams.length){
   if(lootEpisode){lootEpisode.count=0;if(++lootEpisode.misses>=2)lootEpisode=null;}
   $('loot-status').textContent='等待光柱出现';return;
 }
 const beam=beams.find(b=>lootEpisode&&Math.abs(b.screen_x-lootEpisode.x)<.15)||beams[0];
 if(!Number.isFinite(beam.screen_x))return;
 if(!fresh){if(lootEpisode){lootEpisode.count=0;lootEpisode.misses=0;lootEpisode.last=now;}$('loot-status').textContent='看到疑似光柱，等待当前位置确认';return;}
 if(!lootEpisode||lootEpisode.map!==candidate.id){lootEpisode={map:candidate.id,x:beam.screen_x,last:now,count:0,misses:0,recorded:false};}
 // Camera motion while a beam remains visible must not leave a marker trail.
 if(!lootEpisode.recorded&&Math.abs(beam.screen_x-lootEpisode.x)>=.15)lootEpisode.count=0;
 Object.assign(lootEpisode,{x:beam.screen_x,last:now,misses:0,count:lootEpisode.count+1});
 if(lootEpisode.recorded){$('loot-status').textContent='此处已记录，靠近后请自行核对';return;}
 if(lootEpisode.count<2){$('loot-status').textContent='看到疑似光柱，正在连续确认';return;}
 const position=[...candidate.position];
 const radius=(current?.id===candidate.id?Math.max(current.width,current.height):2048)*.035;
 if(!lootMarks.some(m=>m.map===candidate.id&&Math.hypot(m.position[0]-position[0],m.position[1]-position[1])<radius)){
   lootMarks.push({id:++lootSerial,map:candidate.id,position,time:now});
 }
 lootEpisode.recorded=true;$('loot-status').textContent='已标记发现位置附近 · 非精确坐标';
}
function renderLootList(){
 const marks=lootMarks.filter(m=>m.map===current?.id),key=JSON.stringify([current?.id,I18N.language,marks.map(m=>m.id),lootMarks.length]);
 if(key===lootPanelKey)return;lootPanelKey=key;$('loot-list').replaceChildren();
 if(!marks.length){const empty=document.createElement('p');empty.className='hint';empty.textContent=t('当前地图暂无记录');$('loot-list').append(empty);}
 for(const mark of marks){
   const row=document.createElement('div'),label=document.createElement('span'),button=document.createElement('button');row.className='loot-row';
   label.textContent=t('疑似彩虹·附近')+' #'+mark.id;button.textContent=t('移除');button.title=t('已拾取或误报时移除');
   button.onclick=()=>{lootMarks=lootMarks.filter(m=>m.id!==mark.id);draw();publishOverlay(true);};row.append(label,button);$('loot-list').append(row);
 }
 $('loot-clear').disabled=!lootMarks.length;
}
function paintLoot(ctx,zoom,markerScale){
 for(const mark of lootMarks.filter(m=>m.map===current.id)){
   const [x,y]=mark.position,r=18*markerScale/zoom;
   ctx.save();ctx.lineWidth=2/zoom;ctx.setLineDash([4/zoom,3/zoom]);ctx.strokeStyle='#e8a5ff';ctx.beginPath();ctx.arc(x,y,r,0,Math.PI*2);ctx.stroke();ctx.setLineDash([]);
   ctx.strokeStyle='#e8a5ff';ctx.beginPath();ctx.moveTo(x,y-r);ctx.lineTo(x,y-30*markerScale/zoom);ctx.stroke();
   drawMarker({x,y:y-40*markerScale/zoom},{icon:'diamond',size:19,color:'#e8a5ff'},ctx,zoom,markerScale);
   ctx.font=`600 ${11*Math.max(.75,markerScale)/zoom}px sans-serif`;ctx.textAlign='center';ctx.lineWidth=3/zoom;ctx.strokeStyle='#101b25';ctx.fillStyle='#f4cdff';
   const label=t('疑似彩虹·附近')+' #'+mark.id;ctx.strokeText(label,x,y-59*markerScale/zoom);ctx.fillText(label,x,y-59*markerScale/zoom);ctx.restore();
 }
}
$('loot-enabled').checked=true;
$('loot-enabled').onchange=()=>{lootEpisode=null;$('loot-status').textContent=$('loot-enabled').checked?'等待光柱出现':'自动标记已暂停';};
$('loot-clear').onclick=()=>{lootMarks=[];draw();publishOverlay(true);};
function overlayButton(){ $('overlay').textContent=overlayEnabled?'关闭悬浮窗':'游戏悬浮窗';$('overlay').setAttribute('aria-pressed',String(overlayEnabled)); }
async function publishOverlay(force=false){
 if(!overlayEnabled){clearTimeout(overlayTimer);overlayTimer=null;return;}
 if(overlaySending){overlayPending=true;return;}
 const remaining=200-(Date.now()-overlayLastSent);
 if(!force&&remaining>0){
   if(!overlayTimer)overlayTimer=setTimeout(()=>{overlayTimer=null;publishOverlay(true);},remaining);
   return;
 }
 clearTimeout(overlayTimer);overlayTimer=null;
 overlaySending=true;overlayLastSent=Date.now();
 try{
   const dungeon=bitmap&&current?.id.startsWith('sanctum-');
   const confirmed=result?.id===current?.id;
   let image=null,title='等待识别地宫',player=null,mapKey='empty',navigation={trail:[],path:[],target:null,stops:[],held:true};
   if(dungeon){
     const b=mapBounds||{x:0,y:0,w:current.width,h:current.height},raster=Math.min(1,2048/Math.max(b.w,b.h));
     const key=mapContentKey()+JSON.stringify(b);
     if(!overlayBaseCache||overlayBaseCache.content!==key){
       const copy=document.createElement('canvas');copy.width=Math.max(1,Math.round(b.w*raster));copy.height=Math.max(1,Math.round(b.h*raster));
       const z=Math.min(copy.width/b.w,copy.height/b.h),x=(copy.width-b.w*z)/2-b.x*z,y=(copy.height-b.h*z)/2-b.y*z;
       const markerScale=.8*z/(Math.min(504/b.w,350/b.h)*.94);
       paintMap(copy.getContext('2d'),z,x,y,markerScale,false,overlayTerrain());
       overlayBaseCache={content:key,key:observationSession+'-map-'+(++overlayBaseSerial),image:copy.toDataURL('image/png'),w:copy.width,h:copy.height,z,x,y};
     }
     const base=overlayBaseCache;mapKey=base.key;image=base.image;
     const project=p=>[(p[0]*base.z+base.x)/base.w,(p[1]*base.z+base.y)/base.h];
     navigation=navigationLayer(project);
     if(confirmed&&result.position){const [x,y]=project(result.position);player={x,y,held:!!result.held,label:t(result.held?'你·上次':result.position_source==='auto'?'你':'手动'),polygon:(result.polygon||[]).map(project)};}
     title=current.name+(!confirmed?' · 地图预览 · 尚未确认':result.held?(recoveryActive?' · 正在重新定位':' · 保留上次位置'):result.position?' · 你的位置':' · 等待角色定位');
   }
   const payload={map_key:mapKey,player,navigation,title:t(title),language:I18N.language};
   if(mapKey!==overlaySentKey||!dungeon)payload.image=image;
   const response=await fetch('/api/overlay/frame',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
   if(!response.ok)throw Error('悬浮窗同步失败');
   overlaySentKey=mapKey;
 }catch(e){overlaySentKey='';$('overlay-hint').textContent='悬浮窗暂未同步，请检查本地服务。';}finally{overlaySending=false;if(overlayPending){overlayPending=false;publishOverlay(true);}}
}
$('overlay').onclick=async()=>{
 $('overlay').disabled=true;
 try{const response=await fetch('/api/overlay',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action:overlayEnabled?'stop':'start'})});const state=await response.json();if(!response.ok)throw Error(state.error);overlayEnabled=state.enabled;overlaySentKey='';overlayButton();await publishOverlay(true);}
 catch(e){$('overlay-hint').textContent='悬浮窗未启动：'+e.message;}finally{$('overlay').disabled=false;}
};
async function overlayStatus(){
 try{const response=await fetch('/api/overlay');if(response.ok){const state=await response.json();window.OverlayHotkeys?.sync(state.hotkeys);const justOpened=!overlayEnabled&&state.enabled;overlayEnabled=state.enabled;overlayButton();if(justOpened){overlaySentKey='';await publishOverlay(true);}}}
 catch(e){}setTimeout(overlayStatus,2500);
}
// Display regions are approximate island extents on the shared atlas, not game boundaries.
const seaRegions=[
 {id:'port',name:'古代港口',box:[65,150,250,160]},
 {id:'north',name:'北部岛区',box:[310,78,250,193]},
 {id:'east',name:'东北岛区',box:[557,68,237,221]},
 {id:'center',name:'中央岛区',box:[244,223,219,184]},
 {id:'southeast',name:'东南岛区',box:[459,235,267,183]},
 {id:'southwest',name:'西南岛区',box:[157,302,139,109]},
 {id:'south',name:'南部粉色岛区',box:[246,353,212,190]}
];
let seaView='auto', activeSeaRegion=null;
const isSea=()=>current?.id.startsWith('egg-heist');
function regionAt(position){
 const [x,y]=[position[0]*900/current.width,position[1]*600/current.height];
 return [...seaRegions].sort((a,b)=>distance(a)-distance(b))[0];
 function distance(r){const [l,t,w,h]=r.box;return Math.hypot(Math.max(l-x,0,x-l-w),Math.max(t-y,0,y-t-h))*10+Math.hypot(x-l-w/2,y-t-h/2);}
}
function regionBounds(){if(!isSea()||seaView==='all'||!activeSeaRegion)return null;const [x,y,w,h]=activeSeaRegion.box;return {x:x*current.width/900,y:y*current.height/600,w:w*current.width/900,h:h*current.height/600};}
function syncSeaRegion(){
 $('sea-region').hidden=!isSea();$('region-follow').hidden=!isSea();
 const fitLabel=t(isSea()?'全岛':'全图');if($('fit').textContent!==fitLabel)$('fit').textContent=fitLabel;
 if(!isSea()){activeSeaRegion=null;return false;}
 const next=seaView==='auto'?(result?.id===current.id&&result.position?regionAt(result.position):null):seaRegions.find(r=>r.id===seaView);
 const changed=next?.id!==activeSeaRegion?.id;activeSeaRegion=next||null;return changed;
}
function confirmMap(candidate){
 if(!candidate?.id||candidate.held)return;
 // Only confirmed full-map results (or explicit confirmation) reach here.
 // Browsing a candidate, a covered map, and reopening the same map keep records.
 if(confirmedMapId&&confirmedMapId!==candidate.id){
   resetNavigation();resetLoot();history=[];lastSignature=null;
   tracking=null;lastKnown=null;trackedAt=0;generation++;
   seaView='auto';$('sea-region').value='auto';
 }
 confirmedMapId=candidate.id;
}
function rememberPosition(candidate){
 if(candidate?.position){
  const now=Date.now();
  if(lastKnown?.position&&lastKnown.id!==candidate.id){journal.pause();clearRoute();}
  else if(lastKnown?.position&&Math.hypot(candidate.position[0]-lastKnown.position[0],candidate.position[1]-lastKnown.position[1])>100){journal.pause();routeFollower.pause();}
  if(running&&!candidate.held){
   journal.record(candidate.id,candidate.position,now);
   if(navEnabled&&current?.id===candidate.id){routeFollower.observe(candidate.position,now);if(routeFollower.path.length)navPath=routeFollower.remaining();}
  }
  tracking={id:candidate.id,position:candidate.position,scale:candidate.minimap_scale};trackedAt=Date.now();lastKnown={...candidate};
 }else if(candidate&&lastKnown?.id!==candidate.id){tracking=null;lastKnown=null;}
}
function holdPosition(){journal.pause();routeFollower.pause();if(!lastKnown)return false;result={...lastKnown,held:true,polygon:[]};$('position-status').textContent='位置暂未更新 · 保留上次位置';$('result').textContent='位置保留 · '+lastKnown.name;$('reason').textContent=`画面暂时无法定位，按仍在原处显示。上次定位 ${Math.max(0,Math.floor((Date.now()-trackedAt)/1000))} 秒前；地图恢复后自动继续。`;return true;}
const temp=document.createElement('canvas'), tc=temp.getContext('2d');
const ICON_PATHS={
 compass:'M12 2a10 10 0 1 0 0 20 10 10 0 1 0 0-20 M16 8l-3 5-5 3 3-5z',
 door:'M5 21V5l7-3 7 3v16 M3 21h18 M8 21V7h8v14 M12 12v4 M10 14h4',
 side:'M5 21V5l7-3 7 3v16 M3 21h18 M8 7h8 M12 9v9 M9 15l3 3 3-3',
 egg:'M12 3C8 3 5 10 5 15a7 7 0 0 0 14 0c0-5-3-12-7-12z M9 10l2-2 M8 15v2',
 chest:'M3 11h18v9H3z M3 11V8a4 4 0 0 1 4-4h10a4 4 0 0 1 4 4v3 M3 13h7 M14 13h7 M10 11h4v5h-4z',
 key:'M9 3a5 5 0 1 0 0 10A5 5 0 0 0 9 3 M12.5 11.5L21 20 M17 16l3-3 M19 18l3-3',
 shop:'M3 9l2-6h14l2 6 M3 9a3 3 0 0 0 6 0 3 3 0 0 0 6 0 3 3 0 0 0 6 0 M5 12v9h14v-9 M9 21v-6h6v6',
 creature:'M6 12l-3-7 7 3h4l7-3-3 7v5l-6 4-6-4z M9 13v2 M15 13v2 M11 17h2',
 room:'M3 9V3h6 M15 3h6v6 M21 15v6h-6 M9 21H3v-6 M8 8h8v8H8z',
 star:'M12 2l3 6 7 1-5 5 1 7-6-3-6 3 1-7-5-5 7-1z',
 diamond:'M12 3l8 9-8 9-8-9z M4 12h16 M12 3l3 9-3 9-3-9z',
 boat:'M4 13l8 4 8-4-2 6H6z M7 14V6h10v8 M12 6V2 M3 22l3-1 3 1 3-1 3 1 3-1 3 1',
 monitor:'M3 4h18v13H3z M8 21h8 M12 17v4',
 stop:'M6 6h12v12H6z',
 scan:'M3 8V3h5 M16 3h5v5 M21 16v5h-5 M8 21H3v-5 M7 12h10 M12 7v10',
 upload:'M12 16V3 M7 8l5-5 5 5 M4 15v6h16v-6',
 pin:'M19 9c0 5-7 12-7 12S5 14 5 9a7 7 0 0 1 14 0 M12 6a3 3 0 1 0 0 6 3 3 0 0 0 0-6',
 reset:'M3 10a9 9 0 1 1 1 7 M3 3v7h7',
 focus:'M3 8V3h5 M16 3h5v5 M21 16v5h-5 M8 21H3v-5',
 follow:'M12 2v4 M12 18v4 M2 12h4 M18 12h4 M12 6a6 6 0 1 0 0 12 6 6 0 0 0 0-12 M12 10a2 2 0 1 0 0 4 2 2 0 0 0 0-4',
 plus:'M12 5v14 M5 12h14',minus:'M5 12h14',external:'M14 3h7v7 M21 3L10 14 M10 3H3v18h18v-7'
};
const iconPaths=Object.fromEntries(Object.entries(ICON_PATHS).map(([k,v])=>[k,new Path2D(v)]));
function icon(name){const svg=document.createElementNS('http://www.w3.org/2000/svg','svg');svg.setAttribute('viewBox','0 0 24 24');svg.setAttribute('class','ui-icon');svg.setAttribute('aria-hidden','true');const p=document.createElementNS(svg.namespaceURI,'path');p.setAttribute('d',ICON_PATHS[name]||ICON_PATHS.diamond);svg.append(p);return svg;}
const POINT_ASSETS={"unique-rooms":"/data/icons/special-room-monster.webp","timed-challenges":"/data/icons/timed-challenge.webp","egg-nests": "/data/icons/95ea407d9709.webp", "merchants": "/data/icons/37cf1b3a107a.webp", "chests-legendary": "/data/icons/142526bf6d00.webp", "chests-epic": "/data/icons/142526bf6d00.webp", "chests-rare": "/data/icons/142526bf6d00.webp", "chests-uncommon": "/data/icons/142526bf6d00.webp", "teleporters": "/data/icons/76e54419740c.webp", "extraction": "/data/icons/d22c145ac350.webp", "giant-egg": "/data/icons/5859f8149869.webp", "coin-monsters": "/data/icons/e809a83f987c.webp", "egg-boats": "/data/icons/9a84fb851b88.webp", "rare-chests": "/data/icons/4e231d9f5c79.webp", "chests": "/data/icons/142526bf6d00.webp", "collectibles": "/data/icons/94eef2370f56.webp", "entrance": "/data/icons/88283228aef0.webp", "side-entrance": "/data/icons/door-side-game.webp", "key-rooms-gold": "/data/icons/key-gold-game.webp", "key-rooms-purple": "/data/icons/key-purple-game.webp", "key-rooms-blue": "/data/icons/key-blue-game.webp"};
const CREATURE_ASSETS={"幽黯云朵羊": "/data/icons/4994391e97ee.png", "幽黯冰刃狼": "/data/icons/dfe252f67d0c.png", "幽黯刺剑玫": "/data/icons/84e60a3f66de.png", "幽黯吊灯水母": "/data/icons/79bd1ad167cb.png", "幽黯土堡蚁": "/data/icons/2171bbd97e59.png", "幽黯埋埋": "/data/icons/e5446840d6f1.png", "幽黯大号鸥": "/data/icons/5f9ce11d8c81.png", "幽黯大眼盔": "/data/icons/8f9776cc8593.png", "幽黯小号鸥": "/data/icons/909daeddac19.png", "幽黯小哭苞": "/data/icons/903de297cc12.png", "幽黯小炭犬": "/data/icons/c23b1e09b1bd.png", "幽黯巫帽草": "/data/icons/f5a868340d22.png", "幽黯幻焰灵": "/data/icons/c1179f63d0ca.png", "幽黯幻翼蝶": "/data/icons/b406f9758b0c.png", "幽黯幽幽焰": "/data/icons/dcd9bb40480e.png", "幽黯幽爪镰": "/data/icons/5623dea84982.png", "幽黯星乐蒂": "/data/icons/9aad1c57cef6.png", "幽黯星骑士": "/data/icons/2286b85297c5.png", "幽黯星魔师": "/data/icons/81c264b13943.png", "幽黯星魔师首领": "/data/icons/81c264b13943.png", "幽黯晶背龙": "/data/icons/7f77927e89f0.png", "幽黯暴睡熊": "/data/icons/c77ac145bff0.png", "幽黯泡泡獭": "/data/icons/a9dc19959d38.png", "幽黯淬刃螳螂": "/data/icons/5b7f86048ec2.png", "幽黯滚滚郎": "/data/icons/c7c8c39a278e.png", "幽黯漂漂獭": "/data/icons/17cc8d83695e.png", "幽黯灯泡水母": "/data/icons/0cadbed822c1.png", "幽黯灯纱水母": "/data/icons/956a879b48cd.png", "幽黯焚火狼": "/data/icons/1d4eaa852ea6.png", "幽黯狼斗士": "/data/icons/70ea1cf56079.png", "幽黯盔勇士": "/data/icons/1465c981c213.png", "幽黯盔卫士": "/data/icons/8977d2fd51e3.png", "幽黯簇晶脊龙": "/data/icons/be08406cc613.png", "幽黯胖胖獭": "/data/icons/9f90243c1466.png", "幽黯花舞兰": "/data/icons/7f158c15c70e.png", "幽黯花芽蟹": "/data/icons/1738c600e48d.png", "幽黯莲冠龙": "/data/icons/ef43e9a470f7.png", "幽黯莲顶鱼": "/data/icons/8a65d7c5dd91.png", "幽黯莹冰龙": "/data/icons/ed6f3598996e.png", "幽黯蓬蓬羊": "/data/icons/fde84557c7a4.png", "幽黯蟹葱葱": "/data/icons/398749ecc6e7.png", "幽黯走调草": "/data/icons/d272972c4aae.png", "幽黯迷梦崽": "/data/icons/85d4e12fd80e.png", "幽黯长号鸥": "/data/icons/27c1cb61beff.png", "幽黯雷光貂": "/data/icons/96ed2fa1fb58.png", "幽黯顽皮鱼": "/data/icons/fe5cada52134.png", "幽黯飘飘花": "/data/icons/c99ef19f1737.png", "幽黯香氛鸟": "/data/icons/b3f1f161c723.png", "幽黯魅乐薇": "/data/icons/6c6f3c8e7b25.png", "幽黯碎岩仔": "/data/icons/official-rockling.png"};
const pointImages=new Map();
const pendingPortraits=new Map();
async function loadMapCreatures(map){
 if(!map)return;
 const urls=new Set((map.displayPoints||map.points).filter(p=>enabled.has(p.category)&&(p.category==='aniimo'||p.category==='aniimo-spawns')).map(p=>CREATURE_ASSETS[p.name]).filter(Boolean));
 await Promise.all([...urls].map(url=>{
   if(pointImages.has(url))return;
   if(!pendingPortraits.has(url))pendingPortraits.set(url,(async()=>{
     try{
       const image=new Image();image.src=url;await image.decode();
       const thumbnail=document.createElement('canvas'),scale=64/Math.max(image.naturalWidth,image.naturalHeight);
       thumbnail.width=Math.max(1,Math.round(image.naturalWidth*scale));thumbnail.height=Math.max(1,Math.round(image.naturalHeight*scale));
       thumbnail.getContext('2d').drawImage(image,0,0,thumbnail.width,thumbnail.height);pointImages.set(url,thumbnail);
     }catch(e){}finally{pendingPortraits.delete(url);}
   })());
   return pendingPortraits.get(url);
 }));
}
const POINT_RECTS={'142526bf6d00.webp':[11,18,89,82],'37cf1b3a107a.webp':[16,12,88,89],'4e231d9f5c79.webp':[10,15,95,87],'71067aac18a9.webp':[16,16,84,84]};
async function loadPointImages(){
 await Promise.all([...new Set(Object.values(POINT_ASSETS))].map(async url=>{
  try{const image=new Image();image.src=url;await image.decode();pointImages.set(url,image);}catch(e){}
 }));
}
function markerStyle(category,color,name){
 const styles={
  entrance:['#ffd36b',27,'黄门','IN'],'side-entrance':['#82beff',27,'蓝门','OUT'],
  sanctums:['#82beff',22,'地宫','DG'],teleporters:['#8ee0c4',22,'传送','TP'],extraction:['#8ee0c4',22,'撤离','EX'],
  'egg-boats':['#89d9f5',22,'蛋船','BT'],'egg-nests':['#ffe9b0',20,'蛋巢','EG'],'giant-egg':['#ffe9b0',22,'巨蛋','GE'],
  'chests-legendary':['#ffb02e',18,'金箱','GC','金','G'],'chests-epic':['#c07cff',18,'紫箱','PC','紫','P'],
  'chests-rare':['#5aa9ff',18,'蓝箱','BC','蓝','B'],'rare-chests':['#5aa9ff',18,'蓝箱','BC','蓝','B'],'chests-uncommon':['#7ee3c0',18,'绿箱','UC','绿','U'],chests:['#ffc662',18,'宝箱','CH'],
  'key-rooms-gold':['#ffd36b',20,'金钥匙房','GK'],'key-rooms-purple':['#b892ff',20,'紫钥匙房','PK'],'key-rooms-blue':['#4ec3ff',20,'蓝钥匙房','BK'],
  merchants:['#8ee0c4',20,'商人','SH'],aniimo:['#ef9aab',18,'伊莫','AN'],'aniimo-spawns':['#ef9aab',18,'伊莫','AN'],
  rooms:['#acbbc9',17,'房间','RM'],'unique-rooms':['#c9acff',20,'特殊','SP'],'timed-challenges':['#8fdcff',22,'挑战','TC'],'coin-monsters':['#ffd36b',18,'金币','CO'],collectibles:['#8ee0c4',18,'采集','IT']
 };
 const [defaultColor,size,zh,en,badgeZh,badgeEn]=styles[category]||['#d7e2ed',18,'点位','PT'];
 const creature=category==='aniimo'||category==='aniimo-spawns';
 return {point:true,asset:creature?CREATURE_ASSETS[name]:POINT_ASSETS[category],color:category==='entrance'||category==='side-entrance'?defaultColor:color||defaultColor,size,text:I18N.language==='en'?en:creature&&name?name.replace(/^幽黯/,''):zh,badge:I18N.language==='en'?badgeEn:badgeZh,label:category==='entrance'?'黄门':category==='side-entrance'?'蓝门':undefined};
}
function pointLegendIcon(style){
 if(style.asset){const image=document.createElement('img');image.src=style.asset;image.alt='';image.className='map-category-icon';return image;}
 const text=document.createElement('span');text.className='map-category-text';text.setAttribute('aria-hidden','true');return text;
}
function drawOriginalPoint(p,style,ctx,zoom,markerScale){
 const size=style.size*1.4,image=pointImages.get(style.asset);
 // Scale the complete marker, including fallback text, badges and outlines.
 // A high-resolution overlay must not shrink fixed-size text on downsampling.
 ctx.save();ctx.translate(p.x,p.y);ctx.scale(markerScale/zoom,markerScale/zoom);
 if(image){
   const bounds=POINT_RECTS[style.asset.split('/').pop()]||[0,0,image.naturalWidth||image.width||100,image.naturalHeight||image.height||100];
   const [left,top,right,bottom]=bounds,sw=right-left,sh=bottom-top,ratio=size/Math.max(sw,sh),dw=sw*ratio,dh=sh*ratio;
   ctx.shadowColor='#000b';ctx.shadowBlur=2;ctx.drawImage(image,left,top,sw,sh,-dw/2,-dh/2,dw,dh);ctx.shadowBlur=0;
   if(style.badge){
     ctx.fillStyle='#101b25db';ctx.strokeStyle=style.color;ctx.lineWidth=1;ctx.beginPath();ctx.arc(size*.36,size*.32,4.5,0,Math.PI*2);ctx.fill();ctx.stroke();
     ctx.fillStyle=style.color;ctx.font='600 8px sans-serif';ctx.textAlign='center';ctx.textBaseline='middle';ctx.fillText(style.badge,size*.36,size*.32);
   }
 }else{
   ctx.font=`600 ${Math.max(9,Math.min(12,size*.48))}px sans-serif`;ctx.textAlign='center';ctx.textBaseline='middle';ctx.lineWidth=3;ctx.strokeStyle='#101b25';ctx.fillStyle=style.color;ctx.strokeText(style.text,0,0);ctx.fillText(style.text,0,0);
 }
 if(image&&style.label){ctx.textAlign='left';ctx.textBaseline='middle';ctx.font='600 9px sans-serif';ctx.lineWidth=3;ctx.strokeStyle='#101b25';ctx.fillStyle=style.color;ctx.strokeText(t(style.label),size/2+3,0);ctx.fillText(t(style.label),size/2+3,0);}
 ctx.restore();
}
function uniqueMapPoints(points){
 // Source exports repeat observations with sub-pixel coordinate differences.
 // Merge only the same named type within four map pixels; keep distinct sites.
 const cells=new Map(),unique=[],distance=4;
 for(const p of points){
   const cx=Math.floor(p.x/distance),cy=Math.floor(p.y/distance),prefix=p.category+'\0'+p.name+'\0';let duplicate=false;
   for(let dx=-1;dx<=1&&!duplicate;dx++)for(let dy=-1;dy<=1&&!duplicate;dy++){
     duplicate=(cells.get(prefix+(cx+dx)+','+(cy+dy))||[]).some(q=>Math.hypot(q.x-p.x,q.y-p.y)<=distance);
   }
   if(duplicate)continue;
   unique.push(p);const key=prefix+cx+','+cy;if(!cells.has(key))cells.set(key,[]);cells.get(key).push(p);
 }
 return unique;
}
// Keep coordinates for routing/pickup; separate overlapping nest/key artwork only.
function markerPosition(p,z,scale=1){
 if(p.category!=='egg-nests'||!current)return p;
 const keys=current.keyRooms||(current.displayPoints||current.points).filter(q=>q.category.startsWith('key-rooms-'));
 const overlap=keys.some(q=>enabled.has(q.category)&&!($('hide-picked').checked&&journal.picked(current.id,q))&&Math.hypot(q.x-p.x,q.y-p.y)<18);
 return overlap?{...p,x:p.x+26*scale/z,y:p.y+12*scale/z}:p;
}
function drawMarker(p,style,ctx,zoom,markerScale=1){if(style.point){ctx.save();if(current&&journal.picked(current.id,p))ctx.globalAlpha=.28;const placed=markerPosition(p,zoom,markerScale);if(placed!==p){ctx.strokeStyle='#ffe9b099';ctx.lineWidth=1/zoom;ctx.beginPath();ctx.moveTo(p.x,p.y);ctx.lineTo(placed.x,placed.y);ctx.stroke();}drawOriginalPoint(placed,style,ctx,zoom,markerScale);ctx.restore();return;}const {color}=style;const size=style.size*1.4*markerScale;ctx.save();ctx.translate(p.x,p.y);ctx.scale(1/zoom,1/zoom);ctx.shadowColor='#0009';ctx.shadowBlur=3;ctx.fillStyle='#101b25b8';ctx.strokeStyle=color;ctx.lineWidth=1.15;ctx.beginPath();ctx.arc(0,0,size/2,0,Math.PI*2);ctx.fill();ctx.stroke();ctx.shadowBlur=0;const s=(size-5)/24;ctx.scale(s,s);ctx.translate(-12,-12);ctx.lineWidth=1.9;ctx.lineCap='round';ctx.lineJoin='round';ctx.stroke(iconPaths[style.icon]);ctx.restore();if(style.label){ctx.save();ctx.font=`600 ${11*Math.max(.75,markerScale)/zoom}px sans-serif`;ctx.lineWidth=3/zoom;ctx.strokeStyle='#0b141e';ctx.strokeText(t(style.label),p.x+(size/2+5)/zoom,p.y+4/zoom);ctx.fillStyle=color;ctx.fillText(t(style.label),p.x+(size/2+5)/zoom,p.y+4/zoom);ctx.restore();}}
function newRun(){confirmedMapId=null;resetNavigation();lastFullFrameAt=-Infinity;resetLoot();seaView='auto';$('sea-region').value='auto';history=[];lastSignature=null;result=null;tracking=null;lastKnown=null;trackedAt=0;generation++;$('position-status').textContent='先开大地图校准，再用小地图追踪';$('result').textContent='新一局 · 等待主门附近地图';$('reason').textContent='从黄门进入后打开地图，探索更多房间以缩小候选。';$('candidates').replaceChildren();draw();}
function notice(text){$('reason').textContent=text;}
async function loadMap(id){
 const requestVersion=++mapLoadVersion;if(current?.id!==id){clearRoute();selectedPoint=null;}
 const d=await fetch('/data/'+id+'.json',{cache:'no-store'}).then(r=>r.json());
 const im=new Image();im.src=d.image;await im.decode();if(requestVersion!==mapLoadVersion)return;current=d;current.displayPoints=uniqueMapPoints(d.points);current.keyRooms=current.displayPoints.filter(p=>p.category.startsWith('key-rooms-'));bitmap=im;
 if(typeof RouteGoals!=='undefined')RouteGoals.render();if(typeof MapNotes!=='undefined')MapNotes.syncMap();
 const measure=document.createElement('canvas');measure.width=256;measure.height=256;const mc=measure.getContext('2d');mc.drawImage(im,0,0,256,256);const pixels=mc.getImageData(0,0,256,256).data;let left=256,top=256,right=0,bottom=0;for(let y=0;y<256;y++)for(let x=0;x<256;x++){const i=(y*256+x)*4;if((pixels[i]+pixels[i+1]+pixels[i+2])/3>85){left=Math.min(left,x);right=Math.max(right,x);top=Math.min(top,y);bottom=Math.max(bottom,y);}}mapBounds=right>left?{x:Math.max(0,left-8)*d.width/256,y:Math.max(0,top-8)*d.height/256,w:Math.min(256,right-left+16)*d.width/256,h:Math.min(256,bottom-top+16)*d.height/256}:{x:0,y:0,w:d.width,h:d.height};
 enabled=new Set(d.categories.filter(c=>pointVisibility.has(c.id)?pointVisibility.get(c.id):/egg|entrance|legendary|key-room|sanctums|teleporters|extraction|timed-challenges/.test(c.id)).map(c=>c.id));
 loadMapCreatures(current).then(()=>{if(current===d){draw();publishOverlay(true);}});
 if($('challenge-note'))$('challenge-note').hidden=!d.challengeSource;
 $('filters').replaceChildren();for(const c of d.categories){const l=document.createElement('label'), i=document.createElement('input'),style=markerStyle(c.id,c.color);i.type='checkbox';i.checked=enabled.has(c.id);i.onchange=()=>setPointVisibility(c.id,i.checked);l.append(i,pointLegendIcon(style),document.createTextNode(style.label||c.name));l.style.color=style.color;$('filters').append(l);}
 $('mapinfo').textContent=`${d.name} · ${d.width} × ${d.height} · ${current.displayPoints.length} 条点位`;fit();
}
function fit(){if(!current)return;syncSeaRegion();const b=regionBounds()||mapBounds||{x:0,y:0,w:current.width,h:current.height};zoom=Math.min(canvas.clientWidth/b.w,canvas.clientHeight/b.h)*.90;ox=(canvas.clientWidth-b.w*zoom)/2-b.x*zoom;oy=(canvas.clientHeight-b.h*zoom)/2-b.y*zoom;draw();}
// Process only terrain; point icons are drawn afterwards and keep their artwork.
// Cache one map so position updates never repeat the pixel pass.
let overlayTerrainCache=null;
function overlayTerrain(){
 if(overlayTerrainCache?.bitmap===bitmap)return overlayTerrainCache.canvas;
 const layer=document.createElement('canvas');layer.width=bitmap.naturalWidth;layer.height=bitmap.naturalHeight;
 const context=layer.getContext('2d');context.drawImage(bitmap,0,0);
 const pixels=context.getImageData(0,0,layer.width,layer.height),data=pixels.data;
 for(let i=0;i<data.length;i+=4){
   const light=Math.max(data[i],data[i+1],data[i+2]);
   const strength=light<=24?0:light<80?.10*(light-24)/56:Math.min(1,.10+.90*(light-80)/40);
   data[i+3]=Math.round(data[i+3]*strength);
 }
 context.putImageData(pixels,0,0);overlayTerrainCache={bitmap,canvas:layer};return layer;
}

function paintMap(ctx,zoom,ox,oy,markerScale=1,includePlayer=true,terrain=bitmap){
 ctx.save();ctx.translate(ox,oy);ctx.scale(zoom,zoom);const crop=regionBounds();if(crop){ctx.beginPath();ctx.rect(crop.x,crop.y,crop.w,crop.h);ctx.clip();}ctx.drawImage(terrain,0,0,current.width,current.height);
 const seen=new Set(),doors=[];for(const p of current.displayPoints||current.points){if(!enabled.has(p.category)||($('hide-picked').checked&&journal.picked(current.id,p)))continue;const key=p.category+':'+p.x+':'+p.y;if(seen.has(key))continue;seen.add(key);if(p.category==='entrance'||p.category==='side-entrance'){doors.push(p);continue;}const cat=current.categories.find(c=>c.id===p.category);drawMarker(p,markerStyle(p.category,cat?.color,p.name),ctx,zoom,markerScale*pointIconScale);}for(const p of doors)drawMarker(p,markerStyle(p.category),ctx,zoom,markerScale*pointIconScale);
 paintLoot(ctx,zoom,markerScale);
 if(includePlayer)paintPlayer(ctx,zoom);
 ctx.restore();
}
function paintPlayer(ctx,zoom){
 if(result&&result.id===current.id){ctx.strokeStyle='#58ead2';ctx.fillStyle='#58ead213';ctx.lineWidth=2/zoom;ctx.beginPath();result.polygon.forEach((p,i)=>i?ctx.lineTo(...p):ctx.moveTo(...p));ctx.closePath();ctx.fill();ctx.stroke();if(result.position){ctx.fillStyle=result.held?'#e6b75b':'#ff7188';ctx.beginPath();ctx.arc(...result.position,9/zoom,0,Math.PI*2);ctx.fill();ctx.strokeStyle='#fff';ctx.lineWidth=2/zoom;ctx.stroke();ctx.font=`600 ${12/zoom}px sans-serif`;ctx.fillStyle='#fff';ctx.strokeStyle='#111b29';ctx.lineWidth=3/zoom;const playerLabel=t(result.held?'你·上次':result.position_source==='auto'?'你':'手动');ctx.strokeText(playerLabel,result.position[0]+14/zoom,result.position[1]+4/zoom);ctx.fillText(playerLabel,result.position[0]+14/zoom,result.position[1]+4/zoom);}}
}
function draw(){
 renderLootList();renderNavigation();syncQuality();
 if(current&&syncSeaRegion()){fit();return;}
 const w=canvas.clientWidth,h=canvas.clientHeight,dpr=devicePixelRatio; if(canvas.width!==Math.round(w*dpr)||canvas.height!==Math.round(h*dpr)){canvas.width=Math.round(w*dpr);canvas.height=Math.round(h*dpr);}ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,w,h);if(!bitmap)return;
 const baseKey=mapContentKey()+JSON.stringify([w,h,dpr,zoom,ox,oy]);
 if(webBaseKey!==baseKey){webBase.width=canvas.width;webBase.height=canvas.height;const baseContext=webBase.getContext('2d');baseContext.setTransform(dpr,0,0,dpr,0,0);paintMap(baseContext,zoom,ox,oy,1,false);webBaseKey=baseKey;}
 ctx.drawImage(webBase,0,0,webBase.width,webBase.height,0,0,w,h);
 ctx.save();ctx.translate(ox,oy);ctx.scale(zoom,zoom);const activeCrop=regionBounds();if(activeCrop){ctx.beginPath();ctx.rect(activeCrop.x,activeCrop.y,activeCrop.w,activeCrop.h);ctx.clip();}paintNavigation(ctx,zoom);paintPlayer(ctx,zoom);if(typeof MapNotes!=='undefined')MapNotes.paint(ctx,zoom);ctx.restore();$('viewmode').textContent=isSea()?(activeSeaRegion&&seaView!=='all'?activeSeaRegion.name+' · 分区地图':'全岛总览'):(result&&result.id===current.id?(result.held?'保留上次位置':'匹配范围'):'全图浏览');
 publishOverlay();updateRoute();
}
let drag=null;canvas.onpointerdown=e=>{if(e.button!==0)return;drag={x:e.clientX,y:e.clientY,ox,oy};canvas.setPointerCapture(e.pointerId);};canvas.onpointermove=e=>{if(drag){ox=drag.ox+e.clientX-drag.x;oy=drag.oy+e.clientY-drag.y;draw();}};canvas.onpointerup=e=>{if(drag&&Math.hypot(e.clientX-drag.x,e.clientY-drag.y)<5&&current){const r=canvas.getBoundingClientRect(),x=(e.clientX-r.left-ox)/zoom,y=(e.clientY-r.top-oy)/zoom;const near=(current.displayPoints||current.points).filter(p=>enabled.has(p.category)&&(!$('hide-picked').checked||!journal.picked(current.id,p))&&Math.hypot(markerPosition(p,zoom,pointIconScale).x-x,markerPosition(p,zoom,pointIconScale).y-y)<20/zoom);if(near.length)choosePoint(near.sort((a,b)=>Math.hypot(markerPosition(a,zoom,pointIconScale).x-x,markerPosition(a,zoom,pointIconScale).y-y)-Math.hypot(markerPosition(b,zoom,pointIconScale).x-x,markerPosition(b,zoom,pointIconScale).y-y))[0]);$('tooltip').textContent=[...new Set(near.map(p=>pointName(p)))].join(' / ');$('tooltip').style.display=near.length?'block':'none';}drag=null;};canvas.onwheel=e=>{e.preventDefault();const r=canvas.getBoundingClientRect(),x=e.clientX-r.left,y=e.clientY-r.top;const z=Math.max(.08,Math.min(8,zoom*Math.exp(-e.deltaY*.001)));ox=x-(x-ox)*z/zoom;oy=y-(y-oy)*z/zoom;zoom=z;draw();};
new ResizeObserver(()=>fit()).observe($('mapwrap'));
function preview(){if(!frame)return;const w=frame.videoWidth||frame.width,h=frame.videoHeight||frame.height,s=Math.min(1,800/Math.max(w,h));const pw=Math.round(w*s),ph=Math.round(h*s);if(cap.width!==pw||cap.height!==ph){cap.width=pw;cap.height=ph;}cc.clearRect(0,0,cap.width,cap.height);cc.drawImage(frame,0,0,cap.width,cap.height);previewFrameAt=Date.now();$('empty').hidden=true;}
$('newrun').onclick=newRun;
async function importFile(file){if(!file||!file.type.startsWith('image/'))return;stop();const im=await createImageBitmap(file);frame=im;cap.width=im.width;cap.height=im.height;newRun();$('capture-status').textContent='截图模式';preview();await identify();}
$('file').onchange=e=>importFile(e.target.files[0]).catch(e=>notice(e.message));document.onpaste=e=>{const f=[...e.clipboardData.items].find(i=>i.type.startsWith('image/'));if(f)importFile(f.getAsFile()).catch(e=>notice(e.message));};
let captureEpoch=0,firstFrameDeadline=0,receivedCaptureFrame=false;
let matchController=null,currentCaptureAt=0;
let nativeSession=null,nativePreviewAt=0,nativeSequence=0,nativeRetryAfter=0,nativeCost=null;
function captureInterval(){return realtimeTracking?effectiveInterval():Math.max(1000,effectiveInterval());}
function captureMessage(text){$('capture-status').textContent=text;$('empty').textContent=text;$('empty').hidden=false;}
function stop(){
 captureEpoch++;running=false;clearTimeout(timer);
 matchController?.abort();currentCaptureAt=0;
 if(nativeSession){const session=nativeSession;nativeSession=null;fetch('/api/native',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action:'stop',session}),keepalive:true}).catch(()=>{});}
 $('native-start').disabled=false;
timer=null;journal.pause();routeFollower.pause();navRequest++;if(lastKnown)holdPosition();
 frame=null;
 $('stop').disabled=true;captureMessage('未连接画面');generation++;
}
$('stop').onclick=()=>{stop();draw();notice('已停止读取游戏画面。');};
async function connectionFailure(error){
 const original=(error.name||'Error')+': '+error.message;
 try{
  const response=await fetch('/api/status',{cache:'no-store',signal:AbortSignal.timeout(2500)});
  if(!response.ok)throw Error('status '+response.status);
  const status=await response.json();
  return '采集请求失败，但助手后台仍可连接。'+(status.error?'后台错误：'+status.error+'。':'')+'原始错误：'+original+'。请重新连接采集。';
 }catch(e){
  return '无法连接助手后台，自动检查也未得到响应；后台可能退出或连接受阻，具体原因未确认。原始错误：'+original+'。请重新启动助手。';
 }
}
async function nativeRequest(payload){
 let response;
 try{response=await fetch('/api/native',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload),signal:AbortSignal.timeout(15000)});}
 catch(e){
  throw Error(await connectionFailure(e));
 }
 const out=await response.json();if(!response.ok)throw Error(out.error||'本地采集不可用');return out;
}
async function listNativeWindows(){
 $('native-connect').disabled=true;$('native-help').textContent='正在读取可用窗口…';
 try{const out=await nativeRequest({action:'list'});$('native-window').replaceChildren();
  const placeholder=document.createElement('option');placeholder.value='';placeholder.textContent='请选择游戏窗口';placeholder.disabled=true;placeholder.selected=true;$('native-window').append(placeholder);
  for(const item of out.windows){const option=document.createElement('option');option.value=item.id;option.dataset.pid=String(item.pid);option.textContent=item.title+' · '+item.pid;$('native-window').append(option);}
  $('native-connect').disabled=!out.windows.length;$('native-help').textContent=out.windows.length?'请选择伊莫游戏窗口。仅在本机读取，停止后立即结束采集。':'没有可用窗口，请先打开游戏。';
 }catch(e){$('native-help').textContent=e.message;}
}
$('native-start').onclick=()=>{$('native-dialog').showModal();listNativeWindows();};
$('native-refresh').onclick=listNativeWindows;
$('native-cancel').onclick=()=>$('native-dialog').close();
$('native-connect').onclick=async()=>{
 const windowId=$('native-window').value;if(!windowId){$('native-help').textContent='请先选择游戏窗口。';return;}
 const windowPid=Number($('native-window').selectedOptions[0]?.dataset.pid);
 $('native-dialog').close();stop();const epoch=captureEpoch;$('native-start').disabled=true;$('stop').disabled=false;captureMessage('正在连接本地采集…');
 try{const out=await nativeRequest({action:'start',window:windowId,window_pid:windowPid,interval:captureInterval()});
  if(epoch!==captureEpoch){nativeRequest({action:'stop',session:out.session}).catch(()=>{});return;}
  nativeSession=out.session;nativeRetryAfter=0;nativeSequence=0;nativePreviewAt=-Infinity;receivedCaptureFrame=false;firstFrameDeadline=performance.now()+12000;
  running=true;newRun();notice(out.capture_mode==='compatible'?'本地采集已连接（兼容模式），请打开游戏大地图校准。':'本地采集已连接，请打开游戏大地图校准。');tick(epoch);
 }catch(e){if(epoch!==captureEpoch)return;stop();notice(e.message);}
};

async function tick(epoch=captureEpoch){
 if(!running||!nativeSession||epoch!==captureEpoch)return;
 let delay=0;
 try{
  // Yield while an explicit scan or cancelled request finishes; never spin on busy.
  if(busy){delay=50;return;}
  nativeCost=null;await identify();if(epoch!==captureEpoch)return;
  const live=result?.position&&!result.held?result:null;
  if(nativeCost!==null)cadence.observe(nativeCost,live?.position,live?.id,Date.now());
  syncQuality();
 }catch(e){if(epoch===captureEpoch)notice('读取画面失败：'+e.message);delay=1000;}
 finally{
  if(running&&nativeSession&&epoch===captureEpoch){
   delay=Math.max(delay,nativeRetryAfter-performance.now());
   // The native endpoint long-polls at the requested interval.
   if(delay>0)timer=setTimeout(()=>tick(epoch),delay);
   else Promise.resolve().then(()=>tick(epoch));
  }
 }
}
function signature(){const c=document.createElement('canvas');c.width=c.height=32;const x=c.getContext('2d');x.drawImage(temp,0,0,32,32);const d=x.getImageData(0,0,32,32).data;return Array.from({length:1024},(_,i)=>Math.round((d[i*4]+d[i*4+1]+d[i*4+2])/24));}
function evidence(r,sig){
 const changed=!!sig&&(!lastSignature||sig.reduce((s,v,i)=>s+Math.abs(v-lastSignature[i]),0)/sig.length>.7);
 if(changed&&r.candidates?.length){history.push(r.candidates.map(c=>({id:c.id,score:c.score})));history=history.slice(-8);lastSignature=sig;}
 const tally=new Map();history.forEach((list,i)=>{const top=list[0]?.score||1;list.forEach(c=>{let t=tally.get(c.id)||{value:0,frames:0};t.value+=c.score/top*Math.pow(.85,history.length-1-i);if(c.id===list[0].id)t.frames++;tally.set(c.id,t);});});
 return tally;
}
function capturePayload(forceFull=false){
 if(nativeSession){
  const full=forceFull||performance.now()-lastFullFrameAt>=5000;
  if(full)lastFullFrameAt=performance.now();
  const preview=performance.now()-nativePreviewAt>=1000;
  if(preview)nativePreviewAt=performance.now();
  return {sig:null,payload:{native_session:nativeSession,after:nativeSequence,interval:captureInterval(),force_full:full,preview,loot:realtimeTracking&&$('loot-enabled').checked,tracking,realtime_tracking:realtimeTracking,observation:{session:observationSession+'-'+generation,sequence:1,captured_at:Date.now()}}};
 }
 // Imported screenshots use a single full-frame request; live cropping is native.
 const w=frame.width,h=frame.height;
 temp.width=w;temp.height=h;tc.drawImage(frame,0,0,w,h);
 return {payload:{anchor:null,tracking,realtime_tracking:realtimeTracking,capture_kind:'full',image:temp.toDataURL('image/jpeg',.9)},sig:signature()};
}

async function requestMatch(payload){
 const controller=new AbortController();matchController=controller;
 const timeout=setTimeout(()=>controller.abort(),15000);
 try{
 const response=await fetch('/api/match',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload),signal:controller.signal});
 const out=await response.json();if(!response.ok){const error=Error(out.error||'识别失败');error.status=response.status;throw error;}return out;
 }catch(e){if(e.name==='AbortError')throw Error('识别等待超时或已停止，下一次读取会自动重试');if(e instanceof TypeError)throw Error(await connectionFailure(e));throw e;}
 finally{clearTimeout(timeout);if(matchController===controller)matchController=null;}
}
async function identify(forceFull=false){
 if((!frame&&!nativeSession)||busy)return;busy=true;let g=generation;
 try{
 let {payload,sig}=capturePayload(forceFull),out=await requestMatch(payload);if(g!==generation)return;
 if(out.capture_wait){
  recoveryActive=false;holdPosition();draw();captureMessage(out.reason);
  if(!receivedCaptureFrame&&performance.now()>firstFrameDeadline)$('reason').textContent='本地采集暂未收到新画面，请保持游戏窗口打开且不要最小化；持续无画面请停止后重新连接。';
  return;
 }
 if(out.native_capture){
  const meta=out.native_capture;nativeCost=Number(meta.processing_ms)||0;nativeSequence=meta.sequence;currentCaptureAt=meta.captured_at;sig=meta.signature;
  receivedCaptureFrame=true;$('capture-status').textContent='本地采集中';
  if(meta.preview){const im=new Image();im.src=meta.preview;await im.decode();if(g!==generation)return;cap.width=im.width;cap.height=im.height;cc.drawImage(im,0,0);previewFrameAt=Date.now();$('empty').hidden=true;}
 }
 if(out.requires_full_frame){
   ({payload,sig}=capturePayload(true));out=await requestMatch(payload);if(g!==generation)return;
 }
 recoveryActive=!!out.recovering;updateLoot(out);
 if(out.method==='minimap'){
   if(out.status==='paused'){showTrackingPaused();draw();return;}
   result=out.status==='matched'?out.candidates[0]:null;
   $('position-status').textContent=result?'小地图追踪中 · 每帧重新定位':'小地图定位暂停';
   $('result').textContent=result?'实时位置 · '+result.name:tracking?'已锁定地图 · 暂未定位':'请先打开大地图';
   $('reason').textContent=out.reason;$('candidates').replaceChildren();
   if(result){rememberPosition(result);if(current?.id!==result.id)await loadMap(result.id);}else{holdPosition();if(out.reason)$('reason').textContent=out.reason;}
   draw();return;
 }
 $('position-status').textContent='正在确认地图与位置';
 if(out.status==='loading'){if(!holdPosition())notice('地图索引仍在准备，稍后再识别。');draw();return;}
 if(out.status==='matched'){confirmMap(out.candidates?.[0]);g=generation;}
 const tallies=evidence(out,sig);result=out.status==='matched'?out.candidates[0]:null;
 const ranked=[...(out.candidates||[])].sort((a,b)=>(tallies.get(b.id)?.value||0)-(tallies.get(a.id)?.value||0));
 const leader=ranked[0],lt=leader&&tallies.get(leader.id),runner=ranked[1]&&tallies.get(ranked[1].id);
 const currentLead=out.candidates?.[0],currentRunner=out.candidates?.[1];
 const clearLead=leader?.id===currentLead?.id&&(!currentRunner||(currentLead.score-currentRunner.score>=8&&currentLead.score>=currentRunner.score*1.2));
 const eligible=leader&&(leader.method==='doors'?leader.score>=45:leader.inliers>=10&&leader.score>=8);
 // Two distinct explored views can confirm a clearly leading candidate.
 // Repeating the same still image does not count as new evidence.
 const accumulated=!result&&clearLead&&eligible&&lt?.frames>=2&&lt.value>(runner?.value||0)*1.5;
 if(accumulated)result=leader;
 if(result){confirmMap(result);g=generation;rememberPosition(result);}
 $('position-status').textContent=result?.position?(out.position_source==='manual'?'手动位置 · 点重置恢复自动追踪':'已定位角色 · 可关闭大地图继续追踪'):out.position_source==='auto'?'已看到箭头，但尚未确认地图位置':'当前画面无法定位角色';
 $('result').textContent=result?(accumulated?'探索推测 · ':'当前匹配 · ')+result.name:out.status==='uncertain'?'仍有多个候选':'当前画面无法确认';
 $('reason').textContent=(accumulated?'连续探索更支持这张地图，仍请核对主门和岔路。':out.reason)+` 已记录 ${history.length} 个有变化的探索画面。`;
 $('candidates').replaceChildren();let moreCandidates=null;for(const [index,c] of ranked.entries()){const t=tallies.get(c.id);const b=document.createElement('button');const detail=c.method==='doors'?`两门＋地形 ${Math.round(c.score)}分`:`${c.inliers} 个吻合特征`;const rank=document.createElement('span');rank.className='candidate-rank';rank.textContent=String(index+1).padStart(2,'0');const content=document.createElement('span'),title=document.createElement('span'),meta=document.createElement('span');title.className='candidate-title';title.textContent=c.name;meta.className='candidate-meta';meta.textContent=`${detail} · 历史首选 ${t?.frames||0} 次`;content.append(title,meta);b.append(rank,content);b.title='地形分是相对匹配指标，不代表正确概率。';b.onclick=async()=>{try{generation++;await loadMap(c.id);result=c;confirmMap(c);rememberPosition(c);$('result').textContent='已手动确认 · '+c.name;$('position-status').textContent=c.position?'已定位角色 · 可关闭大地图继续追踪':'已确认地图，请在大地图上标记角色位置';draw();}catch(e){notice(e.message);}};if(index===0){$('candidates').append(b);}else{if(!moreCandidates){moreCandidates=document.createElement('details');moreCandidates.className='more-candidates';const summary=document.createElement('summary');summary.textContent='其余 '+(ranked.length-1)+' 个候选';moreCandidates.append(summary);$('candidates').append(moreCandidates);}moreCandidates.append(b);}}
 if(!result)holdPosition();
 const displayed=result||leader;
 if(displayed&&current?.id!==displayed.id)await loadMap(displayed.id);
 if(!result&&leader){$('result').textContent='候选预览 · '+leader.name;$('reason').textContent+=' 当前仅预览候选，确认该地图可点击候选卡片开始追踪。';}
 if(!realtimeTracking){if(result&&!result.held)$('position-status').textContent='大地图位置已更新 · 实时定位已关闭';else showTrackingPaused();}
 draw();
 }catch(e){if(g!==generation)return;nativeRetryAfter=performance.now()+1000;if(nativeSession&&e.status===400)stop();recoveryActive=false;result=null;holdPosition();notice('识别暂不可用：'+e.message);draw();}finally{busy=false;}
}
$('once').onclick=()=>identify(true);$('fit').onclick=()=>{if(isSea()){seaView='all';$('sea-region').value='all';}fit();};
for(const r of seaRegions){const o=document.createElement('option');o.value=r.id;o.textContent=r.name;$('sea-region').append(o);}
$('sea-region').onchange=e=>{seaView=e.target.value;fit();};
$('region-follow').onclick=()=>{seaView='auto';$('sea-region').value='auto';fit();if(!result?.position||result.id!==current?.id)notice('请先打开游戏大地图定位；也可以在分区列表手动选择。');};
$('focus').onclick=()=>{const active=document.body.classList.toggle('focus-mode');$('focus').textContent=active?'显示控制台':'专注地图';$('focus').setAttribute('aria-pressed',String(active));requestAnimationFrame(fit);};
function zoomBy(factor){const x=canvas.clientWidth/2,y=canvas.clientHeight/2,z=Math.max(.08,Math.min(8,zoom*factor));ox=x-(x-ox)*z/zoom;oy=y-(y-oy)*z/zoom;zoom=z;draw();}
$('zoom-in').onclick=()=>zoomBy(1.3);$('zoom-out').onclick=()=>zoomBy(1/1.3);
document.querySelector('.upload').onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();$('file').click();}};
async function status(){try{const s=await fetch('/api/status').then(r=>r.json());$('engine').title=s.error||'';if(s.error)notice('识别引擎异常：'+s.error);$('engine').textContent=s.error?'识别引擎异常':s.ready?`${s.indexed} 张地图 · 本地识别就绪${s.version?" · v"+s.version:""}`:`正在索引 ${s.indexed} 张地图…`;if(!s.ready&&!s.error)setTimeout(status,1500);}catch(e){$('engine').textContent='本地服务未连接';}}
async function init(){await loadPointImages();await loadMap('sanctum-31');status();overlayStatus();}init().catch(e=>notice('地图加载失败：'+e.message));
const buttonIcons={newrun:'reset',focus:'focus','native-start':'monitor',stop:'stop',once:'scan',fit:'focus','zoom-in':'plus','zoom-out':'minus'};
function decorateButtons(){for(const [id,name]of Object.entries(buttonIcons)){const el=$(id);if(!el||el.querySelector('.ui-icon'))continue;if(id==='source')el.textContent=el.textContent.replace(' ↗','');if(id==='zoom-in'||id==='zoom-out')el.replaceChildren();el.prepend(icon(name));}const label=document.querySelector('.upload');if(!label.querySelector('.ui-icon'))label.prepend(icon('upload'));}
decorateButtons();for(const id of Object.keys(buttonIcons))new MutationObserver(decorateButtons).observe($(id),{childList:true});document.querySelector('.brand>b').replaceChildren(icon('compass'));document.querySelector('#empty>span').replaceChildren(icon('monitor'));

function pointName(point){
 if(I18N.language!=='en')return point.name+(point.note?' · '+point.note:'');
 const translated=t(point.name);
 if(!/[\u3400-\u9fff]/.test(translated))return translated;
 // Unknown proper names retain their source spelling after an English category.
 const category=current?.categories.find(c=>c.id===point.category);
 return t(category?.name||point.category)+' ('+point.name+')';
}
window.addEventListener('languagechange',()=>{draw();publishOverlay(true);});

// Restore only supported intervals; storage may be unavailable in private mode.
try {
 const saved=localStorage.getItem('aniimo-scan-interval');
 const migrateAuto=localStorage.getItem('aniimo-interval-default-version')!=='2'&&saved==='auto';
 if(!migrateAuto&&['auto','250','500','1000','2000','3000'].includes(saved)) $('interval').value=saved;
 if(migrateAuto)localStorage.setItem('aniimo-scan-interval','500');
 localStorage.setItem('aniimo-interval-default-version','2');
} catch(e) {}
$('interval').onchange=()=>{syncQuality();try {localStorage.setItem('aniimo-scan-interval',$('interval').value);} catch(e) {}};
