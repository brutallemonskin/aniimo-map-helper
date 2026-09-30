"""Door-constrained registration, verified against visible floor edges only."""
import json, math
from pathlib import Path
import cv2
import numpy as np

class DoorMatcher:
    def __init__(self, root):
        self.refs=[]
        for p in (root/'data').glob('sanctum-*.json'):
            d=json.loads(p.read_text(encoding='utf8'))
            doors=[next((q for q in d['points'] if q['category']==c),None) for c in ('entrance','side-entrance')]
            if not all(doors):continue
            im=cv2.imread(str(root/d['image'].lstrip('/')))
            gray=cv2.cvtColor(im,cv2.COLOR_BGR2GRAY)
            self.refs.append((d,np.float32([[p['x'],p['y']] for p in doors]),gray))

    @staticmethod
    def blobs(mask, min_area):
        n,l,stats,cent=cv2.connectedComponentsWithStats(mask)
        return [(s,c) for s,c in zip(stats[1:],cent[1:]) if s[4]>=min_area and .4<s[2]/s[3]<2.2]

    def match(self, image, anchor=None):
        h0,w0=image.shape[:2]; scale=min(1.,1600/w0)
        im=cv2.resize(image,None,fx=scale,fy=scale);h,w=im.shape[:2]
        hsv=cv2.cvtColor(im,cv2.COLOR_BGR2HSV)
        yellow=cv2.inRange(hsv,(22,90,180),(40,255,255))
        blue=cv2.inRange(hsv,(95,90,180),(125,255,255))
        k=max(3,round(w/180)); k+=1-k%2
        blue=cv2.morphologyEx(blue,cv2.MORPH_CLOSE,np.ones((k,k),np.uint8))
        ys=self.blobs(yellow, max(18,w*h*.00012)); bs=self.blobs(blue,max(16,w*h*.00008))
        # Header/logo is not a gate. Only suppress the top-left UI corner.
        bs=[(s,c) for s,c in bs if not (c[0]<w*.2 and c[1]<h*.2)]
        ys=[(s,c) for s,c in ys if s[2]<w*.12 and s[3]<h*.15]
        bs=[(s,c) for s,c in bs if s[2]<w*.1 and s[3]<h*.12]
        orange=cv2.inRange(hsv,(5,90,180),(21,255,255))
        orange=cv2.morphologyEx(orange,cv2.MORPH_CLOSE,np.ones((3,3),np.uint8))
        os=self.blobs(orange,max(10,w*h*.00004))
        os=[(s,c) for s,c in os if s[2]<w*.08 and s[3]<h*.12 and not(c[0]<w*.2 and c[1]<h*.2)]
        gate_visible=len(os)==1
        if len(bs)!=1 or (not gate_visible and len(ys)!=1):return None
        sy,cy=os[0] if gate_visible else ys[0]
        sb,cb=bs[0]
        if np.linalg.norm(cy-cb)<w*.08:return None
        floor=cv2.inRange(hsv,(0,0,105),(179,65,255))
        floor[:round(h*.12),:round(w*.25)]=0
        n,l,stats,_=cv2.connectedComponentsWithStats(floor)
        valid=[i for i,s in enumerate(stats) if i and s[4]>max(80,w*h*.0004)]
        floor=np.uint8(np.isin(l,valid))*255
        if cv2.countNonZero(floor)<150:return None
        visible=cv2.dilate(floor,np.ones((13,13),np.uint8))
        # Remove the overlapping player/gate icon and blue gate from terrain evidence.
        for s in [sy,sb]+[s for s,c in ys]:
            x,y,bw,bh,_=s;pad=10
            visible[max(0,y-pad):y+bh+pad,max(0,x-pad):x+bw+pad]=0
        gray=cv2.cvtColor(im,cv2.COLOR_BGR2GRAY)
        edges=cv2.Canny(gray,35,85)
        qedge=cv2.bitwise_and(edges,visible)
        yy,xx=np.where(visible>0)
        if len(xx)<100:return None
        x0,y0,x1,y1=max(0,xx.min()-3),max(0,yy.min()-3),min(w,xx.max()+4),min(h,yy.max()+4)
        qe=qedge[y0:y1,x0:x1]; vm=visible[y0:y1,x0:x1]
        qy,qx=np.where(qe>0)
        if len(qx)<40:return None
        qdist=cv2.distanceTransform(255-qe,cv2.DIST_L2,3)
        rows=[]
        for d,pins,ref in self.refs:
            best=None
            # Yellow player arrow can overlap and displace the apparent gate center.
            for offset in ((0,) if gate_visible else (0,.2,.4,.6)):
                a=cy+np.float64([0,sy[3]*offset]);b=cb
                u=pins[1]-pins[0];v=b-a
                z=complex(*v)/complex(*u)
                angle=math.degrees(math.atan2(z.imag,z.real))
                if abs(angle)>14:continue  # game map is north-up; refuse large inferred rotations
                A=np.float64([[z.real,-z.imag],[z.imag,z.real]])
                t=a-A@pins[0]
                for dx in (-3,0,3):
                    for dy in (-3,0,3):
                        shift=np.float64([dx,dy]);M=np.column_stack([A,t+shift-[x0,y0]])
                        warped=cv2.warpAffine(ref,M,(x1-x0,y1-y0))
                        re=cv2.Canny(warped,35,85)
                        rd=cv2.distanceTransform(255-re,cv2.DIST_L2,3)
                        forward=float(np.mean(np.exp(-rd[qy,qx]/2.5)))
                        ry,rx=np.where((re>0)&(vm>0))
                        backward=float(np.mean(np.exp(-qdist[ry,rx]/2.5))) if len(rx) else 0
                        score=2*forward*backward/max(.001,forward+backward)
                        if best is None or score>best[0]:best=(score,A,t+shift,angle,forward,backward)
            if best is None:continue
            score,A,t,angle,fwd,bwd=best
            inv=np.linalg.inv(A)
            def project(points):return ((np.float64(points)-t)@inv.T).tolist()
            poly=project([[x0,y0],[x1,y0],[x1,y1],[x0,y1]])
            pos=project([[anchor[0]*w,anchor[1]*h]])[0] if anchor else None
            rows.append({'id':d['id'],'name':d['name'],'score':round(score*100,2),'inliers':0,'coverage':round(len(qx)/(w*h),4),'polygon':poly,'position':pos,'center':project([[(x0+x1)/2,(y0+y1)/2]])[0],'method':'doors','edge_fit':round(score,3),'angle':round(angle,2)})
        rows.sort(key=lambda r:r['score'],reverse=True)
        if not rows:return None
        best=rows[0];margin=best['score']-(rows[1]['score'] if len(rows)>1 else 0)
        certain=best['score']>=60 and margin>=12
        return {'status':'matched' if certain else 'uncertain','method':'doors','candidates':rows[:5], 'doors':{'yellow':(cy/scale).tolist(),'blue':(cb/scale).tolist()}, 'reason':'已结合两门位置和可见地形匹配。' if certain else '已检测两门；起始房间仍可能重复，请继续探索。'}
