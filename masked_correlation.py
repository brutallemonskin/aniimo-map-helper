"""复用二值遮罩的统计量，保留遮罩归一化相关匹配公式。"""
import cv2
import numpy as np


class MaskedCorrelation:
    def __init__(self, template, mask):
        self.template = template
        self.mask = mask
        self.binary = mask.dtype == np.uint8 and template.ndim == 2
        if not self.binary:
            return
        self.weights = np.float32(mask != 0)
        self.count = float(self.weights.sum())
        if self.count == 0:
            self.norm = 0.
            return
        values = template.astype(np.float32)
        mean = float(np.sum(values * self.weights, dtype=np.float64) / self.count)
        self.centered = (values - mean) * self.weights
        self.norm = float(np.sqrt(np.sum(self.centered * self.centered, dtype=np.float64)))
        self.remainder = float(np.sum(self.centered, dtype=np.float64) / self.count)

    def match(self, image):
        if not self.binary:
            return cv2.matchTemplate(image, self.template, cv2.TM_CCOEFF_NORMED, mask=self.mask)
        shape = (image.shape[0] - self.template.shape[0] + 1,
                 image.shape[1] - self.template.shape[1] + 1)
        if self.norm < 1e-8:
            return np.full(shape, -1, dtype=np.float32)
        # 整图减去常量不改变归一化相关系数，并减少方差相减时的消减误差。
        values = image.astype(np.float32)
        values -= float(np.mean(values))
        total = cv2.matchTemplate(values, self.weights, cv2.TM_CCORR)
        square = cv2.matchTemplate(values * values, self.weights, cv2.TM_CCORR)
        numerator = cv2.matchTemplate(values, self.centered, cv2.TM_CCORR)
        numerator -= total * self.remainder
        variance = square - total * total / self.count
        with np.errstate(divide='ignore', invalid='ignore'):
            result = numerator / (self.norm * np.sqrt(np.maximum(variance, 0)))
        # 无纹理区域的浮点残差不能作为定位依据。
        result[variance <= np.maximum(1e-6, np.abs(square) * 1e-6)] = -1
        return np.nan_to_num(result, nan=-1, posinf=-1, neginf=-1)
