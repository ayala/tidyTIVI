"""One native backup, complete country logos and a companion update bundle."""
import copy
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import sqlite3
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from .database import prepare, channel_group_name, profile_name, profile_group_name
from .logo_bundle import build_country_logos
from .tmb_codec import decode, encode, load_seed

RECEIVER_ROOT='/sdcard/Download/tidyTIVI/current'


def write_private(path, data):
    with Path(path).open('wb') as handle:
        os.chmod(path,0o600);handle.write(data)


def m3u(job, profiles=None, categorized=False):
    def attr(value):return str(value).replace('"',"'").replace('\r',' ').replace('\n',' ')
    lines=['#EXTM3U']
    for profile in (profiles or job['profiles']):
        for channel in profile['channels']:
            guide=channel.get('epg') or {}
            catchup=(' catchup="xc" catchup-days="'+str(channel['catchup_hours']//24)+'"') if channel.get('catchup_hours',0)>0 else ''
            lines.append('#EXTINF:-1'+catchup+' tvg-id="'+attr(guide.get('xmltv_id',''))+'" tvg-logo="'+attr(channel.get('logo_url') or '')+'" group-title="'+attr(channel_group_name(job,profile_group_name(profile,channel['group_name']) if categorized else profile_name(profile)))+'",tidytivi-'+str(channel['id']))
            url=channel['provider_url']
            if '\n' in url or '\r' in url:raise ValueError('Invalid stream URL.')
            lines.append(url)
    return ('\n'.join(lines)+'\n').encode()


def export_backups(job, settings):
    seed=load_seed(settings.get('codec_seed_path') or '/data/tidytivi/codec-seed.json')
    template=decode(Path(settings.get('template_path') or '/data/tidytivi/template.tmb').read_bytes(),seed)
    directory=Path(settings.get('export_directory') or '/data/exports/tidytivi')
    if not directory.is_absolute():raise ValueError('Export directory must be an absolute path.')
    directory.mkdir(parents=True,exist_ok=True,mode=0o700)
    staging=Path(tempfile.mkdtemp(prefix='.building-',dir=directory))
    destination=directory/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+job['id'])
    try:
        with tempfile.TemporaryDirectory(prefix='tidytivi-') as scratch,zipfile.ZipFile(io.BytesIO(template)) as archive:
            scratch=Path(scratch);baseline=scratch/'baseline.db';baseline.write_bytes(archive.read('TvPlayer.db'))
            database=scratch/'combined.db';report=prepare(job,baseline,database)
            with sqlite3.connect(database) as db:
                first=db.execute('SELECT id,last_group_playlist_id,last_group_id FROM channels ORDER BY playlist_id,position_in_playlist ASC,id LIMIT 1').fetchone()
            prefs=ET.fromstring(archive.read('ar.tvplayer.tv_preferences.xml'))
            overrides={'lastChannelId':('long',str(first[0])), 'lastGroupPlaylistId':('long',str(first[1])),
                'lastGroupId':('long',str(first[2])),'lastGroupTypeId':('int','4'),'lastContentType':('int','0'),
                'isInexactLogosMatching':('boolean','false'),'logosPriority':('int','1'),
                'lastTvGuideUpdateTime':('long','0'),'lastTvGuideUpdateChannelCount':('int','0'),
                'shouldUpdateTvGuideOnAppStart':('boolean','true' if job['epg_sources'] else 'false')}
            for name,(kind,value) in overrides.items():
                node=prefs.find("*[@name='"+name+"']")
                if node is None:node=ET.SubElement(prefs,kind,{'name':name})
                node.set('value',value)
            folder=prefs.find("string[@name='logosFolder']")
            if folder is None:folder=ET.SubElement(prefs,'string',{'name':'logosFolder'})
            folder.text=RECEIVER_ROOT+'/logos/_matched'
            data=io.BytesIO()
            with zipfile.ZipFile(data,'w') as target:
                for entry in archive.infolist():
                    content=(database.read_bytes() if entry.filename=='TvPlayer.db' else
                        ET.tostring(prefs,encoding='utf-8',xml_declaration=True) if entry.filename=='ar.tvplayer.tv_preferences.xml' else archive.read(entry.filename))
                    target.writestr(copy.copy(entry),content)
            blob=encode(data.getvalue(),seed);decode(blob,seed)
            write_private(staging/'tidytivi.tmb',blob)
            write_private(staging/'lineup.m3u',m3u(job))
            if job['settings'].get('profile_playlists',True):
                for profile in job['profiles']:
                    write_private(staging/('lineup-'+str(profile['id'])+'.m3u'),m3u(job,[profile],True))
            logo_report=build_country_logos(job,staging/'logos') if job['settings']['logos'] else {'country_files':0,'matched_files':0,'countries':[]}
            manifest={'schema':'tidytivi.bundle.v1','version':job['id'],'created_at':job['created_at'],
                'backup':'tidytivi.tmb','target_version':'5.3.3','receiver_root':RECEIVER_ROOT,
                'profiles':[{'name':p['name'],'channels':len(p['channels'])} for p in job['profiles']],
                'files':{}}
            for path in sorted(staging.rglob('*')):
                if path.is_file():manifest['files'][path.relative_to(staging).as_posix()]={'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
            write_private(staging/'manifest.json',json.dumps(manifest,indent=2).encode())
            with zipfile.ZipFile(staging/'tidytivi-latest.zip','w',zipfile.ZIP_DEFLATED) as bundle:
                for path in sorted(staging.rglob('*')):
                    if path.is_file() and path.name!='tidytivi-latest.zip':bundle.write(path,path.relative_to(staging).as_posix())
            (staging/'tidytivi-latest.zip').chmod(0o600)
            result={'path':str(destination/'tidytivi.tmb'),'bundle':str(destination/'tidytivi-latest.zip'),
                'logo_directory':str(destination/'logos'),'logos':logo_report,'channels':report['channels'],
                'live_playlists':report['playlists'],'catchup_channels':report['catchup_channels'],'vod':report['vod'],'profiles':manifest['profiles'],'skipped_profiles':[p['name'] for p in job['profiles'] if not p['channels']],'epg_sources':[s['name'] for s in job['epg_sources']],
                'sha256':hashlib.sha256(blob).hexdigest()}
        os.rename(staging,destination)
        return [result]
    except Exception:
        shutil.rmtree(staging,ignore_errors=True);raise
