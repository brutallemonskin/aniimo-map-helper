/* Route preferences are independent of marker visibility and run completion. */
const RouteGoals=(()=>{
 const presets={egg:['egg-nests'],gold:['chests-legendary'],both:['egg-nests','chests-legendary']};
 const categories=['egg-nests','chests-legendary','merchants','side-entrance'];
 let mode='egg',custom={};
 try{const s=JSON.parse(localStorage.getItem('aniimo-route-goals')||'{}');if([...Object.keys(presets),'custom'].includes(s.mode))mode=s.mode;if(s.custom&&typeof s.custom==='object'&&!Array.isArray(s.custom))custom=s.custom;}catch{}
 const el=id=>document.getElementById(id),key=p=>NavigatorTools.pointKey(p);
 function available(map){return (map.displayPoints||map.points).filter(p=>categories.includes(p.category));}
 function targets(map){return available(map).filter(p=>mode==='custom'?(Array.isArray(custom[map.id])&&custom[map.id].includes(key(p))):presets[mode].includes(p.category));}
 function persist(){try{localStorage.setItem('aniimo-route-goals',JSON.stringify({mode,custom}));}catch{}}
 function changed(rebuild=true){persist();clearRoute();if(rebuild)render();draw();if(navEnabled)updateRoute(true);publishOverlay(true);}
 function render(){
  el('route-goal').value=mode;el('route-custom').hidden=mode!=='custom';el('route-custom-list').replaceChildren();
  if(!current||mode!=='custom')return;
  const selected=new Set(Array.isArray(custom[current.id])?custom[current.id]:[]);
  for(const [i,p] of available(current).entries()){
   const row=document.createElement('label'),check=document.createElement('input'),locate=document.createElement('button'),text=document.createElement('span');
   check.type='checkbox';check.checked=selected.has(key(p));check.onchange=()=>{const keys=new Set(custom[current.id]||[]);check.checked?keys.add(key(p)):keys.delete(key(p));custom[current.id]=[...keys];changed(false);};
   text.textContent=`${i+1}. ${pointName(p)} (${Math.round(p.x)}, ${Math.round(p.y)})`;
   locate.type='button';locate.textContent=t('查看');locate.onclick=e=>{e.preventDefault();choosePoint(p);zoom=Math.max(zoom,.8);ox=canvas.clientWidth/2-p.x*zoom;oy=canvas.clientHeight/2-p.y*zoom;draw();};
   row.append(check,text,locate);el('route-custom-list').append(row);
  }
 }
 document.addEventListener('DOMContentLoaded',()=>{
  el('route-goal').value=mode;
  el('route-goal').onchange=()=>{const next=el('route-goal').value;if(next==='custom'&&current&&!Array.isArray(custom[current.id]))custom[current.id]=targets(current).map(key);mode=next;changed();};
  el('route-select-all').onclick=()=>{if(current){custom[current.id]=available(current).map(key);changed();}};
  el('route-select-none').onclick=()=>{if(current){custom[current.id]=[];changed();}};
 });
 window.addEventListener('languagechange',render);
 return {targets,render};
})();
