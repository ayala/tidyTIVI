import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from dropbox_upload import upload_bundle

class DropboxTests(unittest.TestCase):
    def test_overwrite_verify_and_reuse_link(self):
        data=b'private test bundle'
        digest=hashlib.sha256(hashlib.sha256(data).digest()).hexdigest()
        requests=[]
        def response(request, **kwargs):
            requests.append(request)
            result=({'content_hash':digest} if request.full_url.endswith('/files/upload') else
                    {'links':[{'url':'https://www.dropbox.com/scl/fi/example/bundle.zip?rlkey=test&dl=0'}]})
            return io.BytesIO(json.dumps(result).encode())
        with tempfile.TemporaryDirectory() as folder, patch('dropbox_upload.urlopen',side_effect=response):
            path=Path(folder)/'bundle.zip';path.write_bytes(data)
            result=upload_bundle(path,{'dropbox_access_token':'test'})
        self.assertEqual(len(requests),2)
        self.assertEqual(json.loads(requests[0].get_header('Dropbox-api-arg'))['mode'],'overwrite')
        self.assertIn('dl=1',result['download_url'])
        self.assertIn('rlkey=test',result['download_url'])

    def test_mismatched_upload_stops_before_sharing(self):
        with tempfile.TemporaryDirectory() as folder, patch('dropbox_upload.urlopen',return_value=io.BytesIO(b'{"content_hash":"incorrect"}')) as call:
            path=Path(folder)/'bundle.zip';path.write_bytes(b'test')
            with self.assertRaisesRegex(ValueError,'verification failed'):
                upload_bundle(path,{'dropbox_access_token':'test'})
            self.assertEqual(call.call_count,1)
