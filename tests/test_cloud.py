import base64
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs,urlparse
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from tidyTIVI import cloud_auth as auth
from tidyTIVI import drive_upload as drive

class CloudAuthTests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup)
        p=patch.object(auth,'ROOT',Path(t.name));p.start();self.addCleanup(p.stop)
        auth.write('cloud-clients.json',{'dropbox':{'client_id':'dbx'},'drive':{'client_id':'google','client_secret':'private'}})
    def test_both_callbacks_save_authorization_without_returning_secrets(self):
        for provider,file in [('drive','google-drive.json'),('dropbox','dropbox.json')]:
            query=parse_qs(urlparse(auth.begin({'cloud_provider':provider})).query)
            state=query['state'][0];pending=auth.read('cloud-pending.json')[state]
            expected=base64.urlsafe_b64encode(hashlib.sha256(pending['verifier'].encode()).digest()).decode().rstrip('=')
            self.assertEqual(query['code_challenge'],[expected]);self.assertNotIn('client_secret',query)
            with patch.object(auth,'token_request',return_value={'refresh_token':'private-token'}) as req:
                message=auth.finish(state,'code')
                self.assertEqual(req.call_args.args[1]['redirect_uri'],query['redirect_uri'][0])
                self.assertEqual(req.call_args.args[1]['code_verifier'],pending['verifier'])
                self.assertEqual('client_secret' in req.call_args.args[1],provider=='drive')
            self.assertNotIn('private-token',message)
            self.assertEqual(auth.read(file)['refresh_token'],'private-token')
            self.assertEqual((auth.ROOT/file).stat().st_mode&0o777,0o600)
            with self.assertRaisesRegex(ValueError,'already-used'):auth.finish(state,'code')
    def test_failed_or_denied_reconnection_preserves_old_connection(self):
        auth.write('google-drive.json',{'refresh_token':'old'})
        for denied in ('access_denied',''):
            state=parse_qs(urlparse(auth.begin({'cloud_provider':'drive'})).query)['state'][0]
            with patch.object(auth,'token_request',side_effect=ValueError('failed')):
                with self.assertRaises(ValueError):auth.finish(state,'code',denied)
            self.assertEqual(auth.read('google-drive.json')['refresh_token'],'old')
    def test_expired_and_forged_state_never_exchange(self):
        state=parse_qs(urlparse(auth.begin({'cloud_provider':'drive'})).query)['state'][0]
        pending=auth.read('cloud-pending.json');pending[state]['created_at']=0;auth.write('cloud-pending.json',pending)
        with patch.object(auth,'token_request') as req:
            for value in (state,'unknown',''):
                with self.assertRaises(ValueError):auth.finish(value,'code')
            req.assert_not_called()
    def test_localhost_callback_is_allowed_but_private_http_is_not(self):
        self.assertEqual(auth.validate_redirect('http://127.0.0.1:19191'+auth.CALLBACK_PATH),'http://127.0.0.1:19191'+auth.CALLBACK_PATH)
        for url in ('http://10.1.1.107:9191','https://10.1.1.107','ftp://localhost','https://user:pass@example.com'):
            with self.assertRaises(ValueError):auth.validate_redirect(url+auth.CALLBACK_PATH)

class Response(io.BytesIO):
    def __init__(self,data,status=200,headers=None):
        super().__init__(json.dumps(data).encode());self.status=status;self.headers=headers or {}

class DriveUploadTests(unittest.TestCase):
    def test_update_keeps_file_identity_and_verifies_before_sharing(self):
        blob=b'private bundle';seen=[]
        replies=[{'files':[{'id':'existing'}]},None,{'id':'existing','size':str(len(blob)),'md5Checksum':hashlib.md5(blob).hexdigest()},
                 {'permissions':[]},{'id':'permission'},{'webContentLink':'https://drive.google.com/uc?id=existing&export=download&resourcekey=key'}]
        def respond(request,**kwargs):
            seen.append(request);data=replies.pop(0)
            return Response(data,headers={'Location':'https://www.googleapis.com/upload/session'}) if data is None else Response(data)
        with tempfile.TemporaryDirectory() as folder,patch.object(drive,'drive_token',return_value='token'),patch.object(drive,'urlopen',side_effect=respond):
            p=Path(folder)/'bundle.zip';p.write_bytes(blob);result=drive.upload_bundle(p,{})
        self.assertEqual(seen[1].method,'PATCH');self.assertIn('/existing?',seen[1].full_url)
        self.assertEqual(seen[2].data,blob)
        self.assertEqual(json.loads(seen[4].data),{'type':'anyone','role':'reader','allowFileDiscovery':False})
        self.assertEqual(result['file_id'],'existing');self.assertIn('resourcekey=key',result['download_url'])
    def test_bad_hash_does_not_create_share(self):
        replies=[Response({'files':[]}),Response({},headers={'Location':'https://www.googleapis.com/upload/session'}),Response({'id':'new','size':'4','md5Checksum':'wrong'})]
        with tempfile.TemporaryDirectory() as folder,patch.object(drive,'drive_token',return_value='token'),patch.object(drive,'urlopen',side_effect=replies) as req:
            p=Path(folder)/'bundle.zip';p.write_bytes(b'test')
            with self.assertRaisesRegex(ValueError,'verification'):drive.upload_bundle(p,{})
            self.assertEqual(req.call_count,3)
