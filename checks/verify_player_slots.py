"""验证本局编号选择、颜色变化和歧义拒绝。"""
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import cv2
import numpy as np
from image_io import read_image
from player import detect_player

ROOT=Path(__file__).resolve().parents[1]


def scene(slots=(1,2,3),colors=((0,220,255),(80,240,120),(255,170,80)),duplicate=False):
    image=np.full((720,1280,3),35,np.uint8);points={}
    for index,slot in enumerate(slots):
        template=read_image(ROOT/f'data/player-number-{slot}-template.png',cv2.IMREAD_GRAYSCALE)
        x,y=240+index*220,260
        h,w=template.shape;image[y:y+h,x:x+w][template>0]=colors[index%len(colors)]
        points[slot]=[x+w/2,y+h/2]
        if duplicate:
            image[y+120:y+120+h,x:x+w][template>0]=colors[index%len(colors)]
    # 金色图标不能替代已指定的队伍编号。
    cv2.ellipse(image,(1010,210),(25,18),0,0,280,(0,220,255),7)
    return image,points


class SlotChecks(unittest.TestCase):
    def test_all_slots_and_color_orders(self):
        for colors in (((0,220,255),(80,240,120),(255,170,80)),
                       ((255,170,80),(0,220,255),(80,240,120))):
            image,points=scene(colors=colors)
            for slot in (1,2,3):
                found=detect_player(image,slot)
                self.assertIsNotNone(found,f'编号 {slot} 未识别')
                self.assertEqual(found['slot'],slot)
                np.testing.assert_allclose(found['point'],points[slot],atol=1)

    def test_scaled_labels(self):
        original,points=scene()
        for scale in (.75,1.5):
            image=cv2.resize(original,None,fx=scale,fy=scale)
            for slot in (1,2,3):
                found=detect_player(image,slot)
                self.assertIsNotNone(found,f'编号 {slot} 缩放 {scale} 未识别')
                np.testing.assert_allclose(np.array(found['point'])/scale,points[slot],atol=1)

    def test_unspecified_or_missing_slot_does_not_pick_egg(self):
        image,_=scene(slots=(1,3))
        self.assertIsNone(detect_player(image))
        self.assertIsNone(detect_player(image,2))

    def test_duplicate_slot_is_ambiguous(self):
        image,_=scene(slots=(2,),duplicate=True)
        self.assertIsNone(detect_player(image,2))

    def test_normal_arrow_still_works_without_team_label(self):
        image=np.full((720,1280,3),35,np.uint8)
        cv2.fillPoly(image,[np.array([[550,280],[530,325],[550,312],[570,325]])],(0,220,255))
        found=detect_player(image)
        self.assertIsNotNone(found)
        self.assertNotEqual(found.get('kind'),'team-label')


if __name__=='__main__':unittest.main()
