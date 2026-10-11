"""与固定上游提交比较结果和耗时；支持加入真实截图验收。"""
import argparse
import json
from pathlib import Path
import statistics
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cv2
import numpy as np
from matcher import Matcher
from door_matcher import DoorMatcher
from checks.fixtures import BASELINE, ROOT, dungeon, upstream_module
from image_io import read_image
from local_version import LOCAL_VERSION
from minimap import MinimapTracker
from checks.fixtures import minimap_sample


def run_timed(call, repeats=1):
    elapsed=[]
    result=None
    for _ in range(repeats):
        cv2.setRNGSeed(17)
        start=time.perf_counter()
        result=call()
        elapsed.append((time.perf_counter()-start)*1000)
    return result, {'平均毫秒':round(statistics.mean(elapsed),2),
                    '最大毫秒':round(max(elapsed),2),'各次毫秒':[round(v,2) for v in elapsed]}


def leader(result):
    candidates=(result or {}).get('candidates',[])
    return candidates[0]['id'] if candidates else None


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repeats',type=int,default=2)
    parser.add_argument('--images',nargs='*',default=[])
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    if args.repeats<1:parser.error('重复次数必须大于零。')
    matcher=Matcher();matcher.build()
    if not matcher.ready:raise RuntimeError(matcher.error)
    old=upstream_module('matcher');old.DoorMatcher=upstream_module('door_matcher').DoorMatcher
    old.detect_player=upstream_module('player').detect_player
    old_minimap=upstream_module('minimap')
    old_minimap.Relocalizer=upstream_module('relocalizer').Relocalizer
    old.MinimapTracker=old_minimap.MinimapTracker
    original=old.Matcher();original.maps=matcher.maps;original.ready=True;original.doors=old.DoorMatcher(ROOT)
    cases=[('完整地形黄色入口',dungeon(entrance='yellow')),
           ('完整地形橙色入口',dungeon('sanctum-31')),
           ('稀疏黄色入口',dungeon(entrance='yellow',sparse=True)),
           ('稀疏橙色入口',dungeon('sanctum-35',sparse=True)),
           ('无门特征匹配',dungeon(entrance=None)),
           ('纯色画面',np.zeros((1080,1920,3),np.uint8))]
    cases.extend((Path(p).name,read_image(p)) for p in args.images)
    report={'上游基线':BASELINE,'本地修订':LOCAL_VERSION,'计算后端':matcher.features.status(),
            '说明':'内置输入由底图构造，计时覆盖 Matcher.match；不包含采集、网络和网页显示。',
            '结果':[]}
    for name,image in cases:
        cv2.setNumThreads(2)
        before,cpu=run_timed(lambda:original.match(image),args.repeats)
        cv2.setNumThreads(2)
        after,optimized=run_timed(lambda:matcher.match(image),args.repeats)
        row={'样例':name,'原版':cpu,'优化版':optimized,'原版状态':before['status'],
             '优化版状态':after['status'],'原版首选':leader(before),'优化版首选':leader(after),
             '识别路径':after.get('recognition_path'),
             '首选与状态一致':leader(before)==leader(after) and before['status']==after['status']}
        report['结果'].append(row)
        print(json.dumps(row,ensure_ascii=False),flush=True)
    for scale,name in ((None,'小地图首次比例搜索'),(1.,'小地图移动跟踪')):
        samples=[(minimap_sample((870+4*i,955)),[862+4*i,955]) for i in range(args.repeats)]
        old_tracker=old.MinimapTracker(ROOT);new_tracker=MinimapTracker(ROOT)
        old_inputs=iter(samples);new_inputs=iter(samples)
        def track(tracker,inputs):
            sample,previous=next(inputs)
            return tracker.match(sample,'sanctum-32',previous,scale)
        before,cpu=run_timed(lambda:track(old_tracker,old_inputs),args.repeats)
        after,optimized=run_timed(lambda:track(new_tracker,new_inputs),args.repeats)
        same=leader(before)==leader(after) and before['status']==after['status']
        if before['candidates'] and after['candidates']:
            same=bool(same and np.allclose(before['candidates'][0]['position'],after['candidates'][0]['position'],atol=.01))
        row={'样例':name,'原版':cpu,'优化版':optimized,'首选与状态一致':same}
        report['结果'].append(row)
        print(json.dumps(row,ensure_ascii=False),flush=True)
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    if any(not row['首选与状态一致'] for row in report['结果']):
        raise SystemExit('存在识别差异，请人工检查结果。')


if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
