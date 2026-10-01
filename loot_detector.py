"""Heuristic pink/purple loot-beam detection; no world-coordinate inference."""
import cv2
import numpy as np

def detect_rainbow_beams(image):
    if image is None or image.ndim!=3:return []
    h0,w0=image.shape[:2]
    if min(h0,w0)<100:return []
    scale=min(1.,800/w0)
    im=cv2.resize(image,None,fx=scale,fy=scale)
    h,w=im.shape[:2]
    hsv=cv2.cvtColor(im,cv2.COLOR_BGR2HSV)
    # A tall magenta/purple shaft, not an arbitrary purple object or HUD icon.
    mask=cv2.inRange(hsv,(128,65,130),(179,255,255))
    mask[:int(h*.08)]=0;mask[int(h*.86):]=0
    mask[:,:int(w*.16)]=0;mask[:,int(w*.83):]=0
    linked=cv2.morphologyEx(mask,cv2.MORPH_CLOSE,np.ones((max(3,round(h*.018)),3),np.uint8))
    _,_,stats,_=cv2.connectedComponentsWithStats(linked)
    beams=[]
    for x,y,bw,bh,area in stats[1:]:
        if bh<h*.18 or bw>w*.065 or bw<2 or bh/max(1,bw)<4 or area<h*w*.00025:continue
        region=mask[y:y+bh,x:x+bw]>0
        upper=region[:max(1,int(bh*.65))]
        persistence=float(upper.any(axis=1).mean())
        # The thin upper shaft should stay on one vertical axis.
        column_support=float(upper.sum(axis=0).max()/max(1,upper.shape[0]))
        if persistence<.68 or column_support<.48:continue
        if y+bh<h*.4 or y+bh>h*.85:continue
        # Screen x is only for consecutive-frame association, not map projection.
        beams.append({'box':[round(x/scale),round(y/scale),round(bw/scale),round(bh/scale)],'screen_x':float((x+bw/2)/w),'strength':round(min(1.,(persistence+column_support)/2),3),'kind':'rainbow_beam_candidate'})
    return sorted(beams,key=lambda b:b['strength'],reverse=True)[:4]
