/* Select combinations explicitly; no global keyboard recording. */
window.OverlayHotkeys=(()=>{
 const actions=['toggle_lock','toggle_hidden','opacity_up','opacity_down'];
 const labels=['鼠标穿透','隐藏 / 显示','增加不透明度','增加透明度'];
 const modifiers=['Alt+Shift','Ctrl+Alt','Ctrl+Shift','Ctrl+Alt+Shift','Ctrl','Alt'];
 const keys=[...'ABCDEFGHIJKLMNOPQRSTUVWXYZ',...'0123456789',...Array.from({length:11},(_,i)=>'F'+(i+1)),'Up','Down','Left','Right','PageUp','PageDown','Home','End','Insert','Delete'];
 const keyLabels={Up:'↑',Down:'↓',Left:'←',Right:'→'};
 const el=id=>document.getElementById(id);let dirty=false,saving=false,current=null,poll=null;
 function fill(bindings){for(const action of actions){const parts=bindings[action].split('+');el('hk-'+action+'-key').value=parts.pop();el('hk-'+action+'-mods').value=parts.join('+');}}
 function sync(state){
  if(!state)return;const first=!current;current=state;
  if(!dirty&&!saving&&(!state.error||first))fill(state.bindings);
  const actual=state.active??state.bindings;
  el('hotkey-summary').textContent=actions.map((a,i)=>t(labels[i])+': '+(actual[a]||t('未启用'))).join(' · ');
  if(!dirty){el('hotkey-status').textContent=state.pending?t('正在应用快捷键…'):state.error?t(state.error):state.active?t('快捷键已生效'):t('设置已保存，开启悬浮窗后生效');}
  el('hotkey-save').disabled=saving||state.pending;el('hotkey-defaults').disabled=saving||state.pending;
  for(const a of actions)for(const suffix of ['mods','key'])el('hk-'+a+'-'+suffix).disabled=saving||state.pending;
  if(state.pending&&!poll)poll=setTimeout(()=>{poll=null;load();},700);
 }
 async function load(){try{const response=await fetch('/api/overlay/hotkeys');if(!response.ok)throw Error();sync(await response.json());}catch{el('hotkey-status').textContent=t('无法读取快捷键设置，请检查本地服务');}}
 async function save(){
  const bindings=Object.fromEntries(actions.map(a=>[a,el('hk-'+a+'-mods').value+'+'+el('hk-'+a+'-key').value]));
  if(new Set(Object.values(bindings)).size!==actions.length){el('hotkey-status').textContent=t('快捷键不能重复，请为每项选择不同组合');return;}
  saving=true;if(current)sync(current);el('hotkey-status').textContent=t('正在应用快捷键…');
  try{
   const response=await fetch('/api/overlay/hotkeys',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({bindings})});
   const state=await response.json();if(!response.ok)throw Error(state.error||'保存失败');
   dirty=false;saving=false;sync(state);
  }catch(error){el('hotkey-status').textContent=t(error.message);}
  finally{saving=false;el('hotkey-save').disabled=!!current?.pending;el('hotkey-defaults').disabled=!!current?.pending;for(const a of actions)for(const suffix of ['mods','key'])el('hk-'+a+'-'+suffix).disabled=!!current?.pending;}
 }
 for(const [i,action] of actions.entries()){
  const row=document.createElement('div');row.className='hotkey-row';
  const label=document.createElement('span');label.id='hk-'+action+'-label';label.textContent=t(labels[i]);row.append(label);
  for(const [suffix,values] of [['mods',modifiers],['key',keys]]){
   const select=document.createElement('select');select.id='hk-'+action+'-'+suffix;select.setAttribute('aria-label',t(labels[i])+' '+t(suffix==='mods'?'组合键':'按键'));
   for(const value of values){const option=document.createElement('option');option.value=value;option.textContent=keyLabels[value]||value;select.append(option);}
   select.onchange=()=>{dirty=true;el('hotkey-status').textContent=t('修改后点击保存快捷键');};row.append(select);
  }
  el('hotkey-fields').append(row);
 }
 el('hotkey-save').onclick=save;
 el('hotkey-defaults').onclick=()=>{if(current){fill(current.defaults);dirty=true;save();}};
 window.addEventListener('languagechange',()=>{actions.forEach((a,i)=>{el('hk-'+a+'-label').textContent=t(labels[i]);for(const suffix of ['mods','key'])el('hk-'+a+'-'+suffix).setAttribute('aria-label',t(labels[i])+' '+t(suffix==='mods'?'组合键':'按键'));});if(current)sync(current);});
 load();return {sync};
})();
