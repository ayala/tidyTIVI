import tempfile,unittest,zipfile
from pathlib import Path
from unittest.mock import patch
from logos import build_logo_pack

class LogosTests(unittest.TestCase):
    def test_same_provider_name_keeps_distinct_assigned_logos(self):
        a=b'\x89PNG\r\n\x1a\nA'; b=b'\x89PNG\r\n\x1a\nB'
        class Response:
            def __init__(self,data):self.data=data
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def read(self,*args):return self.data
        p={'channels':[{'id':10,'provider_name':'Same','logo_url':'https://example.test/a'},
                       {'id':11,'provider_name':'Same','logo_url':'https://example.test/b'}]}
        with tempfile.TemporaryDirectory() as temp,patch('logos.urlopen',side_effect=lambda req,**kw:Response(a if req.full_url.endswith('/a') else b)):
            out=Path(temp)/'logos.zip';self.assertEqual(build_logo_pack(p,out),2)
            with zipfile.ZipFile(out) as z:
                self.assertEqual(z.read('logos/tidytivi-10.png'),a)
                self.assertEqual(z.read('logos/tidytivi-11.png'),b)
