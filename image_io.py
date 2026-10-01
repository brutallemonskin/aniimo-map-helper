"""Read image bytes with Python so Windows Unicode paths work reliably."""
from pathlib import Path
import cv2
import numpy as np


def read_image(path, flags=cv2.IMREAD_COLOR):
    path = Path(path)
    try:
        raw = path.read_bytes()
    except OSError as error:
        raise ValueError(f'Cannot read image: {path.name}. Extract the complete ZIP into a writable folder.') from error
    try:
        image = cv2.imdecode(np.frombuffer(raw, dtype=np.uint8), flags) if raw else None
    except cv2.error:
        image = None
    if image is None or image.size == 0:
        raise ValueError(f'Invalid or empty image: {path.name}. Download and extract the complete ZIP again.')
    return image
