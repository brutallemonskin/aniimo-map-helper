/* Pure state helpers shared by the UI and deterministic replay tests. */
const NavigatorTools=(()=>{
 class FrameClock {
  constructor(){this.reset();}
  reset(){this.token=null;this.at=null;}
  observe(token,now,interval){
   // Use media counters, never image equality: standing still is valid video.
   if(token==null||token!==this.token){this.token=token;this.at=now;return 'fresh';}
   return now-this.at>=Math.max(5000,interval*3)?'stalled':'waiting';
  }
 }
 const captureFps=interval=>Math.max(1,Math.min(8,2000/Math.max(250,interval)));
 class AdaptiveCadence {
  constructor(){this.reset();}
  reset(){this.cost=0;this.anchor=null;this.movedAt=0;this.interval=500;}
  observe(elapsed,position,map,now){
   if(Number.isFinite(elapsed)&&elapsed>=0)this.cost=this.cost?this.cost*.75+elapsed*.25:elapsed;
   if(position){
    if(!this.anchor||this.anchor.map!==map||Math.hypot(position[0]-this.anchor.p[0],position[1]-this.anchor.p[1])>=5){this.anchor={map,p:[...position]};this.movedAt=now;}
   }else this.anchor=null;
   const idle=position&&now-this.movedAt>=4000;
   const desired=Math.max(this.cost/0.35,position?(idle?1000:250):1500);
   this.interval=[250,500,1000,2000,3000].find(v=>v>=desired)||3000;
   return this.interval;
  }
 }
 const key=p=>JSON.stringify([p.category,p.name,Math.round(p.x*10),Math.round(p.y*10)]);
 class RunJournal {
  constructor(){this.reset();}
  reset(){this.maps=new Map();this.last=null;this.revision=0;this.pickedRevision=0;}
  map(id){if(!this.maps.has(id))this.maps.set(id,{trail:[],picked:new Map()});return this.maps.get(id);}
  pause(){this.last=null;}
  record(id,p,now){
   if(!id||!Array.isArray(p)||p.length!==2||!p.every(Number.isFinite))return;
   const data=this.map(id),prev=this.last,dist=prev?Math.hypot(p[0]-prev.p[0],p[1]-prev.p[1]):Infinity;
   if(prev&&prev.id===id&&dist<12&&now-prev.at<5000)return;
   if(!prev||prev.id!==id||now-prev.at>5000||dist>100){if(data.trail.length&&data.trail.at(-1)!==null)data.trail.push(null);}
   data.trail.push([...p]);if(data.trail.length>600)data.trail.splice(0,data.trail.length-600);
   this.last={id,p:[...p],at:now};this.revision++;
  }
  pick(id,p){const m=this.map(id);m.picked.set(key(p),{...p});this.pickedRevision++;}
  undo(id){const m=this.map(id),k=[...m.picked.keys()].at(-1);if(k!==undefined){m.picked.delete(k);this.pickedRevision++;}}
  picked(id,p){return this.map(id).picked.has(key(p));}
 }
 class RouteFollower {
  constructor(){this.reset();}
  reset(){this.path=[];this.lengths=[];this.progress=0;this.last=null;this.offSince=null;this.offFrames=0;this.lastAttempt=-Infinity;this.attemptPosition=null;}
  set(path,origin,now){
   this.reset();this.path=path.map(p=>[...p]);this.lengths=[0];
   for(let i=1;i<path.length;i++)this.lengths.push(this.lengths[i-1]+Math.hypot(path[i][0]-path[i-1][0],path[i][1]-path[i-1][1]));
   this.last={p:[...origin],at:now};this.attempt(origin,now);
  }
  pause(){this.last=null;this.offSince=null;this.offFrames=0;}
  attempt(p,now){this.lastAttempt=now;this.attemptPosition=[...p];this.offSince=null;this.offFrames=0;}
  pointAt(distance){
   for(let i=1;i<this.path.length;i++){
    const span=this.lengths[i]-this.lengths[i-1];
    if(span>0&&distance<=this.lengths[i]){const t=Math.max(0,(distance-this.lengths[i-1])/span),a=this.path[i-1],b=this.path[i];return [a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t];}
   }
   return this.path.at(-1);
  }
  nearest(p,limit){
   let best={distance:Infinity,along:this.progress};
   for(let i=1;i<this.path.length;i++){
    const lo=Math.max(this.progress,this.lengths[i-1]),hi=Math.min(limit,this.lengths[i]);
    if(hi<lo||this.lengths[i]===this.lengths[i-1])continue;
    const a=this.path[i-1],b=this.path[i],dx=b[0]-a[0],dy=b[1]-a[1],span=this.lengths[i]-this.lengths[i-1];
    const along=Math.max(lo,Math.min(hi,this.lengths[i-1]+((p[0]-a[0])*dx+(p[1]-a[1])*dy)/span));
    const t=(along-this.lengths[i-1])/span,distance=Math.hypot(p[0]-a[0]-dx*t,p[1]-a[1]-dy*t);
    // At overlapping out-and-back segments, keep the earliest traversal.
    if(distance<best.distance-1e-6)best={distance,along};
   }
   if(!Number.isFinite(best.distance)&&this.path.length)best.distance=Math.hypot(p[0]-this.path.at(-1)[0],p[1]-this.path.at(-1)[1]);
   return best;
  }
  observe(p,now){
   if(!this.path.length||!p?.every(Number.isFinite))return;
   const previous=this.last,travel=previous?Math.hypot(p[0]-previous.p[0],p[1]-previous.p[1]):Infinity;
   const continuous=previous&&now>=previous.at&&now-previous.at<=6000&&travel<=100;
   const near=this.nearest(p,this.progress+Math.min(160,continuous?travel*1.6+20:160));
   if(continuous&&near.distance<=18)this.progress=Math.max(this.progress,near.along);
   // A gap/jump cannot advance the route or count as a confirmed deviation.
   if(continuous&&near.distance>48){if(this.offSince===null)this.offSince=now;this.offFrames++;}
   else{this.offSince=null;this.offFrames=0;}
   this.last={p:[...p],at:now};
  }
  shouldReplan(p,now){return this.offFrames>=3&&now-this.offSince>=1500&&now-this.lastAttempt>=10000&&
   (!this.attemptPosition||Math.hypot(p[0]-this.attemptPosition[0],p[1]-this.attemptPosition[1])>=24);}
  remaining(){
   if(!this.path.length||this.progress>=this.lengths.at(-1)-1)return [];
   return [this.pointAt(this.progress),...this.path.filter((p,i)=>this.lengths[i]>this.progress+1e-6)];
  }
 }
 return {AdaptiveCadence,RunJournal,RouteFollower,FrameClock,captureFps,pointKey:key};
})();
