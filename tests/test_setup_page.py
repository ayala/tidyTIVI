import tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from urllib.parse import urlparse,parse_qs
import dropbox_upload as d

class SetupLinkTests(unittest.TestCase):
    def test_page_url_resumes_pending_pkce_without_disclosing_secrets(self):
        with tempfile.TemporaryDirectory() as root,patch.object(d,'AUTH_FILE',Path(root)/'auth.json'):
            d.save_auth({'refresh_token':'private-refresh','app_key':'old'})
            d.connect({},finish=False)
            auth=d.read_auth();url=d.authorization_url();query=parse_qs(urlparse(url).query)
            self.assertEqual(urlparse(url).netloc,'www.dropbox.com')
            self.assertEqual(query['code_challenge_method'],['S256'])
            self.assertNotIn(auth['pending']['verifier'],url)
            self.assertNotIn('private-refresh',url)
            self.assertEqual(d.authorization_url(),url)
            auth['pending']['created_at']=0;d.save_auth(auth)
            self.assertIsNone(d.authorization_url())
            self.assertEqual(d.read_auth()['refresh_token'],'private-refresh')
