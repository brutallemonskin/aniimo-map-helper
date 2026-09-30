"""North-up minimap registration against an already identified dungeon.

Coordinates are image pixels. No keyboard input or game process access is used.
"""
import json
from pathlib import Path
import cv2
import numpy as np


class MinimapTracker:
    def __init__(self, root):
        self.root=Path(root)
        self.refs={}

    @staticmethod
    def extract(image):
        h,w=image.shape[:2]
        if w/h<1.45 or w/h>2.1:return None
        cx,cy,r=round(w*.0945),round(h*.132),round(h*.089)
        crop=image[cy-r:cy+r,cx-r:cx+r]
        if crop.size==0:return None
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

    def match(self, sample, map_id=None, previous=None, previous_scale=None):
        missing={'status':'unknown','method':'minimap','candidates':[], 'position_source':None}
        if not map_id:
            return dict(missing,reason='已看到小地图，请先打开大地图确认本局地图。')
        gray,mask,point,dungeon_color=sample
        # Transparent HUD backgrounds inherit colors from the 3D scene.
        # Reject by terrain fit below, not by how gray the whole circle is.
        if cv2.countNonZero(mask)<3500:
            return dict(missing,reason='小地图遮挡较多，暂时无法确认位置。')
        if map_id not in self.refs:
            path=self.root/'data'/f'{map_id}.json'
            if not path.is_file():return dict(missing,reason='请先确认地图。')
            d=json.loads(path.read_text(encoding='utf8'))
            im=cv2.imread(str(self.root/d['image'].lstrip('/')),cv2.IMREAD_GRAYSCALE)
            self.refs[map_id]=(d,im)
        d,ref=self.refs[map_id]
        if previous is None:return dict(missing,reason='请打开大地图校准角色起点。')
        px,py=previous
        # A local search avoids jumping between repeated rooms across the map.
        radius=230
        x0,y0=max(0,int(px-radius)),max(0,int(py-radius))
        x1,y1=min(ref.shape[1],int(px+radius)),min(ref.shape[0],int(py+radius))
        region=ref[y0:y1,x0:x1]
        if min(region.shape[:2],default=0)<80:return dict(missing,reason='起点超出地图，请重新打开大地图校准。')
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
        if best is None:return dict(missing,reason='小地图比例不匹配，请打开大地图校准。')
        value,pos,scale,loc=best
        alternative=max([v for v,p in peaks if np.linalg.norm(p-pos)>55],default=-1)
        if value<.72 or value-alternative<.06 or np.linalg.norm(pos-previous)>170:
            return dict(missing,reason='小地图地形暂不明确，位置已隐藏；可打开大地图重新校准。', fit=round(value,3))
        origin=np.array(loc)/scale+[x0,y0]
        polygon=[(origin+np.array(p)/scale).tolist() for p in ((0,0),(200,0),(200,200),(0,200))]
        row={'id':map_id,'name':d['name'],'score':round(value*100,2),'inliers':0,'method':'minimap','position_source':'auto','position':pos.tolist(),'center':pos.tolist(),'polygon':polygon,'minimap_scale':scale}
        return {'status':'matched','method':'minimap','position_source':'auto','candidates':[row], 'reason':'正在用小地图地形更新位置；打开大地图可重新校准。'}
