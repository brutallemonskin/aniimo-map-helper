"""验证 GPU 与 CPU 最近邻一致、跨线程调用以及故障回退。"""
from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cv2
import numpy as np
from feature_matcher import FeatureMatcher


class FeatureChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cv2.setNumThreads(2)
        rng = np.random.default_rng(517)
        cls.train = rng.uniform(0, 255, (512, 128)).astype(np.float32)
        cls.query = cls.train[::5].copy() + rng.normal(0, .1, (103, 128)).astype(np.float32)
        cls.maps = [({'id': 'sample'}, 1, None, cls.train)]
        cls.expected = cv2.BFMatcher().knnMatch(cls.query, cls.train, k=2)

    def assert_matches(self, actual):
        self.assertEqual(len(actual), len(self.expected))
        for actual_pair, expected_pair in zip(actual, self.expected):
            self.assertEqual([m.trainIdx for m in actual_pair], [m.trainIdx for m in expected_pair])
            np.testing.assert_allclose([m.distance for m in actual_pair],
                                       [m.distance for m in expected_pair], rtol=2e-5, atol=2e-4)

    def make(self, mode='auto'):
        with patch.dict(os.environ, ANIIMO_COMPUTE_BACKEND=mode):
            matcher = FeatureMatcher()
        matcher.prepare(self.maps)
        return matcher

    def test_cpu_override(self):
        matcher = self.make('cpu')
        self.assertFalse(matcher.enabled)
        self.assert_matches(matcher.knn_match(matcher.query(self.query), 'sample', self.train))

    def test_opencl_other_thread(self):
        matcher = self.make()
        if not matcher.enabled:
            self.skipTest('当前环境没有 OpenCL 显卡。')
        with ThreadPoolExecutor(max_workers=1) as pool:
            actual = pool.submit(lambda: matcher.knn_match(matcher.query(self.query), 'sample', self.train)).result()
        self.assert_matches(actual)

    def test_opencl_failure_retries_on_cpu(self):
        matcher = self.make('cpu')
        original = matcher.bf
        class FailingGPU:
            def knnMatch(self, query, target, k):
                if isinstance(query, cv2.UMat):
                    raise cv2.error('模拟驱动故障')
                return original.knnMatch(query, target, k=k)
        matcher.bf = FailingGPU()
        matcher.enabled = True
        matcher.references['sample'] = cv2.UMat(self.train)
        actual = matcher.knn_match((self.query, cv2.UMat(self.query)), 'sample', self.train)
        self.assert_matches(actual)
        self.assertEqual(matcher.status()['backend'], 'cpu')
        self.assertFalse(matcher.references)
        self.assertIn('模拟驱动故障', matcher.error)

    def test_no_opencl_falls_back(self):
        with patch('cv2.ocl.useOpenCL', return_value=False):
            matcher = self.make()
        self.assertFalse(matcher.enabled)
        self.assert_matches(matcher.knn_match(matcher.query(self.query), 'sample', self.train))


if __name__ == '__main__':
    unittest.main()
