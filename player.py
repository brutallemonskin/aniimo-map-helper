"""Conservative detection of the bright yellow player arrow in map screenshots."""
from image_io import read_image, normalize_map_lighting
import cv2
import numpy as np
from pathlib import Path
from masked_correlation import MaskedCorrelation
from recognition_timing import stage

try:
    _egg=read_image(str(Path(__file__).resolve().parent/'data/player-egg-template.png'),cv2.IMREAD_GRAYSCALE)
except ValueError:
    _egg=None  # The index builder reports the missing asset through /api/status.

_number_labels={}
for _slot in (1,2,3):
    try:
        _number_labels[_slot]=read_image(Path(__file__).resolve().parent/f'data/player-number-{_slot}-template.png',cv2.IMREAD_GRAYSCALE)
    except ValueError:
        pass


def _glyph_score(region,template):
    normalized=cv2.resize(region,(template.shape[1],template.shape[0]),interpolation=cv2.INTER_AREA)
    score=float(cv2.matchTemplate(normalized,template,cv2.TM_CCOEFF_NORMED)[0,0])
    for interpolation in (cv2.INTER_NEAREST,cv2.INTER_AREA):
        resized=cv2.resize(template,(region.shape[1],region.shape[0]),interpolation=interpolation)
        for threshold in (64,127):
            binary=np.uint8(resized>threshold)*255
            score=max(score,float(cv2.matchTemplate(region,binary,cv2.TM_CCOEFF_NORMED)[0,0]))
    return score


def find_team_labels(hsv):
    """识别编号而非身份：颜色只用于提取字形，自己的编号由本局设置指定。"""
    h,w=hsv.shape[:2];found=[]
    for low,high,saturation,brightness in ((22,40,90,180),(41,85,65,150),(86,135,65,150)):
        mask=cv2.inRange(hsv,(low,saturation,brightness),(high,255,255))
        _,_,stats,_=cv2.connectedComponentsWithStats(mask)
        glyphs=[]
        for s in stats[1:]:
            x,y,bw,bh,area=map(int,s)
            if max(8,h*.008)<=bh<=max(60,h*.05) and .18<=bw/bh<=1.1 and .35<=area/(bw*bh)<=.95:
                glyphs.append((x,y,bw,bh))
        glyphs.sort()
        for index,(x,y,bw,bh) in enumerate(glyphs):
            for px,py,pw,ph in glyphs[index+1:]:
                gap=px-(x+bw)
                if gap>bh*.55:break
                if not (gap>=0 and .8<=ph/bh<=1.25 and abs(py-y)<=bh*.2 and .45<=pw/ph<=1.1):continue
                y0=min(y,py);y1=max(y+bh,py+ph);x1=px+pw
                region=mask[y0:y1,x:x1]
                fits=sorted(((_glyph_score(region,template),slot) for slot,template in _number_labels.items()
                             if (slot==1 and bw/bh<=.6) or (slot!=1 and bw/bh>=.48)),reverse=True)
                if not fits or fits[0][0]<.82 or (len(fits)>1 and fits[0][0]-fits[1][0]<.05):continue
                point=[(x+x1)/2,(y0+y1)/2];slot=fits[0][1]
                found.append({'point':point,'normalized':[point[0]/w,point[1]/h],
                              'box':[x,y0,x1-x,y1-y0],'kind':'team-label','label':f'{slot}P','slot':slot})
    return found

