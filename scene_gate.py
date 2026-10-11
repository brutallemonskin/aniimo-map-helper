"""只跳过标题明确的组队／背包页面；未知布局继续完整识别。"""
from pathlib import Path
import cv2
from image_io import read_image
from recognition_timing import stage

_templates={}
for _title,_file in (('队伍','screen-team-template.png'),('背包','screen-inventory-template.png')):
    try:
        _templates[_title]=read_image(Path(__file__).resolve().parent/'data'/_file,cv2.IMREAD_GRAYSCALE)
    except ValueError:
        pass


@stage('界面类型检查')
def non_map_screen(image):
    h,w=image.shape[:2]
    if h<240 or w<320:return None
    factor=720/h
    head=cv2.resize(image[:round(80/factor),:round(200/factor)],(200,80),interpolation=cv2.INTER_AREA)
    white=cv2.inRange(cv2.cvtColor(head,cv2.COLOR_BGR2HSV),(0,0,200),(179,70,255))
    region=white[15:65,70:170]
    fits=[]
    for title,template in _templates.items():
        score=cv2.matchTemplate(region,template,cv2.TM_CCOEFF_NORMED)
        fits.append((cv2.minMaxLoc(score)[1],title))
    fits.sort(reverse=True)
    # 标题匹配必须清楚领先；裁切、英文或更新后的页面不作猜测。
    if fits and fits[0][0]>=.94 and (len(fits)==1 or fits[0][0]-fits[1][0]>=.12):
        return fits[0][1]
    return None
