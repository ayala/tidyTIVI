"""Dropbox upload with renewable OAuth credentials and a stable shared link."""
import hashlib
import json
from pathlib import Path
from urllib.parse import urlencode, urlparse, parse_qsl, urlunparse
from urllib.request import Request, urlopen


def token_request(values):
    try:
        with urlopen(Request('https://api.dropboxapi.com/oauth2/token',data=urlencode(values).encode()),timeout=45) as response:
            return json.load(response)
    except Exception:
        raise ValueError('Dropbox authorization failed. Check the app credentials and authorization/refresh token.') from None


def connect(settings):
    key=str(settings.get('dropbox_app_key','')).strip()
    secret=str(settings.get('dropbox_app_secret','')).strip()
    if not key or not secret:raise ValueError('Enter the Dropbox app key and app secret first.')
    code=str(settings.get('dropbox_auth_code','')).strip()
    if not code:
        return {'authorization_url':'https://www.dropbox.com/oauth2/authorize?'+urlencode({'client_id':key,'response_type':'code','token_access_type':'offline'}),
                'message':'Open this URL, authorize your Dropbox app, then paste the returned code into Dropbox authorization code and run Connect again.'}
    result=token_request({'grant_type':'authorization_code','code':code,'client_id':key,'client_secret':secret})
    if not result.get('refresh_token'):raise ValueError('Dropbox did not return an offline refresh token.')
    from apps.plugins.models import PluginConfig
    cfg=PluginConfig.objects.get(key='tidytivi');cfg.settings.update({'dropbox_refresh_token':result['refresh_token'],'dropbox_auth_code':'','dropbox_access_token':''});cfg.save(update_fields=['settings'])
    return {'message':'Dropbox connected. Enable Upload to Dropbox after export and save settings.'}


def upload_bundle(path, settings):
    path=Path(path);remote=str(settings.get('dropbox_path') or '/tidytivi-latest.zip')
    if not remote.startswith('/') or not remote.endswith('.zip') or '..' in remote.split('/'):
        raise ValueError('Dropbox path must be an absolute .zip file path.')
    refresh=str(settings.get('dropbox_refresh_token','')).strip()
    if refresh:
        token=token_request({'grant_type':'refresh_token','refresh_token':refresh,'client_id':settings.get('dropbox_app_key',''),'client_secret':settings.get('dropbox_app_secret','')}).get('access_token')
    else:token=str(settings.get('dropbox_access_token','')).strip()
    if not token:raise ValueError('Connect Dropbox before enabling automatic upload.')
    def call(route,args,data=None):
        headers={'Authorization':'Bearer '+token}
        host='https://api.dropboxapi.com/2/'
        if data is None:headers['Content-Type']='application/json';body=json.dumps(args).encode()
        else:
            host='https://content.dropboxapi.com/2/';headers.update({'Content-Type':'application/octet-stream','Dropbox-API-Arg':json.dumps(args,ensure_ascii=True)});body=data
        try:
            with urlopen(Request(host+route,data=body,headers=headers),timeout=120) as response:
                raw=response.read();return json.loads(raw) if raw else {}
        except Exception:raise ValueError('Dropbox '+route+' failed. Local export is intact; check scopes, storage and connection.') from None
    commit={'path':remote,'mode':'overwrite','autorename':False,'mute':True,'strict_conflict':False}
    if path.stat().st_size<=140*1024*1024:metadata=call('files/upload',commit,path.read_bytes())
    else:
        with path.open('rb') as source:
            chunk=source.read(8*1024*1024);session=call('files/upload_session/start',{'close':False},chunk)['session_id'];offset=len(chunk)
            while True:
                chunk=source.read(8*1024*1024)
                cursor={'session_id':session,'offset':offset}
                if offset+len(chunk)>=path.stat().st_size:
                    metadata=call('files/upload_session/finish',{'cursor':cursor,'commit':commit},chunk);break
                call('files/upload_session/append_v2',{'cursor':cursor,'close':False},chunk);offset+=len(chunk)
    digest=hashlib.sha256()
    with path.open('rb') as source:
        while True:
            block=source.read(4*1024*1024)
            if not block:break
            digest.update(hashlib.sha256(block).digest())
    if metadata.get('content_hash')!=digest.hexdigest():raise ValueError('Dropbox uploaded content verification failed.')
    links=call('sharing/list_shared_links',{'path':remote,'direct_only':True}).get('links',[])
    link=links[0] if links else call('sharing/create_shared_link_with_settings',{'path':remote})
    parts=urlparse(link['url']);query=dict(parse_qsl(parts.query));query.pop('raw',None);query['dl']='1'
    return {'status':'ok','path':remote,'download_url':urlunparse(parts._replace(query=urlencode(query))), 'bytes':path.stat().st_size}