def detect_egg(image):
    if _egg is None:return None
    h,w=image.shape[:2];factor=min(1.,1600/w)
    small=cv2.resize(image,None,fx=factor,fy=factor)
    gray=cv2.cvtColor(small,cv2.COLOR_BGR2GRAY)
    # The player egg is blue/white. Search around blue components rather than
    # correlating fourteen masked templates against every screen pixel.
    # Keep the original correlation and ambiguity thresholds inside each ROI.
    hsv=cv2.cvtColor(small,cv2.COLOR_BGR2HSV)
    blue=cv2.inRange(hsv,(85,45,max(30,int(hsv[:,:,2].max()*.55))),(135,255,255))
    _,_,stats,_=cv2.connectedComponentsWithStats(blue)
    regions=[]
    if len(stats)>256:
        # Busy scenes use the original full-frame search; bound ROI-merging cost.
        regions=[[0,0,gray.shape[1],gray.shape[0]]]
        stats=stats[:1]
    for x,y,bw,bh,area in stats[1:]:
        if area<3:continue
        box=[max(0,int(x)-60),max(0,int(y)-60),min(gray.shape[1],int(x+bw)+60),min(gray.shape[0],int(y+bh)+60)]
        # Merge overlapping components so one icon is not evaluated repeatedly.
        changed=True
        while changed:
            changed=False
            for i,r in enumerate(regions):
                if box[0]<=r[2] and r[0]<=box[2] and box[1]<=r[3] and r[1]<=box[3]:
                    box=[min(box[0],r[0]),min(box[1],r[1]),max(box[2],r[2]),max(box[3],r[3])]
                    regions.pop(i);changed=True;break
        regions.append(box)
    if not regions:return None
    picks=[]
    for height in range(16,58,3):
        width=round(height*_egg.shape[1]/_egg.shape[0])
        template=cv2.resize(_egg,(width,height))
        mask=np.zeros((height,width),np.uint8)
        cv2.ellipse(mask,(round(width*.43),round(height*.48)),(max(2,round(width*.34)),max(2,round(height*.42))),0,0,360,255,-1)
        correlation=MaskedCorrelation(template,mask)
        for x0,y0,x1,y1 in regions:
            if x1-x0<width or y1-y0<height:continue
            scores=correlation.match(gray[y0:y1,x0:x1])
            scores=np.nan_to_num(scores,nan=-1,posinf=-1,neginf=-1)
            for _ in range(2):
                _,score,_,(lx,ly)=cv2.minMaxLoc(scores)
                if score<.82:break
                x,y=lx+x0,ly+y0
                point=np.array([x+width*.43,y+height*.48])/factor
                picks.append((score,point,[int(x/factor),int(y/factor),int(width/factor),int(height/factor)]))
                scores[max(0,ly-height):ly+height,max(0,lx-width):lx+width]=-1
    if not picks:return None
    picks.sort(key=lambda p:p[0],reverse=True)
    score,point,box=picks[0]
    if score<.86 or any(score-other[0]<.06 for other in picks[1:] if np.linalg.norm(point-other[1])>max(box[2:])):return None
    return {'point':point.tolist(),'normalized':(point/[w,h]).tolist(),'box':box,'kind':'egg'}

@stage('人物图标定位')
def detect_player(image,player_slot=None):
    image=normalize_map_lighting(image)
    h,w=image.shape[:2]
    hsv=cv2.cvtColor(image,cv2.COLOR_BGR2HSV)
    mask=cv2.inRange(hsv,(22,90,180),(40,255,255))
    n,labels,stats,centers=cv2.connectedComponentsWithStats(mask)
    team=find_team_labels(hsv)
    if player_slot is not None:
        selected=[point for point in team if point['slot']==player_slot]
        return selected[0] if len(selected)==1 else None
    # 看到编号但尚未选择自己的编号时，不能把任意队员或蛋巢当作自己。
    if team:return None
    egg=detect_egg(image)
    if egg:return egg
    candidates=[]
    for label,(s,c) in enumerate(zip(stats[1:],centers[1:]),1):
        x,y,bw,bh,area=s
        if not max(30,w*h*.00012)<=area<=w*h*.008:continue
        if not .55<bw/bh<1.8 or bw>w*.10 or bh>h*.14:continue
        if x<2 or y<2 or x+bw>w-2 or y+bh>h-2:continue
        if not .20<area/(bw*bh)<.9:continue
        candidates.append({'point':c.tolist(),'normalized':[float(c[0]/w),float(c[1]/h)],'box':[int(x),int(y),int(bw),int(bh)]})
    # Multiple yellow arrow-like objects are ambiguous; never choose one arbitrarily.
    return candidates[0] if len(candidates)==1 else None
