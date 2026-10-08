import io
import json
import sqlite3
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse
from tidyTIVI.master import collect_master, add_masters

class MasterTests(unittest.TestCase):
    def test_complete_recipient_catalogue_disabled_and_uncurated(self):
        account=dict(id=9,name='Provider',server_url='https://example.test',username='recipient',password='new-account')
        responses={'get_live_categories':[dict(category_id='8',category_name='Provider Mixed Case')],
                   'get_live_streams':[dict(stream_id=11,name='Provider One',category_id='8'),dict(stream_id=99,name='Not in Dispatcharr',category_id='8',tv_archive=1,tv_archive_duration=3)]}
        def fetch(request,**kwargs):
            q=parse_qs(urlparse(request.full_url).query)
            self.assertEqual(q['username'],['recipient']);self.assertEqual(q['password'],['new-account'])
            return io.BytesIO(json.dumps(responses[q['action'][0]]).encode())
        with patch('tidyTIVI.master.urlopen',side_effect=fetch):masters=collect_master([account])
        db=sqlite3.connect(':memory:');db.executescript((Path(__file__).parent/'fixtures/ordering-schema.sql').read_text())
        def insert(db,table,values):
            defaults={r[1]:('' if r[2]=='TEXT' else 0) for r in db.execute('pragma table_info('+table+')') if r[3] and r[4] is None and r[1]!='id'};defaults.update(values)
            return db.execute('INSERT INTO '+table+' ('+','.join(defaults)+') VALUES ('+','.join('?' for _ in defaults)+')',list(defaults.values())).lastrowid
        report=add_masters(db,dict(accounts=[account],provider_masters=masters,settings={'uppercase_groups':True}),{}, {},insert)
        self.assertEqual(report[0]['channels'],2)
        self.assertEqual(db.execute('select is_enabled,include_tv_channels,include_vod,auto_update,is_visible_in_all_channels from playlists').fetchone(),(0,1,0,1,0))
        self.assertEqual(db.execute('select name,is_custom,xc_id from channel_groups').fetchone(),('Provider Mixed Case',0,8))
        self.assertEqual(db.execute('select xc_id,name from channels order by xc_id').fetchall(),[(11,'Provider One'),(99,'Not in Dispatcharr')])
        self.assertEqual(db.execute('select count(*) from channel_group_links').fetchone()[0],2)
        self.assertIn('/recipient/new-account/',db.execute('select url from channels limit 1').fetchone()[0])
        self.assertEqual(db.execute('pragma foreign_key_check').fetchall(),[])

    def test_failed_catalogue_does_not_leak_credentials(self):
        a=dict(id=1,name='Provider',server_url='https://example.test',username='secret-user',password='secret-pass')
        with patch('tidyTIVI.master.urlopen',side_effect=Exception('secret-pass')):
            with self.assertRaises(ValueError) as error:collect_master([a])
        self.assertNotIn('secret-pass',str(error.exception))
