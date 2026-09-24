"""Prepare a COPY of a TiviMate 5.3.3 database for the standalone backup writer.

Never run against a live database. The output is an intermediate SQLite file,
not a native backup until packaged by tmb_codec.
"""
import argparse
import json
import os
from pathlib import Path
import sqlite3
import secrets
import time


def insert(db, table, values):
    keys = list(values)
    return db.execute('INSERT INTO '+table+' ('+','.join('"'+k+'"' for k in keys)+') VALUES ('+
                      ','.join('?' for _ in keys)+')', [values[k] for k in keys]).lastrowid


def prepare(job, baseline, output):
    if job.get('schema') != 'tidytivi.job.v1' or job.get('target_version') != '5.3.3':
        raise ValueError('Only tidyTIVI v1 jobs targeting TiviMate 5.3.3 are supported.')
    output, baseline = Path(output), Path(baseline)
    if output.exists() or output.resolve() == baseline.resolve():
        raise ValueError('Output must be a new file, separate from the baseline.')
    if not baseline.is_file():
        raise ValueError('Baseline database does not exist.')
    source_db = sqlite3.connect(baseline.as_uri()+'?mode=ro', uri=True)
    source_db.row_factory = sqlite3.Row
    if source_db.execute('PRAGMA user_version').fetchone()[0] != 60:
        source_db.close()
        raise ValueError('Expected the tested TiviMate 5.3.3 database schema (60).')
    playlist_template = source_db.execute("SELECT * FROM playlists WHERE url LIKE 'xc:%' LIMIT 1").fetchone()
    channel_template = source_db.execute('SELECT * FROM channels LIMIT 1').fetchone()
    if playlist_template is None or channel_template is None:
        source_db.close()
        raise ValueError('Baseline must contain an existing XC playlist and channel.')
    # Preserve defaults/schema from the real app, but clear viewing and guide state.
    playlist_template = dict(playlist_template)
    channel_template = dict(channel_template)
    output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd = os.open(output, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.close(fd)
    db = sqlite3.connect(output)
    try:
        source_db.backup(db)
        source_db.close()
        # This database is a disposable copy; keep bulk rewrites in a bounded cache.
        db.execute('PRAGMA cache_size=-65536')
        db.execute('PRAGMA temp_store=MEMORY')
        db.execute('PRAGMA journal_mode=MEMORY')
        db.execute('PRAGMA synchronous=OFF')
        db.execute('PRAGMA foreign_keys=ON')
        db.execute('BEGIN')
        # This file is a new selected-profile configuration. Never modify baseline.
        db.execute('DELETE FROM playlists')
        db.execute('DELETE FROM channel_group_options')
        db.execute('DELETE FROM tvg_sources')
        # TiviMate retains detail/connection caches outside its backup database.
        # Fresh IDs prevent a new provider/account from inheriting those entries.
        identity_base=100_000_000+secrets.randbelow(1_000_000_000)
        for table in ('playlists','channels','channel_groups','movies','series','movie_categories','series_categories','tvg_sources'):
            db.execute('DELETE FROM sqlite_sequence WHERE name=?',(table,))
            db.execute('INSERT INTO sqlite_sequence(name,seq) VALUES (?,?)',(table,identity_base))
        source_ids = {}
        for source in job['epg_sources']:
            source_ids[source['id']] = insert(db, 'tvg_sources', {'playlist_id': None, 'type': 1,
                'name': source['name'], 'url': source['url'], 'time_offset': 0, 'last_update_time': 0})
        total = sum(len(profile['channels']) for profile in job['profiles'])
        separate = job['settings'].get('profile_playlists', True)
        batches = [(p['name'], [p], 'lineup-'+str(p['id'])+'.m3u') for p in job['profiles'] if p['channels']] if separate else [(job['settings'].get('playlist_name') or 'tidyTIVI', job['profiles'], 'lineup.m3u')]
        report = {'profiles': [], 'channels': total, 'catchup_channels': sum(c.get('catchup_hours',0)>0 for p in job['profiles'] for c in p['channels']), 'playlists': len(batches), 'epg_sources': len(source_ids)}
        for playlist_position,(name,profiles,filename) in enumerate(batches):
            count = sum(len(p['channels']) for p in profiles)
            archive_hours=max((c.get('catchup_hours',0) for p in profiles for c in p['channels']),default=0)
            values = {k:v for k,v in playlist_template.items() if k != 'id'}
            values.update(name=name,url='file:///sdcard/Download/tidyTIVI/current/'+filename,
                auto_update=0,last_update_time=int(time.time()*1000),include_tv_channels=1,include_vod=0,
                is_vod=0,channel_count=count,movie_count=0,series_count=0,tvg_urls='',is_enabled=1,
                are_new_groups_visible=0,are_new_movie_groups_visible=0,are_new_series_groups_visible=0,
                expiration_date=None,max_connections=None,catchup_type=3 if archive_hours else None,catchup_hours=archive_hours,
                catchup_source=None,user_catchup_type=None,user_catchup_hours=None,user_catchup_time_offset=None,
                stalker_token=None,position=playlist_position,logos_priority=1,
                groups_sorting=5,prev_groups_sorting=1)
            pid = insert(db,'playlists',values)
            used_sources={c['epg']['source_id'] for p in profiles for c in p['channels'] if c.get('epg')}
            for priority,source in enumerate(s for s in job['epg_sources'] if s['id'] in used_sources):
                insert(db,'playlist_tvg_source_assignments',{'playlist_id':pid,'tvg_source_id':source_ids[source['id']],'priority':priority})
            group_number = 0
            position = 0
            def group(name):
                nonlocal group_number
                gid=insert(db,'channel_groups',{'playlist_id':pid,'name':name,'is_custom':1,'position_in_playlist':group_number})
                insert(db,'channel_group_options',{'type':4,'playlist_id':pid,'group_id':gid,'sorting':5,'prev_sorting':1,'is_visible':1,'are_favorites_only':0,'manual_position':group_number})
                group_number+=1
                return gid
            for profile in profiles:
                profile_gid = None if separate else group(profile['name'])
                subgroups = {}
                for local_position,ch in enumerate(profile['channels']):
                    group_ids = [] if separate else [profile_gid]
                    if separate or job['settings'].get('include_subgroups', True):
                        if ch['group_id'] not in subgroups:
                            subgroups[ch['group_id']]=group(ch['group_name'] if separate else profile['name']+' · '+ch['group_name'])
                        group_ids.append(subgroups[ch['group_id']])
                    curated = ch['name'] if job['settings']['names'] else ch['provider_name']
                    if job['settings']['number_prefix']:
                        curated = ch['number']+' · '+curated
                    guide = ch['epg']
                    v = {k:x for k,x in channel_template.items() if k!='id'}
                    v.update(playlist_id=pid, xc_id=None, stalker_id=None,
                        name='tidytivi-'+str(ch['id']), custom_name=curated, url=ch['provider_url'],
                        logo=ch['logo_url'] or '', original_group_id=group_ids[0],
                        tvg_id=guide['xmltv_id'] if guide else '',tvg_name='',tvg_shift=0,tvg_ch_no=-1,
                        drm_scheme='',drm_license_url='',server_timezone=None,
                        catchup_type=3 if ch.get('catchup_hours',0)>0 else None,
                        catchup_hours=ch.get('catchup_hours',0),catchup_source=None,
                        position_in_playlist=position,position_in_group=local_position,
                        is_visible=1,is_blocked=0,is_favorite=0,last_turn_on_time=0,
                        last_group_id=group_ids[0],last_group_type_id=4,last_group_playlist_id=pid,watch_time=0,
                        audio_track_selection=None,video_track_selection=None,closed_captions_selection=None,
                        display_mode=channel_template['display_mode'],audio_offset=None,
                        user_tvg_id=guide['xmltv_id'] if guide else '',
                        user_tvg_source_id=source_ids[guide['source_id']] if guide else None,
                        user_tvg_time_offset=None,blocked_tvg_ids='',audio_decoder_priority=None,
                        video_decoder_priority=None,use_external_player=None,deleted_time=None)
                    cid = insert(db, 'channels', v)
                    for gid in group_ids:
                        insert(db, 'channel_group_links', {'channel_id':cid, 'group_id':gid})
                        insert(db, 'channel_manual_positions', {'channel_id':cid,'type':4,
                            'playlist_id':pid,'group_id':gid,'position':local_position})
                    position += 1
                report['profiles'].append({'name':profile['name'],'channels':len(profile['channels'])})
        from .vod import add_vod
        report['vod'] = add_vod(db, job, playlist_template, insert)
        if db.execute('PRAGMA foreign_key_check').fetchone():
            raise ValueError('Generated database failed its foreign-key check.')
        if db.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise ValueError('Generated database failed its integrity check.')
        db.commit()
        db.execute('PRAGMA wal_checkpoint(TRUNCATE)')
        db.execute('PRAGMA journal_mode=DELETE')
        db.execute('VACUUM')
        return report
    except Exception:
        db.rollback()
        db.close()
        output.unlink(missing_ok=True)
        raise
    finally:
        source_db.close()
        db.close()


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--job', required=True)
    parser.add_argument('--baseline', required=True)
    parser.add_argument('--output', required=True)
    args=parser.parse_args()
    try:
        print(json.dumps(prepare(json.loads(Path(args.job).read_text()), args.baseline, args.output), indent=2))
    except Exception as exc:
        # Never emit SQLite rows or account-bearing URLs.
        raise SystemExit('Preparation failed: '+(str(exc) if isinstance(exc, ValueError) else type(exc).__name__))
