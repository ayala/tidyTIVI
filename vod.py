"""Complete provider VOD with native XC category identities and updates."""
import json
import math
from urllib.parse import quote


def collect_vod(accounts):
    """Fetch the complete catalogue using the final recipient XC credentials."""
    from urllib.parse import urlencode
    from urllib.request import Request, urlopen
    result = {'movies': [], 'series': []}
    for account in accounts:
        def fetch(action):
            endpoint = account['server_url'].rstrip('/') + '/player_api.php?' + urlencode({
                'username': account['username'], 'password': account['password'], 'action': action})
            try:
                with urlopen(Request(endpoint, headers={'User-Agent': 'Mozilla/5.0'}), timeout=180) as response:
                    rows = json.load(response)
                if not isinstance(rows, list):
                    raise ValueError('Expected XC catalogue')
                return rows
            except Exception:
                raise ValueError('Could not load the complete XC VOD catalogue for ' + account['name'] + '. Export stopped; check account access and retry.') from None
        for kind, category_action, item_action, id_key in [
            ('movies', 'get_vod_categories', 'get_vod_streams', 'stream_id'),
            ('series', 'get_series_categories', 'get_series', 'series_id')]:
            categories = {str(row['category_id']): row['category_name'] for row in fetch(category_action)}
            for row in fetch(item_action):
                cid = str(row.get('category_id') or '0')
                try:
                    rating = float(row.get('rating'))
                    if not math.isfinite(rating): rating = None
                except (ValueError, TypeError): rating = None
                result[kind].append({
                    'id': int(row[id_key]), 'account_id': account['id'], 'xc_id': int(row[id_key]),
                    'name': row.get('name') or '', 'category': categories.get(cid, 'Uncategorized'),
                    'category_id': cid, 'image': row.get('stream_icon' if kind == 'movies' else 'cover') or '',
                    'rating': rating, 'extension': (row.get('container_extension') or 'mp4') if kind == 'movies' else None})
    return result


def add_vod(db,job,playlist_template,insert):
    vod=job.get('vod') or {'movies':[],'series':[]}
    result={'movies':len(vod['movies']),'series':len(vod['series']),'playlists':0}
    accounts={a['id']:a for a in job['accounts']}
    for aid in sorted(accounts):
        account=accounts[aid];movies=[x for x in vod['movies'] if x['account_id']==aid];series=[x for x in vod['series'] if x['account_id']==aid]
        values={k:v for k,v in playlist_template.items() if k!='id'}
        import time
        values.update(name=account['name']+' · VOD',url='xc:'+json.dumps({'h':account['server_url'].rstrip('/'),'u':account['username'],'p':account['password'],'o':'ts'},separators=(',',':')),
            include_tv_channels=0,include_vod=1,is_vod=1,is_enabled=1,auto_update=1,last_update_time=int(time.time()*1000),
            channel_count=0,movie_count=len(movies),series_count=len(series),tvg_urls='',position=sum(bool(p['channels']) for p in job['profiles'])+result['playlists'] if job['settings'].get('profile_playlists',True) else 1+result['playlists'],
            is_visible_in_all_channels=0,is_visible_in_all_favorites=0,are_new_groups_visible=0,
            are_new_movie_groups_visible=1,are_new_series_groups_visible=1,expiration_date=None,max_connections=None)
        pid=insert(db,'playlists',values);result['playlists']+=1
        for kind,items in [('movies',movies),('series',series)]:
            groups={}
            table='movie_categories' if kind=='movies' else 'series_categories'
            for position,item in enumerate(items):
                key=str(item['category_id'])
                if key not in groups:
                    groups[key]=insert(db,table,{'playlist_id':pid,'xc_id':key,'name':item['category'],'is_visible':1,'position_in_playlist':len(groups),'manual_position':len(groups),'item_count':0})
                values={'playlist_id':pid,'category_id':groups[key],'xc_id':item['xc_id'],'name':item['name'],
                    'image':item['image'],'rating':item['rating'],'position_in_category':position,'display_mode':1,
                    'is_favorite':0,'last_turn_on_time':0,'deleted_time':None}
                if kind=='movies':
                    ext=item['extension']
                    if not ext.isalnum():raise ValueError('Unsupported movie extension.')
                    values.update(url=account['server_url'].rstrip('/')+'/movie/'+quote(account['username'],safe='')+'/'+quote(account['password'],safe='')+'/'+str(item['xc_id'])+'.'+ext,
                        added_time=0,last_played_position_ms=0,duration_ms=0)
                else:values.update(last_modified_time=0,last_episode_xc_id=None)
                insert(db,kind,values)
            for gid in groups.values():db.execute('UPDATE '+table+' SET item_count=(SELECT count(*) FROM '+kind+' WHERE category_id=?) WHERE id=?',(gid,gid))
    return result
