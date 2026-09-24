import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from tidyTIVI.database import prepare

class LineupOrderTests(unittest.TestCase):
    def test_all_channels_and_categories_follow_the_same_lineup(self):
        for separate in (True,False):
            with self.subTest(separate=separate), tempfile.TemporaryDirectory() as directory:
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
                job=dict(schema='tidytivi.job.v1',target_version='5.3.3',epg_sources=[],accounts=[],vod={'movies':[],'series':[]},settings=dict(profile_playlists=separate,names=True,number_prefix=False,provider_vod=False),profiles=[dict(id=1,name='One',channels=[channel(1,'Zulu',1),channel(2,'Alpha',2),channel(3,'Mike',1)]),dict(id=2,name='Two',channels=[channel(4,'Beta',3)])])
                output=Path(directory)/'output.db';prepare(job,baseline,output)
                with sqlite3.connect(output) as db:
                    # TiviMate All channels uses ascending playlist positions.
                    self.assertEqual([r[0] for r in db.execute('SELECT custom_name FROM channels ORDER BY playlist_id,position_in_playlist,id')],['Zulu','Alpha','Mike','Beta'])
                    for pid, in db.execute('SELECT id FROM playlists ORDER BY position'):
                        positions=[r[0] for r in db.execute('SELECT position_in_playlist FROM channels WHERE playlist_id=? ORDER BY position_in_playlist',(pid,))]
                        self.assertEqual(positions,list(range(len(positions))))
                    gid=db.execute("SELECT id FROM channel_groups WHERE name LIKE '%Group 1'").fetchone()[0]
                    self.assertEqual([r[0] for r in db.execute('SELECT c.custom_name FROM channels c JOIN channel_manual_positions m ON m.channel_id=c.id WHERE m.group_id=? ORDER BY m.position',(gid,))],['Zulu','Mike'])
