"""North-up minimap registration against an already identified dungeon.

Coordinates are image pixels. No keyboard input or game process access is used.
"""
import json, copy, time
from pathlib import Path
from image_io import read_image
import cv2
import numpy as np
from relocalizer import Relocalizer, motion_agrees


class MinimapTracker:
    def __init__(self, root):
        self.root=Path(root)
        self.refs={}
        self.last_matches={}
        self.relocalizer=Relocalizer()
        self.recovery={}

    @staticmethod
    def extract(image):
        h,w=image.shape[:2]
        if w/h<1.45 or w/h>2.1:return None
        cx,cy,r=round(w*.0945),round(h*.132),round(h*.089)
        crop=image[cy-r:cy+r,cx-r:cx+r]
        if crop.size==0:return None
        return MinimapTracker.extract_crop(crop)

    @staticmethod
    def extract_crop(crop):
        """Validate the HUD on every crop; a missing HUD requests a full frame."""
        crop=cv2.resize(crop,(200,200))
        raw_gray=cv2.cvtColor(crop,cv2.COLOR_BGR2GRAY)
        hsv=cv2.cvtColor(crop,cv2.COLOR_BGR2HSV)
        yellow=cv2.inRange(hsv,(22,90,180),(40,255,255))
        n,labels,stats,cent=cv2.connectedComponentsWithStats(yellow)
        arrows=[(s,c) for s,c in zip(stats[1:],cent[1:]) if 25<s[4]<900 and .45<s[2]/s[3]<2.1 and np.linalg.norm(c-[100,100])<25]
        circles=cv2.HoughCircles(raw_gray,cv2.HOUGH_GRADIENT,1,100,param1=70,param2=25,minRadius=90,maxRadius=105)
        rings=[] if circles is None else [c for c in circles[0] if np.linalg.norm(c[:2]-[100,100])<10]
        if len(arrows)==1:
            s,point=arrows[0]
        elif len(rings)==1:
            # The HUD remains centered on the player when its arrow changes
            # into an egg or another form. Require its circular rim first.
            point=rings[0][:2].astype(float)
            s=None
        else:return None
        yy,xx=np.mgrid[:200,:200]
        mask=np.uint8((xx-100)**2+(yy-100)**2<88**2)*255
        # Exclude the heading arrow, gate icons and colored overlays.
        icons=np.uint8(hsv[:,:,1]>65)*255
        icons=cv2.dilate(icons,np.ones((9,9),np.uint8))
        mask[icons>0]=0
        mask[(xx-point[0])**2+(yy-point[1])**2<28**2]=0
        if s is not None:
            x,y,bw,bh,_=s;mask[max(0,y-6):y+bh+6,max(0,x-6):x+bw+6]=0
        gray=cv2.cvtColor(crop,cv2.COLOR_BGR2GRAY)
        gray=cv2.GaussianBlur(gray,(5,5),0)
        # This prototype targets the gray dungeon map, not the colored island.
        interior=(xx-100)**2+(yy-100)**2<80**2
        dungeon_color=float(np.mean(hsv[:,:,1][interior]<55))>.72
        return gray,mask,point,dungeon_color

    def match(self, sample, map_id=None, previous=None, previous_scale=None, observation=None, search_elapsed=0):
        missing={'status':'unknown','method':'minimap','candidates':[], 'position_source':None}
        if not map_id:
            return dict(missing,reason='已看到小地图，请先打开大地图确认本局地图。')
        gray,mask,point,dungeon_color=sample
        cached=self.last_matches.get(map_id)
        if cached is not None and previous is not None:
            old_gray,old_mask,old_point,old_previous,old_scale,answer=cached
            row=answer['candidates'][0]
            same_start=np.allclose(previous,old_previous,rtol=0,atol=.001) and previous_scale==old_scale
            continuation=np.allclose(previous,row['position'],rtol=0,atol=.001) and previous_scale==row['minimap_scale']
            if (same_start or continuation) and np.array_equal(gray,old_gray) and np.array_equal(mask,old_mask) and np.array_equal(point,old_point):
                if observation:self.recovery.pop((observation['session'],map_id),None)
                return copy.deepcopy(answer)
        # Transparent HUD backgrounds inherit colors from the 3D scene.
        # Reject by terrain fit below, not by how gray the whole circle is.
        if cv2.countNonZero(mask)<3500:
            return dict(missing,reason='小地图遮挡较多，暂时无法确认位置。')
        if map_id not in self.refs:
            path=self.root/'data'/f'{map_id}.json'
            if not path.is_file():return dict(missing,reason='请先确认地图。')
            d=json.loads(path.read_text(encoding='utf8'))
            im=read_image(str(self.root/d['image'].lstrip('/')),cv2.IMREAD_GRAYSCALE)
            self.refs[map_id]=(d,im)
        d,ref=self.refs[map_id]
        if previous is None:return dict(missing,reason='请打开大地图校准角色起点。')
        px,py=previous
        # A local search avoids jumping between repeated rooms across the map.
        # Only recovery verification expands its search with elapsed time;
        # accepting the result still requires independent motion evidence.
        step_limit=min(320,170+max(0,search_elapsed-500)*.04)
        radius=max(230,step_limit+150)
        if not search_elapsed:radius=230
        x0,y0=max(0,int(px-radius)),max(0,int(py-radius))
        x1,y1=min(ref.shape[1],int(px+radius)),min(ref.shape[0],int(py+radius))
        region=ref[y0:y1,x0:x1]
        if min(region.shape[:2],default=0)<80:
            return self.recover(sample,map_id,previous,previous_scale,observation,dict(missing,reason='起点超出地图，正在尝试重新定位。'))
        scales=np.linspace(.65,1.55,25) if previous_scale is None else np.linspace(previous_scale*.94,previous_scale*1.06,9)
        best=None;peaks=[]
        for scale in scales:
            target=cv2.resize(region,None,fx=float(scale),fy=float(scale))
            if min(target.shape)<200:continue
            target=cv2.GaussianBlur(target,(5,5),0)
            score=cv2.matchTemplate(target,gray,cv2.TM_CCOEFF_NORMED,mask=mask)
            score=np.nan_to_num(score,nan=-1,posinf=-1,neginf=-1)
            _,value,_,loc=cv2.minMaxLoc(score)
            pos=(np.array(loc)+point)/scale+[x0,y0]
            peaks.append((value,pos))
            if best is None or value>best[0]:best=(value,pos,float(scale),loc)
            # Record a spatially different alternative at this scale.
            lx,ly=loc;score[max(0,ly-35):ly+36,max(0,lx-35):lx+36]=-1
            _,v,_,other=cv2.minMaxLoc(score)
            peaks.append((v,(np.array(other)+point)/scale+[x0,y0]))
        if best is None:return self.recover(sample,map_id,previous,previous_scale,observation,dict(missing,reason='小地图比例不匹配，正在尝试重新定位。'))
        value,pos,scale,loc=best
        alternative=max([v for v,p in peaks if np.linalg.norm(p-pos)>55],default=-1)
        if value<.72 or value-alternative<.06 or np.linalg.norm(pos-previous)>step_limit:
            return self.recover(sample,map_id,previous,previous_scale,observation,dict(missing,reason='小地图地形暂不明确，保留上次位置；正在尝试重新定位。', fit=round(value,3)))
        origin=np.array(loc)/scale+[x0,y0]
        polygon=[(origin+np.array(p)/scale).tolist() for p in ((0,0),(200,0),(200,200),(0,200))]
        row={'id':map_id,'name':d['name'],'score':round(value*100,2),'inliers':0,'method':'minimap','position_source':'auto','position':pos.tolist(),'center':pos.tolist(),'polygon':polygon,'minimap_scale':scale}
        answer={'status':'matched','method':'minimap','position_source':'auto','candidates':[row], 'reason':'正在用小地图地形更新位置；打开大地图可重新校准。'}
        self.last_matches[map_id]=(gray.copy(),mask.copy(),point.copy(),list(previous),previous_scale,copy.deepcopy(answer))
        if observation:self.recovery.pop((observation['session'],map_id),None)
        return answer

    def recover(self,sample,map_id,previous,scale,observation,missing):
        if observation is None:return missing
        missing=dict(missing,recovering=True)
        now=time.monotonic();key=(observation['session'],map_id)
        state=self.recovery.setdefault(key,{'failures':0,'next':0,'pending':None})
        if len(self.recovery)>8:self.recovery.pop(next(iter(self.recovery)))
        state['failures']+=1
        origin=(tuple(previous),scale)
        pending=state['pending']
        if pending and pending['origin']!=origin:state['pending']=None;pending=None
        if pending:
            age=observation['captured_at']-pending['at']
            if 100<=age<=10000 and observation['sequence']>pending['sequence']:
                checked=self.match(sample,map_id,pending['position'],pending['scale'],search_elapsed=age)
                row=checked.get('candidates',[None])[0] if checked.get('candidates') else None
                delta=np.array(row['position'])-pending['position'] if row else None
                distance=np.linalg.norm(delta) if row else float('inf')
                motion_limit=min(320,45+max(0,age-250)*.07)
                coherent=distance<45 or (distance<motion_limit and motion_agrees(pending['sample'],sample,delta,(pending['scale']+row['minimap_scale'])/2))
                if checked['status']=='matched' and coherent:
                    self.recovery.pop(key,None)
                    checked.update(relocalized=True,reason='已连续确认新位置，小地图追踪已恢复。')
                    return checked
                state['pending']=None
            elif age>10000:state['pending']=None
            else:return dict(missing,reason='已找到可能位置，等待下一帧确认。')
        if state['failures']<2 or now<state['next']:return missing
        state['next']=now+2
        proposal=self.relocalizer.propose(sample,map_id,self.refs[map_id][1],scale if state['failures']<4 else None)
        if proposal is None:return missing
        position,new_scale=proposal
        verified=self.match(sample,map_id,position,new_scale)
        if verified['status']!='matched':return missing
        row=verified['candidates'][0]
        state['pending']={'position':row['position'],'scale':row['minimap_scale'],'origin':origin,
                          'at':observation['captured_at'],'sequence':observation['sequence'],
                          'sample':tuple(x.copy() if isinstance(x,np.ndarray) else x for x in sample)}
        return dict(missing,reason='已找到可能位置，等待下一帧确认。')
