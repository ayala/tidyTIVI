"""Complete native XC live catalogues, independent of Dispatcharr filtering."""
import json
from urllib.parse import urlencode, quote
from urllib.request import Request, urlopen
from .accounts import catchup_hours


def collect_master(accounts):
    result = []
    for account in accounts:
        def fetch(action):
            url = account['server_url'].rstrip('/') + '/player_api.php?' + urlencode(dict(
                username=account['username'], password=account['password'], action=action))
            try:
                with urlopen(Request(url, headers={'User-Agent': 'Mozilla/5.0'}), timeout=180) as response:
                    rows = json.load(response)
                if not isinstance(rows, list): raise ValueError()
                return rows
            except Exception:
                raise ValueError('Could not load the complete live catalogue for ' + account['name'] + '. Export stopped.') from None
        categories = fetch('get_live_categories')
        channels = fetch('get_live_streams')
        ids = [str(c['stream_id']) for c in channels]
        if len(ids) != len(set(ids)):
            raise ValueError('Duplicate live stream IDs in ' + account['name'] + '. Export stopped.')
        result.append(dict(account_id=account['id'], categories=categories, channels=channels))
    return result


def add_masters(db, job, playlist_template, channel_template, insert):
    result = []
    accounts = {a['id']: a for a in job['accounts']}
    for master in job.get('provider_masters', []):
        account = accounts[master['account_id']]
        values = {k:v for k,v in playlist_template.items() if k != 'id'}
        values.update(name=account['name']+' · Master', url='xc:'+json.dumps(dict(
            h=account['server_url'].rstrip('/'), u=account['username'], p=account['password'], o='ts'), separators=(',', ':')),
            include_tv_channels=1, include_vod=0, is_vod=0, is_enabled=0, auto_update=1,
            last_update_time=0, channel_count=len(master['channels']), movie_count=0, series_count=0,
            tvg_urls='', is_visible_in_all_channels=0, is_visible_in_all_favorites=0,
            are_new_groups_visible=1, are_new_movie_groups_visible=0, are_new_series_groups_visible=0,
            position=db.execute('SELECT count(*) FROM playlists').fetchone()[0],
            expiration_date=None, max_connections=None, stalker_token=None)
        pid = insert(db, 'playlists', values)
        groups = {}
        for category in master['categories']:
            key = str(category['category_id'])
            groups[key] = insert(db, 'channel_groups', dict(playlist_id=pid, xc_id=int(key),
                name=category['category_name'], is_custom=0, position_in_playlist=len(groups)))
        for position, channel in enumerate(master['channels']):
            key = str(channel.get('category_id') or '0')
            if key not in groups:
                groups[key] = insert(db, 'channel_groups', dict(playlist_id=pid, xc_id=int(key),
                    name='Uncategorized', is_custom=0, position_in_playlist=len(groups)))
            gid = groups[key]
            values = {k:v for k,v in channel_template.items() if k != 'id'}
            hours = catchup_hours(channel)
            values.update(playlist_id=pid, xc_id=int(channel['stream_id']), stalker_id=None,
                name=channel.get('name') or '', custom_name=None,
                url=account['server_url'].rstrip('/')+'/live/'+quote(account['username'],safe='')+'/'+quote(account['password'],safe='')+'/'+str(int(channel['stream_id']))+'.ts',
                logo=channel.get('stream_icon') or '', original_group_id=gid,
                tvg_id=channel.get('epg_channel_id') or '', tvg_name='', tvg_shift=0, tvg_ch_no=-1,
                drm_scheme='', drm_license_url='', server_timezone=None, catchup_type=3 if hours else None,
                catchup_hours=hours, catchup_source=None, position_in_playlist=position, position_in_group=position,
                is_visible=1, is_blocked=0, is_favorite=0, last_turn_on_time=0, watch_time=0,
                last_group_id=None, last_group_type_id=0, last_group_playlist_id=0,
                audio_track_selection=None, video_track_selection=None, closed_captions_selection=None,
                audio_offset=None, user_tvg_id='', user_tvg_source_id=None, user_tvg_time_offset=None,
                blocked_tvg_ids='', audio_decoder_priority=None, video_decoder_priority=None,
                use_external_player=None, deleted_time=None)
            cid = insert(db, 'channels', values)
            insert(db, 'channel_group_links', dict(channel_id=cid, group_id=gid))
        result.append(dict(key=str(account['id']), id=pid, name=account['name']+' · Master', channels=len(master['channels'])))
    return result
