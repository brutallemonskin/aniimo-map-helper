"""检查遮罩、歧义拒绝、定位和快速路径的独立两门约束。"""
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import cv2
import numpy as np
from checks.fixtures import ROOT, dungeon, minimap_sample, upstream_module
from door_matcher import DoorMatcher
from image_io import read_image
from masked_correlation import MaskedCorrelation
from matcher import Matcher
from minimap import MinimapTracker
from player import detect_egg
from relocalizer import Relocalizer


class CorrelationChecks(unittest.TestCase):
    def test_masked_scores_and_peak(self):
        rng=np.random.default_rng(713)
        for shape,template_shape in (((320,380),(40,35)),((450,460),(200,200))):
            image=rng.integers(0,256,shape,dtype=np.uint8)
            h,w=template_shape;query=image[35:35+h,47:47+w].copy()
            mask=np.uint8(rng.random(template_shape)>.25)*255
            expected=cv2.matchTemplate(image,query,cv2.TM_CCOEFF_NORMED,mask=mask)
            actual=MaskedCorrelation(query,mask).match(image)
            np.testing.assert_allclose(actual,expected,rtol=2e-4,atol=2e-5)
            self.assertEqual(cv2.minMaxLoc(actual)[3],(47,35))

    def test_excluded_pixels_do_not_vote(self):
        rng=np.random.default_rng(97)
        query=rng.integers(20,220,(50,50),dtype=np.uint8)
        mask=np.full(query.shape,255,np.uint8);mask[15:35,15:35]=0
        image=query.copy();image[mask==0]=255
        value=MaskedCorrelation(query,mask).match(image)[0,0]
        self.assertAlmostEqual(float(value),1.,places=5)

    def test_flat_or_empty_evidence_is_rejected(self):
        rng=np.random.default_rng(51)
        query=rng.integers(0,256,(40,40),dtype=np.uint8)
        mask=np.full(query.shape,255,np.uint8)
        self.assertTrue(np.all(MaskedCorrelation(query,mask).match(np.full((80,80),127,np.uint8))==-1))
        self.assertTrue(np.all(MaskedCorrelation(query,mask*0).match(query)==-1))
        self.assertTrue(np.all(MaskedCorrelation(query*0,mask).match(query)==-1))


class RecognitionChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cv2.setNumThreads(1)

    def test_moving_minimap_matches_upstream(self):
        original=upstream_module('minimap').MinimapTracker(ROOT)
        optimized=MinimapTracker(ROOT)
        for scale in (None,1.):
            for x in (870,874,878):
                sample=minimap_sample((x,955));previous=[x-8,955]
                before=original.match(sample,'sanctum-32',previous,scale)
                after=optimized.match(sample,'sanctum-32',previous,scale)
                self.assertEqual(before['status'],after['status'])
                self.assertEqual(after['status'],'matched')
                np.testing.assert_allclose(before['candidates'][0]['position'],after['candidates'][0]['position'],atol=.01)
                self.assertAlmostEqual(before['candidates'][0]['score'],after['candidates'][0]['score'],places=2)

    def test_relocalization_matches_upstream(self):
        old=upstream_module('relocalizer').Relocalizer()
        new=Relocalizer();sample=minimap_sample()
        ref=read_image(ROOT/'data/sanctum-32.webp',cv2.IMREAD_GRAYSCALE)
        before=old.propose(sample,'sanctum-32',ref,1.)
        after=new.propose(sample,'sanctum-32',ref,1.)
        self.assertEqual(before is None,after is None)
        if before is not None:
            np.testing.assert_allclose(before[0],after[0],atol=.01)
            self.assertEqual(before[1],after[1])

    def test_repeated_rooms_are_not_confirmed(self):
        rng=np.random.default_rng(315)
        tile=rng.integers(0,255,(80,80),dtype=np.uint8)
        ref=np.tile(tile,(20,20))
        sample=(ref[400:600,400:600].copy(),np.full((200,200),255,np.uint8),np.array([100.,100.]),True)
        self.assertIsNone(Relocalizer().propose(sample,'repeated',ref,1.))

    def test_egg_detection_matches_upstream(self):
        old=upstream_module('player').detect_egg
        template=read_image(ROOT/'data/player-egg-template.png')
        height=34;width=round(height*template.shape[1]/template.shape[0])
        image=np.full((300,450,3),55,np.uint8)
        image[120:120+height,210:210+width]=cv2.resize(template,(width,height))
        self.assertEqual(old(image),detect_egg(image))
        self.assertIsNotNone(detect_egg(image))
        self.assertIsNone(detect_egg(np.full_like(image,55)))

    def test_parallel_doors_preserve_scores(self):
        old=upstream_module('door_matcher').DoorMatcher(ROOT)
        new=DoorMatcher(ROOT)
        image=dungeon(entrance='yellow',sparse=True)
        self.assertEqual(old.match(image),new.match(image))

    def test_fast_path_checks_both_doors_and_ambiguity(self):
        doors=DoorMatcher(ROOT);image=dungeon()
        prepared=doors.prepare(image)
        candidate=doors.match(image,prepared=prepared)['candidates'][0]
        # 门匹配的 polygon 表示地形裁剪；特征匹配的 polygon 表示完整画面。
        polygon=np.array(candidate['polygon'])
        basis=np.column_stack(((polygon[1]-polygon[0])/(prepared.x1-prepared.x0),
                               (polygon[3]-polygon[0])/(prepared.y1-prepared.y0)))
        origin=polygon[0]-basis@[prepared.x0,prepared.y0]
        candidate['polygon']=(np.array([[0,0],[prepared.w,0],[prepared.w,prepared.h],[0,prepared.h]])@basis.T+origin).tolist()
        self.assertTrue(doors.agrees_with_features(prepared,candidate))
        displaced=dict(candidate,polygon=(np.array(candidate['polygon'])+[100,100]).tolist())
        self.assertFalse(doors.agrees_with_features(prepared,displaced))
        matcher=Matcher();matcher.doors=doors
        candidate.update(inliers=100,inlier_ratio=.9,residual=.2,coverage=.1)
        result={'status':'matched','candidates':[candidate],'feature_inlier_margin':3}
        self.assertTrue(matcher._feature_fast_path(result,prepared))
        result['feature_inlier_margin']=1.9
        self.assertFalse(matcher._feature_fast_path(result,prepared))
        result['feature_inlier_margin']=3;candidate['inliers']=12
        self.assertFalse(matcher._feature_fast_path(result,prepared))


if __name__=='__main__':
    unittest.main()
