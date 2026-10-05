import shutil
import sqlite3
import tempfile
import unittest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tidyTIVI.merge import merge_databases, MergeError


class MergeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.receiver = self.root/'receiver.db'
        self.incoming = self.root/'incoming.db'
        self.output = self.root/'merged.db'
        with sqlite3.connect(self.receiver) as db:
            db.executescript((Path(__file__).parent/'fixtures/ordering-schema.sql').read_text())
            self.pid=self.row(db,'playlists',dict(name='US',url='file:///sdcard/Download/tidyTIVI/current/lineup-1.m3u',is_enabled=0))
            self.gid=self.row(db,'channel_groups',dict(playlist_id=self.pid,name='Local',is_custom=1))
            self.row(db,'channel_group_options',dict(type=4,playlist_id=self.pid,group_id=self.gid,is_visible=0))
            self.cid=self.row(db,'channels',dict(playlist_id=self.pid,name='tidytivi-1',custom_name='Old',url='https://example.test/1',original_group_id=self.gid,is_favorite=1,watch_time=123,last_turn_on_time=456,audio_offset=25,last_group_playlist_id=self.pid))
            self.row(db,'channel_group_links',dict(channel_id=self.cid,group_id=self.gid))
            self.row(db,'movies',dict(playlist_id=self.pid,name='Movie',is_favorite=1,last_played_position_ms=10000))
        shutil.copy2(self.receiver,self.incoming)
        with sqlite3.connect(self.incoming) as db:
            db.execute("UPDATE channels SET custom_name='New',position_in_playlist=5,is_favorite=0,watch_time=0,last_turn_on_time=0,audio_offset=NULL")
            db.execute("UPDATE channel_groups SET name='US: Local'")
            db.execute('UPDATE playlists SET is_enabled=1')

    def row(self,db,table,values):
        required={r[1]:('' if r[2]=='TEXT' else 0) for r in db.execute('PRAGMA table_info('+table+')') if r[3] and r[4] is None and r[1]!='id'}
        required.update(values)
        return db.execute('INSERT INTO '+table+' ('+','.join(required)+') VALUES ('+','.join('?' for _ in required)+')',list(required.values())).lastrowid

    def test_changes_curation_preserves_personal_state_and_ids(self):
        report=merge_databases(self.receiver,self.incoming,self.output)
        self.assertEqual(report['updated_channels'],1)
        with sqlite3.connect(self.output) as db:
            self.assertEqual(db.execute('SELECT id,custom_name,position_in_playlist,is_favorite,watch_time,last_turn_on_time,audio_offset FROM channels').fetchone(),(self.cid,'New',5,1,123,456,25))
            self.assertEqual(db.execute('SELECT is_enabled FROM playlists').fetchone(),(0,))
            self.assertEqual(db.execute('SELECT id,name FROM channel_groups').fetchone(),(self.gid,'US: Local'))
            self.assertEqual(db.execute('SELECT is_visible FROM channel_group_options').fetchone(),(0,))
            self.assertEqual(db.execute('SELECT is_favorite,last_played_position_ms FROM movies').fetchone(),(1,10000))
        with sqlite3.connect(self.receiver) as db:
            self.assertEqual(db.execute('SELECT custom_name FROM channels').fetchone(),('Old',))

    def test_rejects_unknown_profile_without_creating_output(self):
        with sqlite3.connect(self.incoming) as db:db.execute("UPDATE playlists SET url='file:///sdcard/Download/tidyTIVI/current/lineup-999.m3u'")
        with self.assertRaises(MergeError):merge_databases(self.receiver,self.incoming,self.output)
        self.assertFalse(self.output.exists())

    def test_duplicate_channel_rolls_back_and_removes_output(self):
        with sqlite3.connect(self.incoming) as db:self.row(db,'channels',dict(playlist_id=self.pid,name='tidytivi-1'))
        with self.assertRaises(MergeError):merge_databases(self.receiver,self.incoming,self.output)
        self.assertFalse(self.output.exists())

    def test_retirement_preserves_favorite_and_identity(self):
        with sqlite3.connect(self.receiver) as db:self.row(db,'channels',dict(playlist_id=self.pid,name='tidytivi-2',is_favorite=1,last_group_playlist_id=self.pid))
        report=merge_databases(self.receiver,self.incoming,self.output)
        self.assertEqual(report['retired_channels'],1)
        with sqlite3.connect(self.output) as db:
            row=db.execute("SELECT is_favorite,deleted_time FROM channels WHERE name='tidytivi-2'").fetchone()
            self.assertEqual(row[0],1);self.assertIsNotNone(row[1])

    def test_personal_group_membership_survives(self):
        with sqlite3.connect(self.receiver) as db:
            gid=self.row(db,'channel_groups',dict(playlist_id=self.pid,name='My picks',is_custom=1))
            self.row(db,'channel_group_links',dict(channel_id=self.cid,group_id=gid))
        # Existing category still has the original name, making this mapping explicit.
        with sqlite3.connect(self.incoming) as db:db.execute("UPDATE channel_groups SET name='Local'")
        merge_databases(self.receiver,self.incoming,self.output)
        with sqlite3.connect(self.output) as db:self.assertIsNotNone(db.execute('SELECT 1 FROM channel_group_links WHERE channel_id=? AND group_id=?',(self.cid,gid)).fetchone())

    def test_ambiguous_group_rename_refused(self):
        with sqlite3.connect(self.incoming) as db:db.execute("UPDATE channel_groups SET name='Unrelated new name'")
        with sqlite3.connect(self.receiver) as db:
            gid=self.row(db,'channel_groups',dict(playlist_id=self.pid,name='Personal duplicate',is_custom=1))
            self.row(db,'channel_group_links',dict(channel_id=self.cid,group_id=gid))
        with self.assertRaises(MergeError):merge_databases(self.receiver,self.incoming,self.output)
        self.assertFalse(self.output.exists())

    def test_refuses_overwriting_input(self):
        with self.assertRaises(MergeError):merge_databases(self.receiver,self.incoming,self.receiver)

    def test_prefix_change_preserves_group_identity_with_personal_duplicate(self):
        with sqlite3.connect(self.receiver) as db:
            gid=self.row(db,'channel_groups',dict(playlist_id=self.pid,name='My picks',is_custom=1))
            self.row(db,'channel_group_links',dict(channel_id=self.cid,group_id=gid))
        merge_databases(self.receiver,self.incoming,self.output)
        with sqlite3.connect(self.output) as db:
            self.assertEqual(db.execute('SELECT name FROM channel_groups WHERE id=?',(self.gid,)).fetchone(),('US: Local',))
            self.assertEqual(db.execute('SELECT name FROM channel_groups WHERE id=?',(gid,)).fetchone(),('My picks',))
