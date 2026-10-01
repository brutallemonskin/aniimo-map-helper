import json, threading
from pathlib import Path
from image_io import read_image
import cv2
import numpy as np
from door_matcher import DoorMatcher
from player import detect_player
from minimap import MinimapTracker

ROOT = Path(__file__).resolve().parent
cv2.setNumThreads(2)

class Matcher:
    def __init__(self):
        self.maps = []
        self.ready = False
        self.error = None
        self.lock = threading.Lock()
        self.sift = cv2.SIFT_create(nfeatures=4500, contrastThreshold=0.02)
        self.doors = None
        self.minimap = MinimapTracker(ROOT)

    @staticmethod
    def gray(im):
        g = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY) if im.ndim == 3 else im
        return cv2.createCLAHE(2.0, (8,8)).apply(g)

    def build(self):
        try:
            self.maps = []
            self.error = None
            self.ready = False
            read_image(ROOT/'data/player-egg-template.png')
            for m in json.loads((ROOT/'data/catalog.json').read_text(encoding='utf8')):
                if not (m['id'].startswith('sanctum-') or m['id'].startswith('egg-heist')): continue
                im = read_image(str(ROOT / m['image'].lstrip('/')))
                if im.shape[1] < 512: raise ValueError('Map image too small: '+m['id'])
                scale = min(1., 1400/im.shape[1])
                im = cv2.resize(im, None, fx=scale, fy=scale)
                kp, des = self.sift.detectAndCompute(self.gray(im), None)
                self.maps.append((m, scale, np.float32([k.pt for k in kp]), des))
            if not self.maps: raise ValueError('No map images found. Extract the complete ZIP again.')
            self.doors = DoorMatcher(ROOT)
            self.ready = True
        except Exception as e:
            self.error = str(e)

    def match(self, im, anchor=None, tracking=None, outdoor_mode='egg-heist'):
        # Uniform frames cannot contain map geometry; skip costly icon searches.
        if float(np.max(cv2.meanStdDev(im)[1]))<1:
            return {'status':'unknown','candidates':[], 'player':None,'position_source':None,'reason':'画面信息不足，请打开地图并扩大可见区域。'}
        sample=self.minimap.extract(im)
        if sample is not None:
            tracking=tracking or {}
            with self.lock:
                return self.minimap.match(sample,tracking.get('id'),tracking.get('position'),tracking.get('scale'))
        player=detect_player(im) if anchor is None else None
        effective_anchor=anchor if anchor is not None else (player['normalized'] if player else None)
        answer=self._match(im,effective_anchor,outdoor_mode)
        answer['player']=player
        answer['position_source']='manual' if anchor is not None else ('auto' if player else None)
        for candidate in answer.get('candidates',[]):
            candidate['position_source']=answer['position_source']
        return answer

    def _match(self, im, anchor=None, outdoor_mode='egg-heist'):
        if not self.ready: return {'status':'loading', 'indexed': len(self.maps), 'error':self.error}
        with self.lock:
            door_result = self.doors.match(im, anchor)
            if door_result and door_result['candidates'][0]['score'] >= 35:
                return door_result
            h,w = im.shape[:2]
            qs = min(1., 1000/max(h,w))
            small = cv2.resize(im, None, fx=qs, fy=qs)
            kp, des = self.sift.detectAndCompute(self.gray(small), None)
            if des is None or len(kp)<12: return {'status':'unknown','candidates':[], 'reason':'画面信息不足，请打开地图并扩大可见区域。'}
            pts = np.float32([k.pt for k in kp])
            bf = cv2.BFMatcher()
            results = []
            for m, scale, target, desc in self.maps:
                if m['id'].startswith('egg-heist') and m['id']!=outdoor_mode:continue
                if desc is None: continue
                pairs = bf.knnMatch(des, desc, k=2)
                good = [a for a,b in pairs if a.distance < .70*b.distance]
                # Multiple query features must not vote for one reference feature.
                unique = {}
                for a in sorted(good, key=lambda a:a.distance): unique.setdefault(a.trainIdx, a)
                good = list(unique.values())
                if len(good)<7: continue
                src = pts[[a.queryIdx for a in good]]
                dst = target[[a.trainIdx for a in good]]
                H, mask = cv2.estimateAffinePartial2D(src,dst,method=cv2.RANSAC,ransacReprojThreshold=5,maxIters=2000)
                if H is None: continue
                ins = mask.ravel().astype(bool)
                n = int(ins.sum()); ratio=n/len(good)
                if n<7 or ratio<.32: continue
                spread = cv2.contourArea(cv2.convexHull(src[ins])) / (small.shape[0]*small.shape[1])
                if spread < .012: continue
                corners = np.float32([[0,0],[w*qs,0],[w*qs,h*qs],[0,h*qs]])
                polygon = (corners @ H[:,:2].T+H[:,2])/scale
                center = (np.float32([w*qs/2,h*qs/2])@H[:,:2].T+H[:,2])/scale
                if not (0<=center[0]<=m['width'] and 0<=center[1]<=m['height']): continue
                score = n * min(1,ratio/.65) * min(1,spread/.12)
                pos = None
                if anchor is not None:
                    pos = ((np.float32(anchor)*[w*qs,h*qs])@H[:,:2].T+H[:,2])/scale
                    pos = pos.tolist()
                residual=float(np.median(np.linalg.norm(src[ins]@H[:,:2].T+H[:,2]-dst[ins],axis=1)))
                results.append({'id':m['id'],'name':m['name'],'score':round(score,2),'inliers':n,'inlier_ratio':round(ratio,3),'residual':round(residual,3),'coverage':round(spread,3),'polygon':polygon.tolist(),'position':pos,'center':center.tolist()})
            results.sort(key=lambda r:r['score'],reverse=True)
            best = results[0] if results else None
            certain = bool(best and best['inliers']>=14 and best['score']>=12 and (len(results)==1 or best['score']>results[1]['score']*1.4))
            # Fog and zoom-out shrink the terrain's share of the whole frame.
            # Strong, spatially distributed geometric support can still lock it.
            strong=bool(best and best['inliers']>=24 and best['inlier_ratio']>=.65 and best['residual']<=2.5 and all(best['inliers']>r['inliers']*1.5 for r in results[1:]))
            certain=certain or strong
            return {'status':'matched' if certain else ('uncertain' if best else 'unknown'),'candidates':results[:3], 'reason':'局部房间可能重复；请走到岔路或扩大地图范围。' if not certain else '已匹配地图形状；请结合入口与房间核对。'}
