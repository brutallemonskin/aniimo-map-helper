"""Read image bytes with Python so Windows Unicode paths work reliably."""
from pathlib import Path
import cv2
import numpy as np


def normalize_map_lighting(image):
    """Restore dim capture whites without changing already-bright frames.

    Use a bounded global gain, preserving hues, geometry and pixel coordinates.
    This is not HDR decoding; it only compensates for uniformly dim captures.
    """
    whites=float(np.percentile(image[::4,::4].max(axis=2),99.9))
    if not 100<=whites<225:return image
    lut=np.clip(np.arange(256)*255/whites,0,255).astype(np.uint8)
    return cv2.LUT(image,lut)


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
