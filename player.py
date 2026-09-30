"""Conservative detection of the bright yellow player arrow in map screenshots."""
import cv2
import numpy as np
from pathlib import Path

_egg=cv2.imread(str(Path(__file__).resolve().parent/'data/player-egg-template.png'),cv2.IMREAD_GRAYSCALE)

def detect_egg(image):
    if _egg is None:return None
    h,w=image.shape[:2];factor=min(1.,1600/w)
    small=cv2.resize(image,None,fx=factor,fy=factor)
    gray=cv2.cvtColor(small,cv2.COLOR_BGR2GRAY)
    picks=[]
    for height in range(16,58,3):
        width=round(height*_egg.shape[1]/_egg.shape[0])
        template=cv2.resize(_egg,(width,height))
        mask=np.zeros((height,width),np.uint8)
        cv2.ellipse(mask,(round(width*.43),round(height*.48)),(max(2,round(width*.34)),max(2,round(height*.42))),0,0,360,255,-1)
        scores=cv2.matchTemplate(gray,template,cv2.TM_CCOEFF_NORMED,mask=mask)
        scores=np.nan_to_num(scores,nan=-1,posinf=-1,neginf=-1)
        for _ in range(2):
            _,score,_,(x,y)=cv2.minMaxLoc(scores)
            if score<.82:break
            point=np.array([x+width*.43,y+height*.48])/factor
            picks.append((score,point,[int(x/factor),int(y/factor),int(width/factor),int(height/factor)]))
            scores[max(0,y-height):y+height,max(0,x-width):x+width]=-1
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
