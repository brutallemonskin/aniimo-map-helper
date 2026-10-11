import json, threading
from pathlib import Path
from image_io import read_image
import cv2
import numpy as np
from door_matcher import DoorMatcher
from player import detect_player
from minimap import MinimapTracker
from loot_detector import detect_rainbow_beams
from feature_matcher import FeatureMatcher
from recognition_timing import recognition, stage
from scene_gate import non_map_screen

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
        self.features = FeatureMatcher()

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
            for slot in (1,2,3):read_image(ROOT/f'data/player-number-{slot}-template.png')
            for name in ('screen-team-template.png','screen-inventory-template.png'):read_image(ROOT/'data'/name)
            for m in json.loads((ROOT/'data/catalog.json').read_text(encoding='utf8')):
                if not (m['id'].startswith('sanctum-') or m['id']=='egg-heist'): continue
                im = read_image(str(ROOT / m['image'].lstrip('/')))
                if im.shape[1] < 512: raise ValueError('Map image too small: '+m['id'])
                scale = min(1., 1400/im.shape[1])
                im = cv2.resize(im, None, fx=scale, fy=scale)
                kp, des = self.sift.detectAndCompute(self.gray(im), None)
                self.maps.append((m, scale, np.float32([k.pt for k in kp]), des))
            if not self.maps: raise ValueError('No map images found. Extract the complete ZIP again.')
            self.doors = DoorMatcher(ROOT)
            self.features.prepare(self.maps)
            self.ready = True
        except Exception as e:
            self.error = str(e)

    @recognition
    def match_crop(self, im, tracking=None, realtime_tracking=True, scene=None, observation=None):
        sample=self.minimap.extract_crop(im)
        if sample is None:
            return {'requires_full_frame':True}
        return self.match_minimap(sample, tracking, realtime_tracking, scene, observation)

    def match_minimap(self, sample, tracking, realtime_tracking, scene, observation=None):
        if not realtime_tracking:
            return {'status':'paused','method':'minimap','candidates':[],
                    'player':None,'position_source':None,'loot_observations':[],
                    'reason':'实时定位已关闭；打开大地图仍可识别地图和位置。'}
        tracking=tracking or {}
        with self.lock:
            answer=self.minimap.match(sample,tracking.get('id'),tracking.get('position'),tracking.get('scale'),observation)
        answer['loot_observations']=detect_rainbow_beams(scene) if scene is not None else []
        return answer

    @recognition
    def match(self, im, anchor=None, tracking=None, outdoor_mode='egg-heist', realtime_tracking=True, observation=None, player_slot=None):
        # Uniform frames cannot contain map geometry; skip costly icon searches.
        if float(np.max(cv2.meanStdDev(im)[1]))<1:
            return {'status':'unknown','candidates':[], 'player':None,'position_source':None,'recognition_path':'blank','reason':'画面信息不足，请打开地图并扩大可见区域。'}
        sample=self.minimap.extract(im)
        if sample is not None:
            return self.match_minimap(sample,tracking,realtime_tracking,im,observation)
        menu=non_map_screen(im)
        if menu:
            return {'status':'unknown','candidates':[],'player':None,'position_source':None,
                    'recognition_path':'menu','reason':f'当前为{menu}界面；返回游戏地图后继续定位。'}
        answer=self._match(im,anchor,outdoor_mode)
        # 只有存在地图候选时才搜索人物，避免组队、背包等界面扫描十四档蛋图标。
        player=detect_player(im,player_slot) if anchor is None and answer.get('candidates') else None
        region=answer.pop('_query_region',[0.,0.,1.,1.])
        if player is not None:
            self._place_player(answer,player['normalized'],region)
        answer['player']=player
        answer['position_source']='manual' if anchor is not None else ('auto' if player else None)
        if answer.get('candidates') and anchor is None and player is None:
            answer['reason']+=' 小队模式请核对“本局我的编号”，再打开大地图校准位置。'
        for candidate in answer.get('candidates',[]):
            candidate['position_source']=answer['position_source']
        return answer

    @staticmethod
    def _place_player(answer,point,region):
        """沿用已经求出的配准变换，不重复识别地形。"""
        x0,y0,x1,y1=region
        fraction=(np.asarray(point,dtype=float)-[x0,y0])/[x1-x0,y1-y0]
        for candidate in answer.get('candidates',[]):
            polygon=np.asarray(candidate['polygon'],dtype=float)
            position=polygon[0]+fraction[0]*(polygon[1]-polygon[0])+fraction[1]*(polygon[3]-polygon[0])
            candidate['position']=position.tolist()

    def _match(self, im, anchor=None, outdoor_mode='egg-heist'):
        if not self.ready: return {'status':'loading', 'indexed': len(self.maps), 'error':self.error}
        with self.lock:
            prepared = self.doors.prepare(im)
            feature_result = None
            if prepared is not None and not prepared.sparse and self.features.enabled:
                feature_result = self._match_features(im, anchor)
                if self._feature_fast_path(feature_result, prepared):
                    feature_result['recognition_path'] = 'features_verified_doors'
                    return feature_result
            door_result = self.doors.match(im, anchor, prepared) if prepared is not None else None
            if door_result and door_result['candidates'][0]['score'] >= 35:
                door_result['recognition_path'] = 'doors'
                door_result['_query_region']=[prepared.x0/prepared.w,prepared.y0/prepared.h,
                                               prepared.x1/prepared.w,prepared.y1/prepared.h]
                return door_result
            if feature_result is None:feature_result = self._match_features(im, anchor)
            feature_result['recognition_path'] = 'features'
            return feature_result

    def _feature_fast_path(self, result, prepared):
        if result['status']!='matched' or not result['candidates']:return False
        best=result['candidates'][0]
        # 比原特征确认更严格：所有地图仍参与检索，弱证据交回完整门匹配。
        strong=(best['inliers']>=40 and best['inlier_ratio']>=.75 and best['residual']<=1.5
                and best['coverage']>=.035
                and result.get('feature_inlier_margin',0)>2)
        return bool(strong and self.doors.agrees_with_features(prepared,best))

    @stage('地图特征匹配')
    def _match_features(self, im, anchor=None):
        h,w = im.shape[:2]
        qs = min(1., 1000/max(h,w))
        small = cv2.resize(im, None, fx=qs, fy=qs)
        kp, des = self.sift.detectAndCompute(self.gray(small), None)
        if des is None or len(kp)<12: return {'status':'unknown','candidates':[], 'reason':'画面信息不足，请打开地图并扩大可见区域。'}
        pts = np.float32([k.pt for k in kp])
        query = self.features.query(des)
        results = []
        for m, scale, target, desc in self.maps:
            if m['id'].startswith('egg-heist') and m['id']!='egg-heist':continue
            if desc is None: continue
            pairs = self.features.knn_match(query, m['id'], desc)
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
        margin=best['inliers']/max(1,max((row['inliers'] for row in results[1:]),default=0)) if best else 0
        return {'status':'matched' if certain else ('uncertain' if best else 'unknown'),'candidates':results[:3], 'feature_inlier_margin':margin,'reason':'局部房间可能重复；请走到岔路或扩大地图范围。' if not certain else '已匹配地图形状；请结合入口与房间核对。'}
