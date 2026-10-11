"""复用 OpenCL 地图描述子，失败时沿用原来的 CPU 精确匹配。"""
import os

import cv2


class FeatureMatcher:
    def __init__(self):
        self.mode = os.environ.get('ANIIMO_COMPUTE_BACKEND', 'auto').lower()
        self.device = None
        self.error = None
        self.references = {}
        self.enabled = False
        self.bf = cv2.BFMatcher()

    def prepare(self, maps):
        self.references.clear()
        self.enabled = False
        if self.mode == 'cpu':
            return
        try:
            cv2.ocl.setUseOpenCL(True)
            device = cv2.ocl.Device_getDefault()
            # 不把支持 OpenCL 的 CPU 当作显卡加速。
            if not cv2.ocl.useOpenCL() or not device.available() or not (device.type() & 4):
                self.error = '没有可用的 OpenCL 显卡，使用 CPU。'
                return
            self.device = device.name()
            for entry, _, _, descriptors in maps:
                if descriptors is not None:
                    self.references[entry['id']] = cv2.UMat(descriptors)
            # 首次编译放在索引阶段，避免第一张游戏截图承担编译延迟。
            for entry, _, _, descriptors in maps:
                if descriptors is not None and len(descriptors) >= 2:
                    self.bf.knnMatch(cv2.UMat(descriptors[:16]), self.references[entry['id']], k=2)
                    cv2.ocl.finish()
                    break
            self.enabled = True
        except cv2.error as error:
            self._fallback(error)

    def _fallback(self, error):
        self.enabled = False
        self.references.clear()
        self.error = 'OpenCL 不可用，已回退到 CPU：' + str(error)

    def query(self, descriptors):
        """每帧只上传一次；OpenCL 开关需要在处理请求的线程中设置。"""
        if self.enabled:
            try:
                cv2.ocl.setUseOpenCL(True)
                if cv2.ocl.useOpenCL():
                    return descriptors, cv2.UMat(descriptors)
                self._fallback('当前线程无法启用 OpenCL。')
            except cv2.error as error:
                self._fallback(error)
        return descriptors, None

    def knn_match(self, query, map_id, descriptors):
        cpu, gpu = query
        if self.enabled and gpu is not None:
            try:
                return self.bf.knnMatch(gpu, self.references[map_id], k=2)
            except cv2.error as error:
                self._fallback(error)
        return self.bf.knnMatch(cpu, descriptors, k=2)

    def status(self):
        return {'backend': 'opencl' if self.enabled else 'cpu',
                'device': self.device, 'fallback_reason': self.error}
