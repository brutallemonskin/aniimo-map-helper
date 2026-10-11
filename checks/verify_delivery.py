"""验证前端版本隔离、旧页面拒绝和人物定位顺序。"""
from pathlib import Path
import json
import sys
import threading
import unittest
from unittest.mock import patch
import urllib.request
import urllib.error
import base64
import cv2

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
from frontend_delivery import versioned_html
from matcher import Matcher
from recognition_timing import recognition, stage


class DeliveryChecks(unittest.TestCase):
    def test_assets_have_unique_build_urls(self):
        source='<head><link href="style.css?v=2"></head><script src="app.js?v=60"></script>'
        page=versioned_html(source,'0.4.3+local.0.0.4')
        self.assertIn('window.ANIIMO_BUILD="0.4.3+local.0.0.4"',page)
        self.assertIn('app.js?v=60&local=0.4.3%2Blocal.0.0.4',page)
        self.assertIn('style.css?v=2&local=0.4.3%2Blocal.0.0.4',page)

    def test_non_map_does_not_search_player(self):
        matcher=Matcher()
        image=np.arange(300*400*3,dtype=np.uint8).reshape(300,400,3)
        with patch.object(matcher.minimap,'extract',return_value=None), \
             patch.object(matcher,'_match',return_value={'status':'unknown','candidates':[]}), \
             patch('matcher.detect_player') as player:
            out=matcher.match(image)
        player.assert_not_called()
        self.assertIsNone(out['player'])
        self.assertIn('performance',out)

    def test_player_projection_respects_viewport(self):
        expected=[102.5,492.8]
        polygon=[[50,80],[650,140],[500,840],[-100,780]]
        result={'candidates':[{'polygon':polygon,'position':None}]}
        Matcher._place_player(result,[.23,.57],[0,0,1,1])
        np.testing.assert_allclose(result['candidates'][0]['position'],expected,atol=1e-8)
        Matcher._place_player(result,[.2+.23*.6,.3+.57*.6],[.2,.3,.8,.9])
        np.testing.assert_allclose(result['candidates'][0]['position'],expected,atol=1e-8)

    def test_nested_timing_does_not_double_count(self):
        @stage('内部')
        def inner():return 1
        @stage('外部')
        def outer():inner()
        @recognition
        def run():outer();return {}
        timing=run()['performance']
        self.assertEqual(set(timing['stages_ms']),{'内部','外部','其他识别处理'})
        self.assertLessEqual(abs(sum(timing['stages_ms'].values())-timing['recognition_ms']),.03)

    def test_http_cache_and_stale_client(self):
        import server
        service=server.LocalHTTPServer(('127.0.0.1',0),server.Handler)
        thread=threading.Thread(target=service.serve_forever,daemon=True);thread.start()
        base='http://127.0.0.1:'+str(service.server_port)
        try:
            request=urllib.request.Request(base+'/',headers={'If-Modified-Since':'Wed, 01 Jan 2099 00:00:00 GMT'})
            with urllib.request.urlopen(request,timeout=5) as response:
                self.assertEqual(response.status,200)
                self.assertIn('no-store',response.headers['Cache-Control'])
                self.assertIn(server.APP_VERSION,response.read().decode('utf-8'))
            request=urllib.request.Request(base+'/api/match',data=json.dumps({'native_session':'stale'}).encode(),
                                           headers={'Content-Type':'application/json'})
            with self.assertRaises(urllib.error.HTTPError) as caught:
                urllib.request.urlopen(request,timeout=5)
            self.assertEqual(caught.exception.code,409)
            self.assertTrue(json.load(caught.exception)['refresh_required'])
            request=urllib.request.Request(base+'/api/native',data=json.dumps({'action':'start','window':'stale'}).encode(),
                                           headers={'Content-Type':'application/json'})
            with self.assertRaises(urllib.error.HTTPError) as caught:
                urllib.request.urlopen(request,timeout=5)
            self.assertEqual(caught.exception.code,409)
            encoded=base64.b64encode(cv2.imencode('.png',np.zeros((32,32,3),np.uint8))[1]).decode()
            with patch.object(server.matcher,'match',return_value={'status':'unknown','candidates':[]}) as matching:
                for slot in (1,2,3,None):
                    request=urllib.request.Request(base+'/api/match',data=json.dumps({'image':encoded,'player_slot':slot}).encode(),
                                                   headers={'Content-Type':'application/json'})
                    with urllib.request.urlopen(request,timeout=5) as response:self.assertEqual(response.status,200)
                    self.assertEqual(matching.call_args.kwargs['player_slot'],slot)
                request=urllib.request.Request(base+'/api/match',data=json.dumps({'image':encoded,'player_slot':4}).encode(),
                                               headers={'Content-Type':'application/json'})
                with self.assertRaises(urllib.error.HTTPError) as invalid:
                    urllib.request.urlopen(request,timeout=5)
                self.assertEqual(invalid.exception.code,400)
            with urllib.request.urlopen(base+'/api/performance',timeout=5) as response:
                self.assertIn('frames',json.load(response))
        finally:
            service.shutdown();service.server_close();thread.join(3)


if __name__=='__main__':unittest.main()
