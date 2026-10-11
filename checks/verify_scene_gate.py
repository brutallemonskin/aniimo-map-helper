"""验证已知菜单快速跳过，并保留地图、未知界面和有效小地图。"""
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import cv2
import numpy as np
from image_io import read_image
from matcher import Matcher
from scene_gate import non_map_screen

ROOT=Path(__file__).resolve().parents[1]


def header_image(path,offset=(0,0)):
    template=read_image(path,cv2.IMREAD_GRAYSCALE)
    image=np.zeros((720,1280,3),np.uint8)
    x,y=83+offset[0],23+offset[1];h,w=template.shape
    image[y:y+h,x:x+w]=cv2.cvtColor(template,cv2.COLOR_GRAY2BGR)
    return image


class SceneChecks(unittest.TestCase):
    def test_known_titles(self):
        for name,title in (('screen-team-template.png','队伍'),('screen-inventory-template.png','背包')):
            for offset in ((0,0),(3,2)):
                image=header_image(ROOT/'data'/name,offset)
                self.assertEqual(non_map_screen(image),title)

    def test_map_title_is_not_skipped(self):
        image=header_image(ROOT/'checks/data/地图标题.png')
        self.assertIsNone(non_map_screen(image))

    def test_partial_title_is_not_enough(self):
        image=header_image(ROOT/'data/screen-team-template.png')
        image[:,112:]=0
        self.assertIsNone(non_map_screen(image))

    def test_map_atlas_is_not_a_menu(self):
        catalog=json.loads((ROOT/'data/catalog.json').read_text(encoding='utf-8'))
        for item in catalog:
            image=read_image(ROOT/item['image'].lstrip('/'))
            self.assertIsNone(non_map_screen(image),item['id'])

    def test_menu_does_not_start_map_search(self):
        matcher=Matcher();image=header_image(ROOT/'data/screen-team-template.png')
        with patch.object(matcher.minimap,'extract',return_value=None),patch.object(matcher,'_match') as search:
            result=matcher.match(image)
        search.assert_not_called()
        self.assertEqual(result['recognition_path'],'menu')

    def test_visible_minimap_has_priority(self):
        matcher=Matcher();image=header_image(ROOT/'data/screen-team-template.png')
        with patch.object(matcher.minimap,'extract',return_value=('sample',)), \
             patch.object(matcher,'match_minimap',return_value={'status':'matched','method':'minimap'}) as tracking:
            result=matcher.match(image)
        tracking.assert_called_once()
        self.assertEqual(result['method'],'minimap')


if __name__=='__main__':unittest.main()
