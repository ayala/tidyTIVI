"""Experimental curation merge into a COPY of a receiver database (schema 60).

Does not decrypt receiver backups or modify a running TiviMate installation.
Only existing tidyTIVI profile playlists are matched; ambiguous matches abort.
"""
from pathlib import Path
import os
import re
import sqlite3
import time
from .database import insert


class MergeError(ValueError):
    pass


def playlist_key(url):
    match = re.fullmatch(r'(?:file://)?/sdcard/Download/tidyTIVI/current/(lineup(?:-\d+)?\.m3u)', url)
    return match.group(1) if match else None


def unique(rows, key, description):
    result = {}
    for row in rows:
        value = key(row)
        if value is None:
            continue
        if value in result:
            raise MergeError('Ambiguous ' + description + '; no changes applied.')
        result[value] = row
    return result


def update(db, table, row_id, values):
    db.execute('UPDATE '+table+' SET '+','.join('"'+k+'"=?' for k in values)+' WHERE id=?', [*values.values(), row_id])


# Curation owns these fields. Visibility, favorites, history, playback settings,
# last selected group and all VOD tables belong to the receiving installation.
CHANNEL_FIELDS = ('name', 'custom_name', 'url', 'logo', 'tvg_id', 'tvg_name',
                  'tvg_shift', 'tvg_ch_no', 'catchup_type', 'catchup_hours',
                  'catchup_source', 'position_in_playlist', 'position_in_group',
                  'user_tvg_id')


