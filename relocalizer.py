"""Coarse full-map search proposes positions; detailed tracking confirms them."""
import cv2
import numpy as np


def motion_agrees(before, after, displacement, scale):
    """Require independent HUD motion evidence before accepting a larger step."""
    old,mask,_,_=before;new,new_mask,_,_=after
    points=cv2.goodFeaturesToTrack(old,100,.015,7,mask=mask)
    if points is None or len(points)<8:return False
    shift,response=cv2.phaseCorrelate(old.astype(np.float32),new.astype(np.float32))
    if not np.all(np.isfinite(shift)) or response<.12:return False
    expected=-np.array(displacement)*scale+(after[2]-before[2])
    if np.linalg.norm(np.array(shift)-expected)>18:return False
    seed=points+np.array(shift,dtype=np.float32)
    moved,ok,_=cv2.calcOpticalFlowPyrLK(old,new,points,seed,winSize=(25,25),maxLevel=2,flags=cv2.OPTFLOW_USE_INITIAL_FLOW)
    if moved is None:return False
    back,back_ok,_=cv2.calcOpticalFlowPyrLK(new,old,moved,points.copy(),winSize=(25,25),maxLevel=2,flags=cv2.OPTFLOW_USE_INITIAL_FLOW)
    if back is None:return False
    a=points[:,0];b=moved[:,0]
    valid=(ok.ravel()>0)&(back_ok.ravel()>0)&(np.linalg.norm(back[:,0]-a,axis=1)<1.5)
    xy=np.rint(b).astype(int);inside=(xy[:,0]>=0)&(xy[:,0]<200)&(xy[:,1]>=0)&(xy[:,1]<200)
    valid &= inside
    valid[inside] &= new_mask[xy[inside,1],xy[inside,0]]>0
    a,b=a[valid],b[valid]
    if len(a)<8:return False
    transform,inliers=cv2.estimateAffinePartial2D(a,b,method=cv2.RANSAC,ransacReprojThreshold=2.5)
    if transform is None or inliers.sum()<8 or inliers.mean()<.65:return False
    keep=inliers.ravel()>0
    if np.min(np.ptp(a[keep],axis=0))<25:return False
    # North-up terrain should translate, not rotate or change floors.
    if np.max(np.abs(transform[:,:2]-np.eye(2)))>.06:return False
    return bool(np.linalg.norm(transform[:,2]-expected)<10)


class Relocalizer:
    def __init__(self):
        self.references={}

    def propose(self,sample,map_id,reference,previous_scale=None):
        gray,mask,point,_=sample
        shrink=.3
        query=cv2.resize(gray,(60,60),interpolation=cv2.INTER_AREA)
        keep=cv2.resize(mask,(60,60),interpolation=cv2.INTER_NEAREST)
        scales=np.linspace(.65,1.55,7) if previous_scale is None else (previous_scale*.94,previous_scale,previous_scale*1.06)
        peaks=[]
        for scale in scales:
            key=(map_id,round(float(scale),5))
            target=self.references.get(key)
            if target is None:
                target=cv2.resize(reference,None,fx=float(scale*shrink),fy=float(scale*shrink),interpolation=cv2.INTER_AREA)
                target=cv2.GaussianBlur(target,(3,3),0)
                self.references[key]=target
                if len(self.references)>12:self.references.pop(next(iter(self.references)))
            if min(target.shape)<60:continue
            score=cv2.matchTemplate(target,query,cv2.TM_CCOEFF_NORMED,mask=keep)
            score=np.nan_to_num(score,nan=-1,posinf=-1,neginf=-1)
            for _ in range(2):
                _,fit,_,loc=cv2.minMaxLoc(score)
                position=(np.array(loc)/shrink+point)/scale
                peaks.append((fit,position,float(scale)))
                x,y=loc;radius=max(10,round(55*scale*shrink))
                score[max(0,y-radius):y+radius+1,max(0,x-radius):x+radius+1]=-1
        if not peaks:return None
        peaks.sort(key=lambda p:p[0],reverse=True);fit,position,scale=peaks[0]
        alternative=max((v for v,p,_ in peaks if np.linalg.norm(p-position)>55),default=-1)
        if fit<.68 or fit-alternative<.05:return None
        return position.tolist(),scale
