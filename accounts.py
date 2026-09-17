"""Recipient credentials never modify Dispatcharr's source accounts."""
import json
from urllib.parse import quote, urlencode, urlparse
from urllib.request import Request, urlopen


def apply_overrides(job, settings):
    for account in job['accounts']:
        aid = account['id']
        if str(settings.get(f'override_{aid}', False)).lower() not in ('true','1','yes','on'):
            continue
        username = str(settings.get(f'export_username_{aid}', '')).strip()
        password = str(settings.get(f'export_password_{aid}', ''))
        server = str(settings.get(f'export_server_{aid}', '')).strip() or account['server_url']
        parsed = urlparse(server)
        if not username or not password or parsed.scheme not in ('http','https') or not parsed.netloc or parsed.query or parsed.fragment or parsed.username:
            raise ValueError(f"Provide a valid export server, username and password for {account['name']}.")
        channels = [c for p in job['profiles'] for c in p['channels'] if c['account_id']==aid]
        url = server.rstrip('/')+'/player_api.php?'+urlencode({'username':username,'password':password,'action':'get_live_streams'})
        try:
            with urlopen(Request(url, headers={'User-Agent':'Mozilla/5.0'}),timeout=60) as response:
                rows = json.load(response)
            ids = {str(row['stream_id']) for row in rows}
        except Exception:
            raise ValueError(f"Could not validate the replacement account for {account['name']}. Check its credentials and server.") from None
        missing = [c['name'] for c in channels if str(c['xc_id']) not in ids]
        if missing:
            raise ValueError(f"Replacement account for {account['name']} lacks {len(missing)} mapped stream IDs: "+', '.join(missing[:12])+'. Export stopped; cross-provider IDs cannot be substituted.')
        for kind,action,id_key in [('movies','get_vod_streams','stream_id'),('series','get_series','series_id')]:
            items=[item for item in job.get('vod',{}).get(kind,[]) if item['account_id']==aid]
            if not items:continue
            try:
                endpoint=server.rstrip('/')+'/player_api.php?'+urlencode({'username':username,'password':password,'action':action})
                with urlopen(Request(endpoint,headers={'User-Agent':'Mozilla/5.0'}),timeout=90) as response:rows=json.load(response)
                allowed={str(row[id_key]) for row in rows}
            except Exception:raise ValueError('Could not validate replacement VOD access for '+account['name']) from None
            missing=sum(str(item['xc_id']) not in allowed for item in items)
            if missing:raise ValueError(f"Replacement account for {account['name']} lacks {missing} curated {kind} IDs; export stopped.")
        account.update(server_url=server,username=username,password=password,overridden=True)
        for channel in channels:
            channel['provider_url'] = server.rstrip('/')+'/live/'+quote(username,safe='')+'/'+quote(password,safe='')+'/'+str(channel['xc_id'])+'.ts'
    return job
