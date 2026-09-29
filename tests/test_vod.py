import io
import json
import sqlite3
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse
from tidyTIVI.vod import collect_vod, add_vod


class ProviderVodTests(unittest.TestCase):
    def test_complete_catalogue_uses_recipient_account_and_provider_ids(self):
        actions=[]
        rows={'get_vod_categories':[{'category_id':'51','category_name':'Provider Movies'}],
              'get_series_categories':[{'category_id':'72','category_name':'Provider Shows'}],
              'get_vod_streams':[{'stream_id':1,'name':'Original title','category_id':'51'},
                                 {'stream_id':2,'name':'New movie','category_id':'51'}],
              'get_series':[{'series_id':3,'name':'Original show','category_id':'72'}]}
        def fetch(request, **kwargs):
            query=parse_qs(urlparse(request.full_url).query)
            self.assertEqual(query['username'],['recipient'])
            self.assertEqual(query['password'],['replacement'])
            action=query['action'][0];actions.append(action)
            return io.BytesIO(json.dumps(rows[action]).encode())
        account=dict(id=9,name='Selected',server_url='https://example.test',username='recipient',password='replacement')
        with patch('urllib.request.urlopen',side_effect=fetch):
            vod=collect_vod([account])
        self.assertEqual(len(actions),4)
        self.assertEqual([x['name'] for x in vod['movies']],['Original title','New movie'])
        self.assertEqual(vod['series'][0]['category_id'],'72')
        self.assertEqual(vod['movies'][0]['category'],'Provider Movies')
        db=sqlite3.connect(':memory:')
        db.executescript((Path(__file__).parent/'fixtures/ordering-schema.sql').read_text())
        def insert(db, table, values):
            defaults={r[1]:('' if r[2]=='TEXT' else 0) for r in db.execute('PRAGMA table_info('+table+')') if r[3] and r[4] is None and r[1]!='id'}
            defaults.update(values)
            return db.execute('INSERT INTO '+table+' ('+','.join(defaults)+') VALUES ('+','.join('?' for _ in defaults)+')',list(defaults.values())).lastrowid
        add_vod(db,dict(accounts=[account],vod=vod,profiles=[],settings={}),{},insert)
        self.assertEqual(db.execute('SELECT xc_id,name FROM movie_categories').fetchall(),[(51,'Provider Movies')])
        self.assertEqual(db.execute('SELECT auto_update,are_new_movie_groups_visible,are_new_series_groups_visible,include_tv_channels FROM playlists').fetchone(),(1,1,1,0))
        self.assertEqual(db.execute('SELECT count(*) FROM movies').fetchone()[0],2)

    def test_account_failure_stops_incomplete_export_without_exposing_credentials(self):
        account=dict(id=9,name='Selected',server_url='https://example.test',username='private-user',password='private-password')
        with patch('urllib.request.urlopen',side_effect=ValueError('private-password')):
            with self.assertRaisesRegex(ValueError,'complete XC VOD catalogue') as error:
                collect_vod([account])
        self.assertNotIn('private-password',str(error.exception))
