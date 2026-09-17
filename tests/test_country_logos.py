import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from logo_bundle import build_country_logos

class CountryLogoTests(unittest.TestCase):
    def test_complete_folder_plus_exact_aliases(self):
        png=b'\x89PNG\r\n\x1a\nimage'
        job={'logo_repository':{'repository':'test/repo','folders':[{'profile':'DirecTV','country':'us','directory':'logos/us/directv'}]},
             'profiles':[{'name':'DirecTV','channels':[{'id':7,'logo_url':'https://raw.githubusercontent.com/test/repo/main/logos/us/directv/used.png'}]}]}
        def get(url):
            if url=='https://api.github.com/repos/test/repo':return json.dumps({'default_branch':'main'}).encode()
            if '/git/trees/' in url:return json.dumps({'tree':[{'type':'blob','path':'logos/us/directv/used.png'},{'type':'blob','path':'logos/us/directv/not-assigned.png'},{'type':'blob','path':'logos/es/other.png'}]}).encode()
            return png
        with tempfile.TemporaryDirectory() as root,patch('logo_bundle.download',side_effect=get):
            report=build_country_logos(job,root)
            self.assertEqual(report,{'country_files':2,'matched_files':1,'countries':['us'],'missing_assigned_logos':[]})
            self.assertTrue((Path(root)/'us/directv/not-assigned.png').is_file())
            self.assertEqual((Path(root)/'_matched/tidytivi-7.png').read_bytes(),png)
            self.assertFalse((Path(root)/'es').exists())

    def test_unavailable_external_assignment_does_not_drop_channel_or_country_files(self):
        job={'logo_repository':{'repository':'test/repo','folders':[{'profile':'Sky','country':'uk','directory':'logos/uk/sky'}]},'profiles':[{'name':'Sky','channels':[{'id':8,'name':'Example','logo_url':'https://unavailable.example/logo.png'}]}]}
        def get(url):
            if url.endswith('/test/repo'):return b'{"default_branch":"main"}'
            if '/git/trees/' in url:return b'{"tree":[{"type":"blob","path":"logos/uk/sky/original.png"}]}'
            if 'unavailable.example' in url:raise ValueError('Unavailable')
            return b'original image'
        with tempfile.TemporaryDirectory() as root,patch('logo_bundle.download',side_effect=get):
            result=build_country_logos(job,root)
            self.assertEqual(result['country_files'],1)
            self.assertEqual(result['matched_files'],0)
            self.assertEqual(result['missing_assigned_logos'][0]['id'],8)
            self.assertEqual(len(job['profiles'][0]['channels']),1)
