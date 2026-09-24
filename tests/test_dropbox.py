import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from dropbox_upload import upload_bundle

class DropboxTests(unittest.TestCase):
    def setUp(self):
        self.token=patch("dropbox_upload.access_token",return_value="test")
        self.token.start();self.addCleanup(self.token.stop)

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

class DropboxConnectionTests(unittest.TestCase):
    def setUp(self):
        self.folder=tempfile.TemporaryDirectory();self.addCleanup(self.folder.cleanup)
        self.auth=Path(self.folder.name)/'dropbox.json'
        p=patch('dropbox_upload.AUTH_FILE',self.auth);p.start();self.addCleanup(p.stop)

    def test_pkce_connection_needs_no_secret_and_survives_settings_save(self):
        import dropbox_upload as d
        from urllib.parse import urlparse,parse_qs
        settings={'dropbox_app_key':'example-key'}
        message=d.connect(settings)
        query=parse_qs(urlparse(message.splitlines()[1]).query)
        auth=json.loads(self.auth.read_text());verifier=auth['pending']['verifier']
        self.assertEqual(query['code_challenge_method'],['S256'])
        import base64
        self.assertEqual(query['code_challenge'],[base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip('=')])
        self.assertEqual(self.auth.stat().st_mode & 0o777,0o600)
        with patch('dropbox_upload.token_request',return_value={'refresh_token':'private-refresh'}) as token, patch('dropbox_upload.clear_code') as clear:
            self.assertIn('connected',d.connect(dict(settings,dropbox_auth_code='one-time-code')))
            self.assertEqual(token.call_args.args[0]['code_verifier'],verifier)
            self.assertNotIn('client_secret',token.call_args.args[0]);clear.assert_called_once()
        self.assertNotIn('pending',json.loads(self.auth.read_text()))
        with patch('dropbox_upload.token_request',return_value={'access_token':'fresh'}) as token:
            self.assertEqual(d.access_token({}),'fresh')
            self.assertEqual(token.call_args.args[0]['client_id'],'example-key')
            self.assertNotIn('client_secret',token.call_args.args[0])
        self.assertNotIn('private-refresh',d.connection_status({}))

    def test_legacy_connection_is_preserved(self):
        import dropbox_upload as d
        old={'dropbox_app_key':'key','dropbox_app_secret':'secret','dropbox_refresh_token':'refresh'}
        d.migrate_auth(old)
        with patch('dropbox_upload.token_request',return_value={'access_token':'fresh'}) as token:
            d.access_token({})
            self.assertEqual(token.call_args.args[0]['client_secret'],'secret')

    def test_changed_app_key_rejects_code_without_replacing_connection(self):
        import dropbox_upload as d
        d.connect({'dropbox_app_key':'key'})
        before=self.auth.read_bytes()
        with self.assertRaisesRegex(ValueError,'app key changed'):
            d.connect({'dropbox_app_key':'different','dropbox_auth_code':'code'})
        self.assertEqual(before,self.auth.read_bytes())

    def test_failed_reconnection_preserves_previous_credentials(self):
        import dropbox_upload as d
        d.save_auth({'app_key':'old','refresh_token':'working'})
        d.connect({'dropbox_app_key':'new'})
        with patch('dropbox_upload.token_request',side_effect=ValueError('failed')), patch('dropbox_upload.clear_code'):
            with self.assertRaises(ValueError):d.connect({'dropbox_app_key':'new','dropbox_auth_code':'bad'})
        self.assertEqual(d.read_auth()['refresh_token'],'working')

    def test_shared_key_and_replay_protection(self):
        import dropbox_upload as d
        with patch.object(d,'PUBLISHER_APP_KEY','publisher'):
            self.assertIn('client_id=publisher',d.connect({},finish=False))
        with patch.object(d,'clear_code'), patch.object(d,'token_request',return_value={'refresh_token':'saved'}) as request:
            d.connect({'dropbox_auth_code':'code'},finish=True)
            with self.assertRaisesRegex(ValueError,'already used'):
                d.connect({'dropbox_auth_code':'code'},finish=True)
            self.assertEqual(request.call_count,1)
        self.assertEqual(d.read_auth()['app_key'],'publisher')

    def test_cancel_and_expiry_keep_existing_account(self):
        import dropbox_upload as d
        d.save_auth({'app_key':'old','refresh_token':'keep'})
        with patch.object(d,'PUBLISHER_APP_KEY','publisher'), patch.object(d,'clear_code'):
            d.connect({},finish=False)
            auth=d.read_auth();auth['pending']['created_at']=0;d.save_auth(auth)
            with patch.object(d,'token_request') as request:
                with self.assertRaisesRegex(ValueError,'expired'):
                    d.connect({'dropbox_auth_code':'code'},finish=True)
                request.assert_not_called()
            d.cancel_connection({})
        self.assertEqual(d.read_auth(),{'app_key':'old','refresh_token':'keep'})

    def test_drive_migration_disables_upload(self):
        import dropbox_upload as d
        migrated=d.prepare_settings({'cloud_provider':'drive','cloud_upload':True,'profile_1':True})
        self.assertFalse(migrated['cloud_upload'])
        self.assertEqual(migrated['cloud_provider'],'dropbox')
        self.assertTrue(migrated['profile_1'])
        self.assertTrue(d.prepare_settings({'cloud_provider':'dropbox','cloud_upload':True})['cloud_upload'])
