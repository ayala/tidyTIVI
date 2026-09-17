import io,json,unittest
from unittest.mock import patch
from accounts import apply_overrides

class OverrideTests(unittest.TestCase):
    def job(self):return {'accounts':[{'id':3,'name':'Example','server_url':'https://provider.test','username':'source','password':'source-password'}],
        'profiles':[{'channels':[{'account_id':3,'xc_id':123,'name':'Channel','provider_url':'https://provider.test/live/source/source-password/123.ts'}]}], 'vod':{'movies':[],'series':[]}}
    def test_only_export_credentials_change(self):
        job=self.job()
        with patch('accounts.urlopen',return_value=io.BytesIO(json.dumps([{'stream_id':123}]).encode())):
            apply_overrides(job,{'override_3':True,'export_username_3':'recipient','export_password_3':'new-password'})
        self.assertEqual(job['profiles'][0]['channels'][0]['provider_url'],'https://provider.test/live/recipient/new-password/123.ts')
    def test_missing_ids_stop_export(self):
        job=self.job()
        with patch('accounts.urlopen',return_value=io.BytesIO(b'[]')):
            with self.assertRaisesRegex(ValueError,'lacks 1'):apply_overrides(job,{'override_3':True,'export_username_3':'recipient','export_password_3':'new-password'})
        self.assertEqual(job['accounts'][0]['username'],'source')

    def test_vod_is_validated_before_credentials_are_replaced(self):
        job=self.job();job['vod']['movies']=[{'account_id':3,'xc_id':456}]
        with patch('accounts.urlopen',side_effect=[io.BytesIO(b'[{"stream_id":123}]'),io.BytesIO(b'[]')]):
            with self.assertRaisesRegex(ValueError,'curated movies IDs'):
                apply_overrides(job,{'override_3':True,'export_username_3':'recipient','export_password_3':'new-password'})
        self.assertEqual(job['accounts'][0]['username'],'source')

class CatchupTests(unittest.TestCase):
    def test_archive_flag_and_days_are_both_required(self):
        from accounts import catchup_hours
        for props,want in [({'tv_archive':'1','tv_archive_duration':'3'},72),
                           ({'tv_archive':1,'tv_archive_duration':1},24),
                           ({'tv_archive':0,'tv_archive_duration':7},0),
                           ({'tv_archive':1,'tv_archive_duration':None},0),
                           ({'tv_archive':1,'tv_archive_duration':-1},0),({},0)]:
            with self.subTest(props=props):self.assertEqual(catchup_hours(props),want)

    def test_replacement_account_controls_archive_entitlement(self):
        for flag,hours in [('0',0),('1',48)]:
            job=OverrideTests().job();job['profiles'][0]['channels'][0]['catchup_hours']=72
            rows=[{'stream_id':123,'tv_archive':flag,'tv_archive_duration':'2'}]
            with patch('accounts.urlopen',return_value=io.BytesIO(json.dumps(rows).encode())):
                apply_overrides(job,{'override_3':True,'export_username_3':'recipient','export_password_3':'new-password'})
            self.assertEqual(job['profiles'][0]['channels'][0]['catchup_hours'],hours)
