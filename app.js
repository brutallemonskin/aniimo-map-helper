const $=id=>document.getElementById(id), cap=$('capture'), cc=cap.getContext('2d'), canvas=$('map'), ctx=canvas.getContext('2d');
let catalog=[], current=null, bitmap=null, zoom=1, ox=0, oy=0, enabled=new Set(), result=null, mapBounds=null, mapLoadVersion=0;
let stream=null, frame=null, busy=false, timer=null, running=false, history=[], lastSignature=null, generation=0;
let tracking=null, trackedAt=0, lastKnown=null;
let overlayEnabled=false,overlaySending=false,overlayLastSent=0,overlayPending=false;
function overlayButton(){ $('overlay').textContent=overlayEnabled?'关闭悬浮窗':'游戏悬浮窗';$('overlay').setAttribute('aria-pressed',String(overlayEnabled)); }
async function publishOverlay(force=false){
 if(!overlayEnabled)return;
 if(overlaySending){overlayPending=true;return;}
 if(!force&&Date.now()-overlayLastSent<200)return;
 overlaySending=true;overlayLastSent=Date.now();
 try{
   const dungeon=bitmap&&current?.id.startsWith('sanctum-');
   const confirmed=result?.id===current?.id;
   let image=null,title='等待识别地宫';
   if(dungeon){
     const copy=document.createElement('canvas');copy.width=504;copy.height=350;
     const b=mapBounds||{x:0,y:0,w:current.width,h:current.height},z=Math.min(copy.width/b.w,copy.height/b.h)*.94;
     paintMap(copy.getContext('2d'),z,(copy.width-b.w*z)/2-b.x*z,(copy.height-b.h*z)/2-b.y*z,.8);
     image=copy.toDataURL('image/png');
     title=current.name+(!confirmed?' · 地图预览 · 尚未确认':result.held?' · 保留上次位置':result.position?' · 你的位置':' · 等待角色定位');
   }
   const response=await fetch('/api/overlay/frame',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({image,title:t(title),language:I18N.language})});
   if(!response.ok)throw Error('悬浮窗同步失败');
 }catch(e){$('overlay-hint').textContent='悬浮窗暂未同步，请检查本地服务。';}finally{overlaySending=false;if(overlayPending){overlayPending=false;publishOverlay(true);}}
}
$('overlay').onclick=async()=>{
 $('overlay').disabled=true;
 try{const response=await fetch('/api/overlay',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action:overlayEnabled?'stop':'start'})});const state=await response.json();if(!response.ok)throw Error(state.error);overlayEnabled=state.enabled;overlayButton();await publishOverlay(true);}
 catch(e){$('overlay-hint').textContent='悬浮窗未启动：'+e.message;}finally{$('overlay').disabled=false;}
};
async function overlayStatus(){
 try{const response=await fetch('/api/overlay');if(response.ok){const state=await response.json();const justOpened=!overlayEnabled&&state.enabled;overlayEnabled=state.enabled;overlayButton();if(justOpened)await publishOverlay(true);}}
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
function rememberPosition(candidate){if(candidate?.position){tracking={id:candidate.id,position:candidate.position,scale:candidate.minimap_scale};trackedAt=Date.now();lastKnown={...candidate};}else if(candidate&&lastKnown?.id!==candidate.id){tracking=null;lastKnown=null;}}
function holdPosition(){if(!lastKnown)return false;result={...lastKnown,held:true,polygon:[]};$('position-status').textContent='位置暂未更新 · 保留上次位置';$('result').textContent='位置保留 · '+lastKnown.name;$('reason').textContent=`画面暂时无法定位，按仍在原处显示。上次定位 ${Math.max(0,Math.floor((Date.now()-trackedAt)/1000))} 秒前；地图恢复后自动继续。`;return true;}
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
function markerStyle(category,color){if(category==='sanctums')return {icon:'door',color:'#82beff',size:22};if(category==='teleporters'||category==='extraction')return {icon:'star',color:'#8ee0c4',size:22};if(category==='entrance')return {icon:'door',color:'#ffd36b',size:27,label:'黄门'};if(category==='side-entrance')return {icon:'side',color:'#82beff',size:27,label:'蓝门'};if(category.includes('egg'))return {icon:'egg',color:'#ffe9b0',size:20};if(category.includes('chest'))return {icon:'chest',color:color||'#ffc662',size:18};if(category.includes('key-room'))return {icon:'key',color:color||'#ffd36b',size:20};if(category==='merchants')return {icon:'shop',color:'#8ee0c4',size:20};if(category==='aniimo'||category.includes('spawn'))return {icon:'creature',color:color||'#ef9aab',size:18};if(category==='rooms')return {icon:'room',color:'#acbbc9',size:17};if(category.includes('unique'))return {icon:'star',color:'#c9acff',size:20};if(category.includes('boat'))return {icon:'boat',color:'#89d9f5',size:22};return {icon:'diamond',color:color||'#d7e2ed',size:18};}
function drawMarker(p,style,ctx,zoom,markerScale=1){const {color}=style;const size=style.size*1.4*markerScale;ctx.save();ctx.translate(p.x,p.y);ctx.scale(1/zoom,1/zoom);ctx.shadowColor='#0009';ctx.shadowBlur=3;ctx.fillStyle='#101b25';ctx.strokeStyle=color;ctx.lineWidth=1.15;ctx.beginPath();ctx.arc(0,0,size/2,0,Math.PI*2);ctx.fill();ctx.stroke();ctx.shadowBlur=0;const s=(size-5)/24;ctx.scale(s,s);ctx.translate(-12,-12);ctx.lineWidth=1.9;ctx.lineCap='round';ctx.lineJoin='round';ctx.stroke(iconPaths[style.icon]);ctx.restore();if(style.label){ctx.save();ctx.font=`600 ${11*Math.max(.75,markerScale)/zoom}px sans-serif`;ctx.lineWidth=3/zoom;ctx.strokeStyle='#0b141e';ctx.strokeText(t(style.label),p.x+(size/2+5)/zoom,p.y+4/zoom);ctx.fillStyle=color;ctx.fillText(t(style.label),p.x+(size/2+5)/zoom,p.y+4/zoom);ctx.restore();}}
function newRun(){seaView='auto';$('sea-region').value='auto';history=[];lastSignature=null;result=null;tracking=null;lastKnown=null;trackedAt=0;generation++;$('position-status').textContent='先开大地图校准，再用小地图追踪';$('result').textContent='新一局 · 等待主门附近地图';$('reason').textContent='从黄门进入后打开地图，探索更多房间以缩小候选。';$('candidates').replaceChildren();draw();}
function notice(text){$('reason').textContent=text;}
async function loadMap(id){
 const requestVersion=++mapLoadVersion;
 const d=await fetch('/data/'+id+'.json',{cache:'no-store'}).then(r=>r.json());
 const im=new Image();im.src=d.image;await im.decode();if(requestVersion!==mapLoadVersion)return;current=d;bitmap=im;
 const measure=document.createElement('canvas');measure.width=256;measure.height=256;const mc=measure.getContext('2d');mc.drawImage(im,0,0,256,256);const pixels=mc.getImageData(0,0,256,256).data;let left=256,top=256,right=0,bottom=0;for(let y=0;y<256;y++)for(let x=0;x<256;x++){const i=(y*256+x)*4;if((pixels[i]+pixels[i+1]+pixels[i+2])/3>85){left=Math.min(left,x);right=Math.max(right,x);top=Math.min(top,y);bottom=Math.max(bottom,y);}}mapBounds=right>left?{x:Math.max(0,left-8)*d.width/256,y:Math.max(0,top-8)*d.height/256,w:Math.min(256,right-left+16)*d.width/256,h:Math.min(256,bottom-top+16)*d.height/256}:{x:0,y:0,w:d.width,h:d.height};
 enabled=new Set(d.categories.filter(c=>/egg|entrance|legendary|key-room|sanctums|teleporters|extraction/.test(c.id)).map(c=>c.id));
 $('filters').replaceChildren();for(const c of d.categories){const l=document.createElement('label'), i=document.createElement('input'),style=markerStyle(c.id,c.color);i.type='checkbox';i.checked=enabled.has(c.id);i.onchange=()=>{i.checked?enabled.add(c.id):enabled.delete(c.id);draw();};l.append(i,icon(style.icon),document.createTextNode(style.label||c.name));l.style.color=style.color;$('filters').append(l);}
 $('mapinfo').textContent=`${d.name} · ${d.width} × ${d.height} · ${d.points.length} 条点位`;fit();
}
function fit(){if(!current)return;syncSeaRegion();const b=regionBounds()||mapBounds||{x:0,y:0,w:current.width,h:current.height};zoom=Math.min(canvas.clientWidth/b.w,canvas.clientHeight/b.h)*.90;ox=(canvas.clientWidth-b.w*zoom)/2-b.x*zoom;oy=(canvas.clientHeight-b.h*zoom)/2-b.y*zoom;draw();}
function paintMap(ctx,zoom,ox,oy,markerScale=1){
 ctx.save();ctx.translate(ox,oy);ctx.scale(zoom,zoom);const crop=regionBounds();if(crop){ctx.beginPath();ctx.rect(crop.x,crop.y,crop.w,crop.h);ctx.clip();}ctx.drawImage(bitmap,0,0,current.width,current.height);
 const seen=new Set(),doors=[];for(const p of current.points){if(!enabled.has(p.category))continue;const key=p.category+':'+p.x+':'+p.y;if(seen.has(key))continue;seen.add(key);if(p.category==='entrance'||p.category==='side-entrance'){doors.push(p);continue;}const cat=current.categories.find(c=>c.id===p.category);drawMarker(p,markerStyle(p.category,cat?.color),ctx,zoom,markerScale);}for(const p of doors)drawMarker(p,markerStyle(p.category),ctx,zoom,markerScale);
 if(result&&result.id===current.id){ctx.strokeStyle='#58ead2';ctx.fillStyle='#58ead213';ctx.lineWidth=2/zoom;ctx.beginPath();result.polygon.forEach((p,i)=>i?ctx.lineTo(...p):ctx.moveTo(...p));ctx.closePath();ctx.fill();ctx.stroke();if(result.position){ctx.fillStyle=result.held?'#e6b75b':'#ff7188';ctx.beginPath();ctx.arc(...result.position,9/zoom,0,Math.PI*2);ctx.fill();ctx.strokeStyle='#fff';ctx.lineWidth=2/zoom;ctx.stroke();ctx.font=`600 ${12/zoom}px sans-serif`;ctx.fillStyle='#fff';ctx.strokeStyle='#111b29';ctx.lineWidth=3/zoom;const playerLabel=t(result.held?'你·上次':result.position_source==='auto'?'你':'手动');ctx.strokeText(playerLabel,result.position[0]+14/zoom,result.position[1]+4/zoom);ctx.fillText(playerLabel,result.position[0]+14/zoom,result.position[1]+4/zoom);}}
 ctx.restore();
}
function draw(){
 if(current&&syncSeaRegion()){fit();return;}
 const w=canvas.clientWidth,h=canvas.clientHeight,dpr=devicePixelRatio; if(canvas.width!==Math.round(w*dpr)||canvas.height!==Math.round(h*dpr)){canvas.width=Math.round(w*dpr);canvas.height=Math.round(h*dpr);}ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,w,h);if(!bitmap)return;
 paintMap(ctx,zoom,ox,oy);$('viewmode').textContent=isSea()?(activeSeaRegion&&seaView!=='all'?activeSeaRegion.name+' · 分区地图':'全岛总览'):(result&&result.id===current.id?(result.held?'保留上次位置':'匹配范围'):'全图浏览');
 publishOverlay();
}
let drag=null;canvas.onpointerdown=e=>{drag={x:e.clientX,y:e.clientY,ox,oy};canvas.setPointerCapture(e.pointerId);};canvas.onpointermove=e=>{if(drag){ox=drag.ox+e.clientX-drag.x;oy=drag.oy+e.clientY-drag.y;draw();}};canvas.onpointerup=e=>{if(drag&&Math.hypot(e.clientX-drag.x,e.clientY-drag.y)<5&&current){const r=canvas.getBoundingClientRect(),x=(e.clientX-r.left-ox)/zoom,y=(e.clientY-r.top-oy)/zoom;const near=current.points.filter(p=>enabled.has(p.category)&&Math.hypot(p.x-x,p.y-y)<20/zoom);$('tooltip').textContent=[...new Set(near.map(p=>pointName(p)))].join(' / ');$('tooltip').style.display=near.length?'block':'none';}drag=null;};canvas.onwheel=e=>{e.preventDefault();const r=canvas.getBoundingClientRect(),x=e.clientX-r.left,y=e.clientY-r.top;const z=Math.max(.08,Math.min(8,zoom*Math.exp(-e.deltaY*.001)));ox=x-(x-ox)*z/zoom;oy=y-(y-oy)*z/zoom;zoom=z;draw();};
new ResizeObserver(()=>fit()).observe($('mapwrap'));
function preview(){if(!frame)return;cc.clearRect(0,0,cap.width,cap.height);cc.drawImage(frame,0,0,cap.width,cap.height);$('empty').hidden=true;}
$('newrun').onclick=newRun;$('outdoor-mode').onchange=()=>{newRun();notice('海岛模式已更换，请打开大地图重新校准。');};
async function importFile(file){if(!file||!file.type.startsWith('image/'))return;stop();const im=await createImageBitmap(file);frame=im;cap.width=im.width;cap.height=im.height;newRun();$('capture-status').textContent='截图模式';preview();await identify();}
$('file').onchange=e=>importFile(e.target.files[0]).catch(e=>notice(e.message));document.onpaste=e=>{const f=[...e.clipboardData.items].find(i=>i.type.startsWith('image/'));if(f)importFile(f.getAsFile()).catch(e=>notice(e.message));};
let captureEpoch=0,firstFrameDeadline=0,receivedCaptureFrame=false;
function captureMessage(text){$('capture-status').textContent=text;$('empty').textContent=text;$('empty').hidden=false;}
function stop(){
 captureEpoch++;running=false;clearTimeout(timer);timer=null;
 const previous=stream;stream=null;
 if(previous)previous.getTracks().forEach(t=>{t.onended=null;t.stop();});
 const video=$('video');video.pause?.();video.srcObject=null;frame=null;
 $('stop').disabled=true;$('share').disabled=false;captureMessage('未连接画面');generation++;
}
$('stop').onclick=()=>{stop();notice('已停止读取游戏画面。');};
$('share').onclick=async()=>{
 stop();const epoch=captureEpoch;$('share').disabled=true;$('stop').disabled=false;
 captureMessage('请选择要共享的游戏窗口');
 try{
  if(!navigator.mediaDevices?.getDisplayMedia)throw Error('当前浏览器不支持窗口读取，请用 Chrome 或 Edge 打开本地地址。');
  const selected=await navigator.mediaDevices.getDisplayMedia({video:{frameRate:{ideal:8,max:8}},audio:false});
  if(epoch!==captureEpoch){selected.getTracks().forEach(t=>t.stop());return;}
  stream=selected;const track=selected.getVideoTracks()[0];
  if(!track||track.readyState==='ended')throw Error('所选窗口的共享已经结束，请重新选择。');
  track.onended=()=>{if(epoch!==captureEpoch)return;stop();notice('窗口共享已结束。');};
  const video=$('video');video.muted=true;video.playsInline=true;video.srcObject=selected;
  running=true;receivedCaptureFrame=false;firstFrameDeadline=performance.now()+12000;newRun();
  captureMessage('已授权，正在等待游戏画面');notice('请切回游戏并保持窗口打开；收到画面后会自动开始识别。');
  // A play promise may remain pending until the source supplies its first
  // frame. Do not let it block status updates, cancellation or the watchdog.
  Promise.resolve(video.play()).catch(e=>{if(epoch!==captureEpoch)return;stop();notice('画面播放失败：'+e.message);});
  tick(epoch);
 }catch(e){if(epoch!==captureEpoch)return;stop();notice(e.name==='NotAllowedError'?'共享已取消或未获授权，请重新选择游戏窗口。':'未开始读取：'+e.message);}
};
function scanDelay(interval,elapsed){return Math.max(50,elapsed*.5,interval-elapsed);}
async function tick(epoch=captureEpoch){
 if(!running||epoch!==captureEpoch)return;const started=performance.now();
 try{
  const video=$('video');const track=stream?.getVideoTracks()[0];
  if(!track||track.readyState==='ended'){stop();notice('窗口共享已结束。');return;}
  if(video.readyState>=2&&video.videoWidth>0&&video.videoHeight>0&&!track.muted){
   cap.width=video.videoWidth;cap.height=video.videoHeight;frame=video;preview();
   if(!receivedCaptureFrame){receivedCaptureFrame=true;notice('已收到游戏画面，正在识别。');}
   $('capture-status').textContent='持续识别中';await identify();
  }else if(!receivedCaptureFrame&&performance.now()>firstFrameDeadline){
   stop();notice('已授权，但 12 秒内未收到游戏画面。请保持游戏窗口打开且不要最小化；仍无画面时，可在共享框中尝试“整个屏幕”。');
  }else captureMessage(receivedCaptureFrame?'画面暂时暂停，请切回游戏':'已授权，正在等待游戏画面');
 }catch(e){if(epoch===captureEpoch)notice('读取画面失败：'+e.message);}
 finally{if(running&&epoch===captureEpoch)timer=setTimeout(()=>tick(epoch),receivedCaptureFrame?scanDelay(Number($('interval').value),performance.now()-started):200);}
}
function signature(){const c=document.createElement('canvas');c.width=c.height=32;const x=c.getContext('2d');x.drawImage(temp,0,0,32,32);const d=x.getImageData(0,0,32,32).data;return Array.from({length:1024},(_,i)=>Math.round((d[i*4]+d[i*4+1]+d[i*4+2])/24));}
function evidence(r,sig){
 const changed=!lastSignature||sig.reduce((s,v,i)=>s+Math.abs(v-lastSignature[i]),0)/sig.length>.7;
 if(changed&&r.candidates?.length){history.push(r.candidates.map(c=>({id:c.id,score:c.score})));history=history.slice(-8);lastSignature=sig;}
 const tally=new Map();history.forEach((list,i)=>{const top=list[0]?.score||1;list.forEach(c=>{let t=tally.get(c.id)||{value:0,frames:0};t.value+=c.score/top*Math.pow(.85,history.length-1-i);if(c.id===list[0].id)t.frames++;tally.set(c.id,t);});});
 return tally;
}
async function identify(){
 if(!frame||busy)return;busy=true;const g=generation;
 try{const w=cap.width,h=cap.height,r={x:0,y:0,w:1,h:1};temp.width=Math.max(1,Math.round(w*r.w));temp.height=Math.max(1,Math.round(h*r.h));tc.drawImage(frame,w*r.x,h*r.y,w*r.w,h*r.h,0,0,temp.width,temp.height);
 const sig=signature();
 const response=await fetch('/api/match',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({image:temp.toDataURL('image/jpeg',.9),anchor:null,tracking:tracking,outdoor_mode:$('outdoor-mode').value})});const out=await response.json();if(g!==generation)return;if(!response.ok)throw Error(out.error||'识别失败');
 if(out.method==='minimap'){
   result=out.status==='matched'?out.candidates[0]:null;
   $('position-status').textContent=result?'小地图追踪中 · 每帧重新定位':'小地图定位暂停';
   $('result').textContent=result?'实时位置 · '+result.name:tracking?'已锁定地图 · 暂未定位':'请先打开大地图';
   $('reason').textContent=out.reason;$('candidates').replaceChildren();
   if(result){rememberPosition(result);if(current?.id!==result.id)await loadMap(result.id);}else{holdPosition();}
   draw();return;
 }
 $('position-status').textContent='正在确认地图与位置';
 if(out.status==='loading'){if(!holdPosition())notice('地图索引仍在准备，稍后再识别。');draw();return;}
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
 if(result)rememberPosition(result);
 $('position-status').textContent=result?.position?(out.position_source==='manual'?'手动位置 · 点重置恢复自动追踪':'已定位角色 · 可关闭大地图继续追踪'):out.position_source==='auto'?'已看到箭头，但尚未确认地图位置':'当前画面无法定位角色';
 $('result').textContent=result?(accumulated?'探索推测 · ':'当前匹配 · ')+result.name:out.status==='uncertain'?'仍有多个候选':'当前画面无法确认';
 $('reason').textContent=(accumulated?'连续探索更支持这张地图，仍请核对主门和岔路。':out.reason)+` 已记录 ${history.length} 个有变化的探索画面。`;
 $('candidates').replaceChildren();let moreCandidates=null;for(const [index,c] of ranked.entries()){const t=tallies.get(c.id);const b=document.createElement('button');const detail=c.method==='doors'?`两门＋地形 ${Math.round(c.score)}分`:`${c.inliers} 个吻合特征`;const rank=document.createElement('span');rank.className='candidate-rank';rank.textContent=String(index+1).padStart(2,'0');const content=document.createElement('span'),title=document.createElement('span'),meta=document.createElement('span');title.className='candidate-title';title.textContent=c.name;meta.className='candidate-meta';meta.textContent=`${detail} · 历史首选 ${t?.frames||0} 次`;content.append(title,meta);b.append(rank,content);b.title='地形分是相对匹配指标，不代表正确概率。';b.onclick=async()=>{try{generation++;await loadMap(c.id);result=c;rememberPosition(c);$('result').textContent='已手动确认 · '+c.name;$('position-status').textContent=c.position?'已定位角色 · 可关闭大地图继续追踪':'已确认地图，请在大地图上标记角色位置';draw();}catch(e){notice(e.message);}};if(index===0){$('candidates').append(b);}else{if(!moreCandidates){moreCandidates=document.createElement('details');moreCandidates.className='more-candidates';const summary=document.createElement('summary');summary.textContent='其余 '+(ranked.length-1)+' 个候选';moreCandidates.append(summary);$('candidates').append(moreCandidates);}moreCandidates.append(b);}}
 if(!result)holdPosition();
 const displayed=result||leader;
 if(displayed&&current?.id!==displayed.id)await loadMap(displayed.id);
 if(!result&&leader){$('result').textContent='候选预览 · '+leader.name;$('reason').textContent+=' 当前仅预览候选，确认该地图可点击候选卡片开始追踪。';}
 draw();
 }catch(e){result=null;if(!holdPosition())notice('识别暂不可用：'+e.message);draw();}finally{busy=false;}
}
$('once').onclick=identify;$('fit').onclick=()=>{if(isSea()){seaView='all';$('sea-region').value='all';}fit();};
for(const r of seaRegions){const o=document.createElement('option');o.value=r.id;o.textContent=r.name;$('sea-region').append(o);}
$('sea-region').onchange=e=>{seaView=e.target.value;fit();};
$('region-follow').onclick=()=>{seaView='auto';$('sea-region').value='auto';fit();if(!result?.position||result.id!==current?.id)notice('请先打开游戏大地图定位；也可以在分区列表手动选择。');};
$('focus').onclick=()=>{const active=document.body.classList.toggle('focus-mode');$('focus').textContent=active?'显示控制台':'专注地图';$('focus').setAttribute('aria-pressed',String(active));requestAnimationFrame(fit);};
function zoomBy(factor){const x=canvas.clientWidth/2,y=canvas.clientHeight/2,z=Math.max(.08,Math.min(8,zoom*factor));ox=x-(x-ox)*z/zoom;oy=y-(y-oy)*z/zoom;zoom=z;draw();}
$('zoom-in').onclick=()=>zoomBy(1.3);$('zoom-out').onclick=()=>zoomBy(1/1.3);
document.querySelector('.upload').onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();$('file').click();}};
async function status(){try{const s=await fetch('/api/status').then(r=>r.json());$('engine').title=s.error||'';if(s.error)notice('识别引擎异常：'+s.error);$('engine').textContent=s.error?'识别引擎异常':s.ready?`${s.indexed} 张地图 · 本地识别就绪`:`正在索引 ${s.indexed} 张地图…`;if(!s.ready&&!s.error)setTimeout(status,1500);}catch(e){$('engine').textContent='本地服务未连接';}}
async function init(){await loadMap('sanctum-31');status();overlayStatus();}init().catch(e=>notice('地图加载失败：'+e.message));
const buttonIcons={newrun:'reset',focus:'focus',share:'monitor',stop:'stop',once:'scan',fit:'focus','zoom-in':'plus','zoom-out':'minus'};
function decorateButtons(){for(const [id,name]of Object.entries(buttonIcons)){const el=$(id);if(!el||el.querySelector('.ui-icon'))continue;if(id==='source')el.textContent=el.textContent.replace(' ↗','');if(id==='zoom-in'||id==='zoom-out')el.replaceChildren();el.prepend(icon(name));}const label=document.querySelector('.upload');if(!label.querySelector('.ui-icon'))label.prepend(icon('upload'));}
decorateButtons();for(const id of Object.keys(buttonIcons))new MutationObserver(decorateButtons).observe($(id),{childList:true});document.querySelector('.brand>b').replaceChildren(icon('compass'));document.querySelector('#empty>span').replaceChildren(icon('monitor'));

function pointName(point){
 if(I18N.language!=='en')return point.name;
 const translated=t(point.name);
 if(!/[\u3400-\u9fff]/.test(translated))return translated;
 // Unknown proper names retain their source spelling after an English category.
 const category=current?.categories.find(c=>c.id===point.category);
 return t(category?.name||point.category)+' ('+point.name+')';
}
window.addEventListener('languagechange',()=>{draw();publishOverlay(true);});

// Restore only supported intervals; storage may be unavailable in private mode.
try { const saved=localStorage.getItem('aniimo-scan-interval'); if(['250','500','1000','2000','3000'].includes(saved)) $('interval').value=saved; } catch(e) {}
$('interval').onchange=()=>{try {localStorage.setItem('aniimo-scan-interval',$('interval').value);} catch(e) {}};