def merge_databases(receiver, curated, output):
    receiver, curated, output = map(Path, (receiver, curated, output))
    if output.exists() or output.resolve() in (receiver.resolve(), curated.resolve()):
        raise MergeError('Output must be a new file separate from both inputs.')
    src = sqlite3.connect(curated.resolve().as_uri()+'?mode=ro', uri=True)
    old = sqlite3.connect(receiver.resolve().as_uri()+'?mode=ro', uri=True)
    src.row_factory = old.row_factory = sqlite3.Row
    db = None
    try:
        if any(c.execute('PRAGMA user_version').fetchone()[0] != 60 for c in (src, old)):
            raise MergeError('Only tested TiviMate schema 60 is supported.')
        incoming = unique(src.execute('SELECT * FROM playlists'), lambda r: playlist_key(r['url']), 'incoming playlist')
        existing = unique(old.execute('SELECT * FROM playlists'), lambda r: playlist_key(r['url']), 'receiver playlist')
        if not incoming or not set(incoming) <= set(existing):
            raise MergeError('Every incoming profile must match an existing tidyTIVI playlist.')
        output.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(output, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600); os.close(fd)
        db = sqlite3.connect(output); db.row_factory = sqlite3.Row
        old.backup(db)
        db.execute('PRAGMA foreign_keys=ON'); db.execute('BEGIN')
        report = dict(playlists=0, updated_channels=0, added_channels=0, retired_channels=0)
        source_map = {}
        def source_id(sid):
            if sid is None:
                return None
            if sid not in source_map:
                row = src.execute('SELECT * FROM tvg_sources WHERE id=?', (sid,)).fetchone()
                if row is None:
                    raise MergeError('Missing EPG source.')
                matches = db.execute('SELECT id FROM tvg_sources WHERE url=? AND type=?', (row['url'], row['type'])).fetchall()
                if len(matches)>1:
                    raise MergeError('Ambiguous receiver EPG source.')
                if matches:
                    source_map[sid] = matches[0]['id']
                else:
                    values = dict(row); values.pop('id'); values['playlist_id'] = None
                    source_map[sid] = insert(db, 'tvg_sources', values)
            return source_map[sid]
        for key, ip in incoming.items():
            rp = existing[key]; pid = rp['id']; iid = ip['id']
            ic = unique(src.execute('SELECT * FROM channels WHERE playlist_id=?', (iid,)), lambda r: r['name'], 'incoming channel')
            rc = unique(db.execute('SELECT * FROM channels WHERE playlist_id=?', (pid,)), lambda r: r['name'], 'receiver channel')
            if any(not re.fullmatch(r'tidytivi-\d+', n) for n in ic):
                raise MergeError('Incoming channels lack stable tidyTIVI identities.')
            # Match groups by their established stable channel membership. This
            # permits renames while retaining receiver hidden/blocked settings.
            rg = list(db.execute('SELECT * FROM channel_groups WHERE playlist_id=?', (pid,)))
            old_members = {g['id']: {r[0] for r in db.execute('SELECT c.name FROM channels c JOIN channel_group_links l ON l.channel_id=c.id WHERE l.group_id=?', (g['id'],))} for g in rg}
            gm = {}; used = set()
            groups = list(src.execute('SELECT * FROM channel_groups WHERE playlist_id=?', (iid,)))
            canonical = lambda name: name.rsplit(':', 1)[-1].strip().casefold()
            reserved = {r['id'] for r in rg for g in groups if canonical(r['name']) == canonical(g['name'])}
            for g in groups:
                members = {r[0] for r in src.execute('SELECT c.name FROM channels c JOIN channel_group_links l ON l.channel_id=c.id WHERE l.group_id=?', (g['id'],))}
                exact = [r for r in rg if r['name']==g['name'] and r['id'] not in used]
                if not exact:
                    exact = [r for r in rg if canonical(r['name'])==canonical(g['name']) and r['id'] not in used]
                if len(exact)>1:
                    raise MergeError('Ambiguous receiver group.')
                match = exact[0] if exact else None
                if match is None:
                    scores = [(len(members & old_members[r['id']]), r) for r in rg if r['id'] not in used and r['id'] not in reserved]
                    best = max((n for n,r in scores), default=0)
                    candidates = [r for n,r in scores if n==best and n>0]
                    if len(candidates)>1:
                        raise MergeError('Ambiguous renamed group; explicit mapping required.')
                    match = candidates[0] if candidates else None
                if match:
                    gid = match['id']; used.add(gid)
                    update(db, 'channel_groups', gid, {k:g[k] for k in ('name','position_in_playlist','deleted_time')})
                    db.execute('UPDATE channel_group_options SET custom_group_name=NULL WHERE playlist_id=? AND group_id=? AND type=4', (pid,gid))
                else:
                    v = dict(g); v.pop('id'); v['playlist_id']=pid; gid=insert(db,'channel_groups',v)
                    for options in src.execute('SELECT * FROM channel_group_options WHERE playlist_id=? AND group_id=?', (iid,g['id'])):
                        v=dict(options);v.pop('id');v.update(playlist_id=pid,group_id=gid);insert(db,'channel_group_options',v)
                gm[g['id']] = gid
            for name, ch in ic.items():
                prior = rc.get(name)
                values = {k:ch[k] for k in CHANNEL_FIELDS}
                values.update(original_group_id=gm.get(ch['original_group_id']), user_tvg_source_id=source_id(ch['user_tvg_source_id']), deleted_time=None)
                if prior:
                    cid = prior['id']; update(db,'channels',cid,values);report['updated_channels']+=1
                else:
                    v=dict(ch);v.pop('id');v.update(values);v.update(playlist_id=pid,last_group_playlist_id=pid,last_group_id=gm.get(ch['last_group_id']))
                    cid=insert(db,'channels',v);report['added_channels']+=1
                # Preserve links to receiver-created personal groups. Replace
                # only membership in the groups matched to incoming curation.
                managed=list(gm.values())
                if managed:
                    marks=','.join('?' for _ in managed)
                    db.execute('DELETE FROM channel_group_links WHERE channel_id=? AND group_id IN ('+marks+')', [cid,*managed])
                    db.execute('DELETE FROM channel_manual_positions WHERE channel_id=? AND type=4 AND playlist_id=? AND group_id IN ('+marks+')', [cid,pid,*managed])
                for link in src.execute('SELECT group_id FROM channel_group_links WHERE channel_id=?', (ch['id'],)):
                    gid=gm[link['group_id']];insert(db,'channel_group_links',dict(channel_id=cid,group_id=gid))
                for pos in src.execute('SELECT * FROM channel_manual_positions WHERE channel_id=?', (ch['id'],)):
                    if pos['group_id'] in gm:
                        v=dict(pos);v.pop('id');v.update(channel_id=cid,playlist_id=pid,group_id=gm[pos['group_id']]);insert(db,'channel_manual_positions',v)
            for name,ch in rc.items():
                if re.fullmatch(r'tidytivi-\d+',name) and name not in ic and ch['deleted_time'] is None:
                    update(db,'channels',ch['id'],dict(deleted_time=int(time.time()*1000)));report['retired_channels']+=1
            for assignment in src.execute('SELECT * FROM playlist_tvg_source_assignments WHERE playlist_id=?', (iid,)):
                sid=source_id(assignment['tvg_source_id'])
                if not db.execute('SELECT 1 FROM playlist_tvg_source_assignments WHERE playlist_id=? AND tvg_source_id=?',(pid,sid)).fetchone():
                    insert(db,'playlist_tvg_source_assignments',dict(playlist_id=pid,tvg_source_id=sid,priority=assignment['priority']))
            update(db,'playlists',pid,dict(name=ip['name'],channel_count=len(ic)))
            report['playlists']+=1
        if db.execute('PRAGMA foreign_key_check').fetchone() or db.execute('PRAGMA integrity_check').fetchone()[0]!='ok':
            raise MergeError('Merged database failed integrity validation.')
        db.commit();db.execute('PRAGMA wal_checkpoint(TRUNCATE)');db.execute('PRAGMA journal_mode=DELETE')
        return report
    except Exception:
        if db is not None:
            db.close();db=None;output.unlink(missing_ok=True)
        raise
    finally:
        if db is not None:db.close()
        old.close();src.close()
