"""Dropbox upload with renewable OAuth credentials and a stable shared link."""
import base64
import os
import secrets
import tempfile
import time
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
        raise ValueError('Dropbox authorization failed. Check the app key or run Connect Dropbox again with a fresh one-time code.') from None


AUTH_FILE = Path('/data/tidytivi/dropbox.json')


def read_auth():
    try:
        return json.loads(AUTH_FILE.read_text())
    except FileNotFoundError:
        return {}
    except Exception:
        raise ValueError('Could not read the saved Dropbox connection.') from None


def save_auth(values):
    AUTH_FILE.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, name = tempfile.mkstemp(prefix='.dropbox-', dir=AUTH_FILE.parent)
    try:
        with os.fdopen(fd, 'w') as handle:
            json.dump(values, handle)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(name, AUTH_FILE)
    finally:
        if os.path.exists(name): os.unlink(name)


def migrate_auth(settings):
    auth = read_auth()
    if not auth.get('refresh_token') and not auth.get('access_token'):
        if settings.get('dropbox_refresh_token') or settings.get('dropbox_access_token'):
            auth.update(app_key=settings.get('dropbox_app_key',''),
                        app_secret=settings.get('dropbox_app_secret',''),
                        refresh_token=settings.get('dropbox_refresh_token',''),
                        access_token=settings.get('dropbox_access_token',''))
            save_auth(auth)
    return auth


def connection_status(settings):
    auth = migrate_auth(settings)
    if auth.get('refresh_token'):
        return 'Dropbox connection saved. Automatic authorization renewal is configured. Export a bundle to verify upload access.'
    if auth.get('access_token'):
        return 'A temporary Dropbox connection is saved. Use Connect Dropbox to authorize automatic renewal.'
    if auth.get('pending'):
        return 'Waiting for Dropbox approval. Paste the one-time code, save settings, then click Connect Dropbox again.'
    return 'Dropbox is not connected. Save your app key, then click Connect Dropbox.'


def clear_code():
    from apps.plugins.models import PluginConfig
    from django.db import transaction
    with transaction.atomic():
        cfg = PluginConfig.objects.select_for_update().get(key='tidytivi')
        cfg.settings = dict(cfg.settings or {})
        for key in ('dropbox_auth_code','dropbox_refresh_token','dropbox_access_token','dropbox_app_secret'):
            cfg.settings.pop(key, None)
        cfg.save(update_fields=['settings'])


def connect(settings):
    auth = migrate_auth(settings)
    key = str(settings.get('dropbox_app_key','')).strip()
    if not key:
        raise ValueError('Save your Dropbox app key first. The setup guide is in the tidyTIVI README; no app secret is needed.')
    code = str(settings.get('dropbox_auth_code','')).strip()
    if code:
        pending = auth.get('pending', {})
        if pending.get('app_key') != key or time.time() - pending.get('created_at',0) > 1800:
            raise ValueError('This connection attempt expired or the app key changed. Clear the one-time code, save, then click Connect Dropbox for a new link.')
        result = token_request({'grant_type':'authorization_code','code':code,'client_id':key,
                                'code_verifier':pending['verifier']})
        if not result.get('refresh_token'):
            raise ValueError('Dropbox did not return ongoing access. Start Connect Dropbox again.')
        save_auth({'app_key':key,'refresh_token':result['refresh_token']})
        clear_code()
        return 'Dropbox connected. Enable Upload to Dropbox after export and save. The next export returns the download link for your Firestick. Refresh the plugin page to clear the completed setup code.'
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip('=')
    auth['pending'] = {'app_key':key,'verifier':verifier,'created_at':time.time()}
    save_auth(auth)
    url = 'https://www.dropbox.com/oauth2/authorize?' + urlencode({'client_id':key,'response_type':'code',
          'token_access_type':'offline','code_challenge':challenge,'code_challenge_method':'S256'})
    return 'Open this link and approve Dropbox access:\n'+url+'\n\nCopy the code Dropbox shows into One-time connection code, save settings, then click Connect Dropbox again. No app secret or token is needed.'


def access_token(settings):
    auth = migrate_auth(settings)
    if auth.get('refresh_token'):
        values = {'grant_type':'refresh_token','refresh_token':auth['refresh_token'],'client_id':auth['app_key']}
        if auth.get('app_secret'): values['client_secret'] = auth['app_secret']
        token = token_request(values).get('access_token')
    else:
        token = auth.get('access_token')
    if not token: raise ValueError('Connect Dropbox before enabling automatic upload.')
    return token


def upload_bundle(path, settings):
    path=Path(path);remote=str(settings.get('dropbox_path') or '/tidytivi-latest.zip')
    if not remote.startswith('/') or not remote.endswith('.zip') or '..' in remote.split('/'):
        raise ValueError('Dropbox path must be an absolute .zip file path.')
    token=access_token(settings)
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
