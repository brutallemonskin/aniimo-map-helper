/* Deliberately separate from official points, the run journal and route inputs. */
const MapNotes=(()=>{
 const el=id=>document.getElementById(id),kinds={point:'点位纠错',passage:'通路纠错',monster:'怪物实测',spawn:'刷新记录'};
 let records=[],draft=null,picking=null,anchor=null,shownMap=null,request=0,saving=false,press=null,selectedId=null;
 async function api(action,extra={}){
  const response=await fetch('/api/notes',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action,...extra})});
  if(action==='export'&&response.ok)return response.blob();
  const out=await response.json();if(!response.ok)throw Error(out.error||'记录操作失败');return out;
 }
 function status(text){el('notes-status').textContent=text;}
 function localRows(){return records.filter(r=>r.map===current?.id).reverse().sort((a,b)=>b.created.localeCompare(a.created));}
 function placements(z){const used=[];return localRows().map((row,index)=>{let position=[...row.position];for(let n=1;used.some(p=>Math.hypot(p[0]-position[0],p[1]-position[1])*z<34)&&n<300;n++){const offset=Math.ceil(n/2)*38/z*(n%2?1:-1);position=[row.position[0],row.position[1]+offset];}used.push(position);return {row,index,position};});}
 async function refresh(){try{const n=++request,out=await api('list');if(n!==request)return;records=out.records;render();draw();}catch(e){status(e.message);}}
 function render(){
  const rows=localRows();el('notes-count').textContent=String(rows.length);el('notes-list').replaceChildren();
  el('notes-export').disabled=!records.length;
  for(const [i,r] of rows.entries()){
   const row=document.createElement('div'),title=document.createElement('button'),text=document.createElement('small');row.className='note-row';
   title.textContent=`${i+1}. ${t(kinds[r.kind])} · ${r.subject||r.note||t('未填写说明')}`;row.classList.toggle('selected',r.id===selectedId);
   title.onclick=()=>edit(r.id);text.textContent=new Date(r.created).toLocaleString()+' · '+t('待核实');row.append(title,text);el('notes-list').append(row);
  }
  if(!rows.length){const p=document.createElement('p');p.className='scan-help';p.textContent=t('右键地图，记录你发现的问题或刷新情况。');el('notes-list').append(p);}
 }
 function closeMenu(){el('note-menu').hidden=true;}
 function cancelPick(){picking=null;el('note-pick-banner').hidden=true;canvas.style.cursor='';draw();}
 function coordinates(e){const r=canvas.getBoundingClientRect();return [(e.clientX-r.left-ox)/zoom,(e.clientY-r.top-oy)/zoom].map(v=>Math.round(v*10)/10);}
 function inside(p){return current&&p[0]>=0&&p[1]>=0&&p[0]<current.width&&p[1]<current.height;}
 function begin(position,kind='point'){
  if(!current||!inside(position))return;
  closeMenu();draft={map:current.id,map_name:current.name,kind,position,subject:'',note:'',mode:'unknown',difficulty:'unknown',rank:'unknown',passage:'unknown'};
  if(kind==='passage')pickEnd();else open();
 }
 function pickEnd(){if(draft.map!==current?.id){el('note-error').textContent=t('地图已切换，请回到记录对应的地图再选择终点。');return;}el('note-dialog').close();picking={map:draft.map,position:draft.position};el('note-pick-text').textContent=t('请点击通路的另一端');el('note-pick-banner').hidden=false;canvas.style.cursor='crosshair';draw();}
 function open(){
  el('note-heading').textContent=t(draft.id?'编辑实测记录':'添加实测记录');
  el('note-location').textContent=`${draft.map_name} · (${draft.position.map(Math.round).join(', ')})`+(draft.end?' → ('+draft.end.map(Math.round).join(', ')+')':'');
  for(const k of ['kind','subject','note','mode','difficulty','rank','passage'])el('note-'+k).value=draft[k]||'';
  el('note-error').textContent='';el('note-delete').hidden=!draft.id;el('note-options').open=!!draft.id;kindFields();imagePreview();el('note-dialog').showModal();draw();
 }
 function kindFields(){const k=el('note-kind').value;el('note-rank-row').hidden=k!=='monster';el('note-passage-row').hidden=k!=='passage';el('note-subject').placeholder=k==='monster'?'必填，例如：星骑士':'选填，例如：蛋巢 / 金色宝箱';}
 function readDraft(){for(const k of ['kind','subject','note','mode','difficulty','rank','passage'])draft[k]=el('note-'+k).value;}
 async function edit(id){closeMenu();try{const r=await api('detail',{id});if(r.map!==current?.id)return;draft=r;selectedId=id;render();open();}catch(e){status(e.message);}}
 function imagePreview(){el('note-image').hidden=!draft.screenshot;el('note-image').src=draft.screenshot||'';el('note-remove-image').hidden=!draft.screenshot;el('note-image-time').textContent=draft.screenshot?t('附图时间')+'：'+(draft.image_time?new Date(draft.image_time).toLocaleString():'—'):t('不自动附图');}
 async function save(){
  if(saving)return;readDraft();if(draft.kind==='passage'&&!draft.end){pickEnd();return;}
  saving=true;el('note-save').disabled=true;el('note-delete').disabled=true;
  try{const saved=await api('save',{record:draft});selectedId=saved.id;el('notes-show').checked=true;el('notes-panel').open=true;el('note-dialog').close();status(t('玩家标记已保存在地图上；刷新和重启后仍保留。'));await refresh();}
  catch(e){el('note-error').textContent=e.message;}finally{saving=false;el('note-save').disabled=false;el('note-delete').disabled=false;}
 }
 function paint(context,z){
  const pending=el('note-dialog')?.open&&!draft?.id&&draft?.map===current?.id?draft:null;
  if(!el('notes-show')?.checked&&!picking&&!pending)return;
  context.save();context.lineWidth=2/z;context.strokeStyle='#58dacf';context.fillStyle='#12312f';context.font=`bold ${11/z}px sans-serif`;context.textAlign='center';context.textBaseline='middle';
  const rows=el('notes-show').checked?placements(z):[];
  for(const {row:r,index:i,position} of rows){
   if(r.end){context.setLineDash([6/z,4/z]);context.beginPath();context.moveTo(...r.position);context.lineTo(...r.end);context.stroke();context.setLineDash([]);context.beginPath();context.arc(...r.end,4/z,0,Math.PI*2);context.stroke();}
   if(position[1]!==r.position[1]){context.beginPath();context.moveTo(...r.position);context.lineTo(...position);context.stroke();}
   context.save();context.translate(...position);context.scale(1/z,1/z);
   if(r.id===selectedId){context.strokeStyle='#fff';context.lineWidth=2;context.beginPath();context.arc(0,0,20,0,Math.PI*2);context.stroke();}
   context.lineWidth=2;context.beginPath();context.moveTo(0,-14);context.lineTo(14,0);context.lineTo(0,14);context.lineTo(-14,0);context.closePath();context.fill();context.stroke();context.fillStyle='#b9fff7';context.font='bold 11px sans-serif';context.fillText(String(i+1),0,0);
   const label=t(r.kind==='point'||r.kind==='passage'?'玩家纠错':'玩家实测')+' · '+t(kinds[r.kind]);context.font='11px sans-serif';context.textAlign='left';const w=context.measureText(label).width;const flip=ox+r.position[0]*z+w+30>canvas.clientWidth;const x=flip?-w-28:20;
   context.fillStyle='#102d2ded';context.fillRect(x-5,-11,w+10,22);context.fillStyle='#a4eee3';context.fillText(label,x,0);context.restore();
  }
  if(picking?.position){context.beginPath();context.arc(...picking.position,14/z,0,Math.PI*2);context.stroke();}
  if(pending){context.setLineDash([4/z,3/z]);context.beginPath();context.arc(...pending.position,17/z,0,Math.PI*2);context.stroke();context.setLineDash([]);context.textAlign='left';context.fillStyle='#b9fff7';context.fillText(t('待保存'),pending.position[0]+22/z,pending.position[1]);}
  context.restore();
 }
 function syncMap(){if(shownMap!==current?.id){shownMap=current?.id;closeMenu();if(picking){const unfinished=!!picking.position;cancelPick();if(unfinished){open();el('note-error').textContent=t('地图已切换，请回到记录对应的地图再选择终点。');}}render();}}
 document.addEventListener('DOMContentLoaded',()=>{
  canvas.addEventListener('contextmenu',e=>{
   e.preventDefault();if(picking||!current)return;anchor=coordinates(e);if(!inside(anchor))return;closeMenu();
   const menu=el('note-menu');menu.hidden=false;menu.style.left=Math.min(e.clientX,innerWidth-menu.offsetWidth-12)+'px';menu.style.top=Math.min(e.clientY,innerHeight-menu.offsetHeight-12)+'px';
   menu.querySelector('button').focus();
  });
  for(const k of Object.keys(kinds))el('note-add-'+k).onclick=()=>begin(anchor,k);
  document.addEventListener('pointerdown',e=>{if(!el('note-menu').contains(e.target))closeMenu();});
  window.addEventListener('blur',closeMenu);window.addEventListener('resize',closeMenu);
  document.addEventListener('keydown',e=>{if(e.key==='Escape'){closeMenu();if(picking)cancelPick();}});
  canvas.addEventListener('pointerdown',e=>{if(!picking||e.button!==0)return;e.preventDefault();e.stopImmediatePropagation();const p=coordinates(e);if(!inside(p))return;if(!picking.position){cancelPick();begin(p);return;}if(Math.hypot(p[0]-picking.position[0],p[1]-picking.position[1])<4)return;draft.end=p;cancelPick();open();},true);
  canvas.addEventListener('pointerdown',e=>{press={x:e.clientX,y:e.clientY,map:current?.id};},true);
  canvas.addEventListener('pointerup',e=>{if(e.button!==0||!press||press.map!==current?.id||Math.hypot(e.clientX-press.x,e.clientY-press.y)>5||!el('notes-show').checked||picking||el('note-dialog').open)return;const p=coordinates(e),near=placements(zoom).find(r=>Math.hypot(p[0]-r.position[0],p[1]-r.position[1])*zoom<17);if(near){e.stopImmediatePropagation();drag=null;edit(near.row.id);}},true);
  el('note-pick-cancel').onclick=cancelPick;
  el('notes-add').onclick=()=>{if(!current)return;closeMenu();picking={map:current.id};el('note-pick-text').textContent=t('请点击要记录的地图位置');el('note-pick-banner').hidden=false;canvas.style.cursor='crosshair';draw();};
  el('note-dialog').addEventListener('cancel',e=>{if(saving)e.preventDefault();});
  el('note-dialog').addEventListener('close',()=>draw());
  el('notes-at-player').onclick=()=>{if(result?.id===current?.id&&result.position&&!result.held)begin([...result.position]);else status(t('当前位置尚未确认，请在地图上右键选点。'));};
  el('note-kind').onchange=()=>{kindFields();};
  el('note-repick').onclick=()=>{readDraft();pickEnd();};
  el('note-cancel').onclick=()=>{if(!saving)el('note-dialog').close();};
  el('note-save').onclick=save;
  el('note-delete').onclick=async()=>{if(saving||!draft?.id)return;if(!confirm(t('删除这条本地实测记录和附图？')))return;saving=true;try{await api('delete',{id:draft.id,revision:draft.revision});el('note-dialog').close();status(t('记录已删除'));await refresh();}catch(e){el('note-error').textContent=e.message;}finally{saving=false;}};
  el('note-attach').onclick=()=>{
   try{
    if(!previewFrameAt||(!frame&&(!nativeSession||Date.now()-previewFrameAt>15000)))throw Error('没有近期游戏预览，请先连接采集或导入截图。');
    const copy=document.createElement('canvas'),s=Math.min(1,1280/Math.max(cap.width,cap.height));copy.width=Math.round(cap.width*s);copy.height=Math.round(cap.height*s);copy.getContext('2d').drawImage(cap,0,0,copy.width,copy.height);
    draft.screenshot=copy.toDataURL('image/jpeg',.78);draft.image_time=new Date(previewFrameAt).toISOString();draft.remove_image=false;imagePreview();el('note-error').textContent='';
   }catch(e){el('note-error').textContent=e.message;}
  };
  el('note-remove-image').onclick=()=>{draft.screenshot=null;draft.remove_image=true;draft.image_time=null;imagePreview();};
  el('notes-export').onclick=async()=>{
   const button=el('notes-export');button.disabled=true;
   try{const blob=await api('export'),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download='aniimo-map-feedback-'+new Date().toISOString().slice(0,10)+'.zip';a.click();setTimeout(()=>URL.revokeObjectURL(url),60000);status(t('已导出全部本地记录，可把 ZIP 发给开发者。'));}catch(e){status(e.message);}finally{button.disabled=!records.length;}
  };
  el('notes-show').onchange=()=>draw();el('notes-refresh').onclick=refresh;refresh();
 });
 window.addEventListener('languagechange',render);
 return {paint,syncMap,refresh};
})();
