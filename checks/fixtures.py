"""由仓库底图构造可复现输入；这些样例不代表真实游戏准确率。"""
import json
from pathlib import Path
import subprocess
import types

import cv2
import numpy as np
from image_io import read_image

ROOT = Path(__file__).resolve().parents[1]
BASELINE = '1be9812'


def upstream_module(name):
    source = subprocess.run(['git', 'show', f'{BASELINE}:{name}.py'], cwd=ROOT,
                            check=True, capture_output=True).stdout.decode('utf-8')
    module = types.ModuleType('baseline_' + name)
    module.__file__ = str(ROOT / (name + '.py'))
    exec(compile(source, module.__file__, 'exec'), module.__dict__)
    return module


def dungeon(map_id='sanctum-32', entrance='orange', size=(1920, 1080), sparse=False):
    data = json.loads((ROOT / 'data' / (map_id + '.json')).read_text(encoding='utf-8'))
    ref = read_image(ROOT / data['image'].lstrip('/'))
    pins = np.array([[p['x'], p['y']] for category in ('entrance', 'side-entrance')
                     for p in data['points'] if p['category'] == category], dtype=float)
    scale = min(.8, 600 / np.linalg.norm(pins[1] - pins[0]))
    shift = np.array([640., 360.]) - pins.mean(axis=0) * scale
    transform = np.column_stack([np.eye(2) * scale, shift])
    image = cv2.warpAffine(ref, transform, (1280, 720))
    if sparse:
        visible = np.zeros(image.shape[:2], np.uint8)
        for point in pins:
            x, y = np.rint(point * scale + shift).astype(int)
            cv2.circle(visible, (x, y), 48, 255, -1)
        image[visible == 0] = 0
    if entrance:
        colors = [(0, 140, 255) if entrance == 'orange' else (0, 255, 255), (255, 120, 0)]
        for point, color in zip(pins, colors):
            x, y = np.rint(point * scale + shift).astype(int)
            cv2.rectangle(image, (x - 9, y - 14), (x + 9, y + 14), color, -1)
    return cv2.resize(image, size)


def minimap_sample(position=(870, 955), map_id='sanctum-32'):
    ref = read_image(ROOT / 'data' / (map_id + '.webp'), cv2.IMREAD_GRAYSCALE)
    x, y = position
    query = cv2.GaussianBlur(ref[y - 100:y + 100, x - 100:x + 100], (5, 5), 0)
    yy, xx = np.mgrid[:200, :200]
    radius = (xx - 100)**2 + (yy - 100)**2
    mask = np.uint8((radius < 88**2) & (radius > 28**2)) * 255
    return query, mask, np.array([100., 100.]), True
