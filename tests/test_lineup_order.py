import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from tidyTIVI.database import prepare

class LineupOrderTests(unittest.TestCase):
    def test_all_channels_and_categories_follow_the_same_lineup(self):
        for separate,caps in ((True,False),(True,True),(False,False),(False,True)):
            with self.subTest(separate=separate,caps=caps), tempfile.TemporaryDirectory() as directory:
                baseline=Path(directory)/'baseline.db'
                with sqlite3.connect(baseline) as db:
                    db.executescript((Path(__file__).parent/'fixtures/ordering-schema.sql').read_text())
                    def row(table, overrides):
                        values={r[1]:('' if r[2]=='TEXT' else 0) for r in db.execute('PRAGMA table_info('+table+')') if r[3] and r[4] is None and r[1]!='id'}
                        values.update(overrides)
                        return db.execute('INSERT INTO '+table+' ('+','.join(values)+') VALUES ('+','.join('?' for _ in values)+')',list(values.values())).lastrowid
                    pid=row('playlists',{'url':'xc:example.test'})
                    row('channels',{'playlist_id':pid,'name':'Template'})
                def channel(i,name,group):
                    return dict(id=i,name=name,number=str(i*10),group_id=group,group_name='Group '+str(group),provider_name=name,provider_url='https://example.test/'+str(i),logo_url=None,epg=None)
                job=dict(schema='tidytivi.job.v1',target_version='5.3.3',epg_sources=[],accounts=[],vod={'movies':[],'series':[]},settings=dict(uppercase_groups=caps,profile_playlists=separate,names=True,number_prefix=False,provider_vod=False),profiles=[dict(id=1,name='One',display_name='Custom One',group_prefix='US:',channels=[channel(1,'Zulu',1),channel(2,'Alpha',2),channel(3,'Mike',1)]),dict(id=2,name='Two',channels=[channel(4,'Beta',3)])])
                output=Path(directory)/'output.db';prepare(job,baseline,output)
                with sqlite3.connect(output) as db:
                    # TiviMate All channels uses ascending playlist positions.
                    self.assertEqual([r[0] for r in db.execute('SELECT custom_name FROM channels ORDER BY playlist_id,position_in_playlist,id')],['Zulu','Alpha','Mike','Beta'])
                    for pid, in db.execute('SELECT id FROM playlists ORDER BY position'):
                        positions=[r[0] for r in db.execute('SELECT position_in_playlist FROM channels WHERE playlist_id=? ORDER BY position_in_playlist',(pid,))]
                        self.assertEqual(positions,list(range(len(positions))))
                    if separate: self.assertEqual(db.execute('SELECT name FROM playlists ORDER BY position').fetchall(), [('Custom One',),('Two',)])
                    groups=db.execute("SELECT id,name FROM channel_groups").fetchall()
                    if caps: self.assertTrue(all(name==name.upper() for _,name in groups))
                    else: self.assertTrue(any("Group" in name for _,name in groups))
                    gid=db.execute("SELECT id FROM channel_groups WHERE name LIKE '%Group 1'").fetchone()[0]
                    self.assertEqual([r[0] for r in db.execute('SELECT c.custom_name FROM channels c JOIN channel_manual_positions m ON m.channel_id=c.id WHERE m.group_id=? ORDER BY m.position',(gid,))],['Zulu','Mike'])

class GroupCaseTests(unittest.TestCase):
    def test_labels_change_without_changing_profile_or_channel_names(self):
        from tidyTIVI.database import channel_group_name
        from tidyTIVI.exporter import m3u
        job={'settings':{'uppercase_groups':True},'profiles':[{'name':'DirecTV','channels':[{'id':1,'name':'Example Channel','group_name':'En Español','provider_url':'https://example.test/1'}]}]}
        self.assertEqual(channel_group_name(job,'En Español'),'EN ESPAÑOL')
        self.assertIn('group-title="EN ESPAÑOL"',m3u(job,categorized=True).decode())
        self.assertIn('group-title="DIRECTV"',m3u(job).decode())
        self.assertEqual(job['profiles'][0]['name'],'DirecTV')
        self.assertEqual(job['profiles'][0]['channels'][0]['name'],'Example Channel')
        job['settings']['uppercase_groups']=False
        self.assertIn('group-title="En Español"',m3u(job,categorized=True).decode())

class ProfileNamingTests(unittest.TestCase):
    def test_prefix_normalization_preserves_other_colons_and_source_identity(self):
        from tidyTIVI.database import profile_name, profile_group_name
        from tidyTIVI.exporter import m3u
        p={'name':'Sky','display_name':'United Kingdom','group_prefix':'UK:', 'channels':[{'id':1,'group_name':'Sky: Local','provider_url':'https://example.test/1'}]}
        self.assertEqual(profile_name(p),'United Kingdom')
        for original in ['Local','Sky: Local','sky: Local','UK: Local','United Kingdom: Local']:
            self.assertEqual(profile_group_name(p,original),'UK: Local')
        self.assertEqual(profile_group_name(p,'Movies: Classics'),'UK: Movies: Classics')
        job={'settings':{'uppercase_groups':True},'profiles':[p]}
        self.assertIn('group-title="UK: LOCAL"',m3u(job,categorized=True).decode())
        self.assertIn('group-title="UNITED KINGDOM"',m3u(job).decode())
        self.assertEqual(p['name'],'Sky')
        p['group_prefix']=''
        self.assertEqual(profile_group_name(p,'Sky: Local'),'Sky: Local')
