"""EPG bindings must survive multiple profiles, shared sources and reused XMLTV IDs."""
import sqlite3
import tempfile
import unittest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tidyTIVI.database import prepare

class EpgProfilesTests(unittest.TestCase):
    def test_single_and_multiple_profiles_preserve_source_and_channel_pairs(self):
        with tempfile.TemporaryDirectory() as directory:
            base=Path(directory)/'baseline.db'
            with sqlite3.connect(base) as db:
                db.executescript((Path(__file__).parent/'fixtures/ordering-schema.sql').read_text())
                def row(table, overrides):
                    v={r[1]:('' if r[2]=='TEXT' else 0) for r in db.execute('PRAGMA table_info('+table+')') if r[3] and r[4] is None and r[1]!='id'}
                    v.update(overrides)
                    return db.execute('INSERT INTO '+table+' ('+','.join(v)+') VALUES ('+','.join('?' for _ in v)+')',list(v.values())).lastrowid
                pid=row('playlists',{'url':'xc:example.test'})
                row('channels',{'playlist_id':pid,'name':'Template'})
            def ch(i, source):
                return dict(id=i,name='Channel '+str(i),number=str(i),group_id=1,group_name='Local',provider_name='Provider',provider_url='https://example.test/'+str(i),logo_url=None,epg={'source_id':source,'xmltv_id':'shared-id'})
            sources=[{'id':i,'name':name,'url':'https://example.test/'+name+'.xml'} for i,name in [(7,'USA'),(13,'UK'),(2,'Shared')]]
            profiles=[{'id':1,'name':'DirecTV','channels':[ch(1,7),ch(2,2)]},{'id':4,'name':'Sky','channels':[ch(3,13),ch(2,2)]}]
            for selected,separate in [(profiles[:1],True),(profiles,True),(profiles,False)]:
                output=Path(directory)/('out'+str(len(selected))+str(separate)+'.db')
                job=dict(schema='tidytivi.job.v1',target_version='5.3.3',profiles=selected,epg_sources=sources,accounts=[],vod={'movies':[],'series':[]},settings={'profile_playlists':separate,'names':True,'number_prefix':False,'provider_vod':False})
                prepare(job,base,output)
                with sqlite3.connect(output) as db:
                    pairs=db.execute('SELECT c.name,c.tvg_id,c.user_tvg_id,s.name FROM channels c JOIN tvg_sources s ON s.id=c.user_tvg_source_id ORDER BY c.id').fetchall()
                    expected=[('tidytivi-'+str(c['id']),'shared-id','shared-id',next(s['name'] for s in sources if s['id']==c['epg']['source_id'])) for p in selected for c in p['channels']]
                    self.assertEqual(pairs,expected)
                    missing=db.execute('SELECT count(*) FROM channels c WHERE NOT EXISTS (SELECT 1 FROM playlist_tvg_source_assignments a WHERE a.playlist_id=c.playlist_id AND a.tvg_source_id=c.user_tvg_source_id)').fetchone()[0]
                    self.assertEqual(missing,0)
                    if separate and len(selected)==2:
                        links=db.execute('SELECT p.name,s.name FROM playlist_tvg_source_assignments a JOIN playlists p ON p.id=a.playlist_id JOIN tvg_sources s ON s.id=a.tvg_source_id').fetchall()
                        self.assertEqual(set(links),{('DirecTV','USA'),('DirecTV','Shared'),('Sky','UK'),('Sky','Shared')})
