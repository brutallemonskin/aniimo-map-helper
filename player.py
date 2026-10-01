"""Conservative detection of the bright yellow player arrow in map screenshots."""
from image_io import read_image
import cv2
import numpy as np
from pathlib import Path

try:
    _egg=read_image(str(Path(__file__).resolve().parent/'data/player-egg-template.png'),cv2.IMREAD_GRAYSCALE)
except ValueError:
    _egg=None  # The index builder reports the missing asset through /api/status.

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
        for x0,y0,x1,y1 in regions:
            if x1-x0<width or y1-y0<height:continue
            scores=cv2.matchTemplate(gray[y0:y1,x0:x1],template,cv2.TM_CCOEFF_NORMED,mask=mask)
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

def detect_player(image):
    egg=detect_egg(image)
    if egg:return egg
    h,w=image.shape[:2]
    hsv=cv2.cvtColor(image,cv2.COLOR_BGR2HSV)
    mask=cv2.inRange(hsv,(22,90,180),(40,255,255))
    n,labels,stats,centers=cv2.connectedComponentsWithStats(mask)
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
