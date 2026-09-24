"""Browser OAuth callbacks and private, renewable authorization for cloud exports."""
import base64
from contextlib import contextmanager
import fcntl
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import secrets
import tempfile
import time
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

ROOT = Path('/data/tidytivi')
CALLBACK_PATH = '/api/plugins/tidytivi/cloud/callback/'
PROVIDERS = {'dropbox': ('Dropbox','https://www.dropbox.com/oauth2/authorize','https://api.dropboxapi.com/oauth2/token'),
             'drive': ('Google Drive','https://accounts.google.com/o/oauth2/v2/auth','https://oauth2.googleapis.com/token')}


def read(name):
    try: return json.loads((ROOT/name).read_text())
    except FileNotFoundError: return {}
    except Exception: raise ValueError('Could not read private cloud configuration.') from None


def write(name, value):
    ROOT.mkdir(parents=True,exist_ok=True,mode=0o700)
    fd, tmp = tempfile.mkstemp(prefix='.cloud-',dir=ROOT)
    try:
        with os.fdopen(fd,'w') as f:
            json.dump(value,f);f.flush();os.fsync(f.fileno())
        os.replace(tmp,ROOT/name)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)


@contextmanager
def locked():
    ROOT.mkdir(parents=True,exist_ok=True,mode=0o700)
    with os.fdopen(os.open(ROOT/'cloud.lock',os.O_CREAT|os.O_RDWR,0o600),'a') as f:
        fcntl.flock(f,fcntl.LOCK_EX)
        try:yield
        finally:fcntl.flock(f,fcntl.LOCK_UN)


def provider(settings):
    value=settings.get('cloud_provider') or 'dropbox'
    if value not in PROVIDERS:raise ValueError('Choose Dropbox or Google Drive.')
    return value


def validate_redirect(value):
    p=urlparse(value)
    loopback=p.hostname in ('localhost','127.0.0.1','::1')
    if p.username or p.password or p.query or p.fragment or p.path!=CALLBACK_PATH or not p.hostname:
        raise ValueError('Use the exact tidyTIVI callback URL shown in CLOUD-SETUP.md.')
    if not loopback:
        try:ipaddress.ip_address(p.hostname);is_ip=True
        except ValueError:is_ip=False
        if is_ip or p.scheme!='https':raise ValueError('Sign-in needs HTTPS with a hostname, or the temporary localhost connection. A private-IP HTTP URL is not supported.')
    elif p.scheme not in ('http','https'):raise ValueError('Invalid callback URL.')
    return value


def client(which, settings):
    config=dict(read('cloud-clients.json').get(which,{}) or {})
    if which=='dropbox' and not config.get('client_id'):
        config['client_id']=settings.get('dropbox_app_key') or read('dropbox.json').get('app_key','')
    if not config.get('client_id') or (which=='drive' and not config.get('client_secret')):
        raise ValueError(PROVIDERS[which][0]+' needs its one-time app registration. Install the client configuration described in CLOUD-SETUP.md; users can then sign in with Connect cloud storage.')
    config['redirect_uri']=validate_redirect(config.get('redirect_uri') or 'http://127.0.0.1:19191'+CALLBACK_PATH)
    return config


def token_request(which, values):
    try:
        with urlopen(Request(PROVIDERS[which][2],data=urlencode(values).encode()),timeout=45) as response:
            result=json.load(response)
        if not isinstance(result,dict):raise ValueError()
        return result
    except Exception:raise ValueError(PROVIDERS[which][0]+' authorization failed. Start Connect cloud storage again; your previous connection was kept.') from None


def begin(settings):
    which=provider(settings);config=client(which,settings)
    state=secrets.token_urlsafe(32);verifier=secrets.token_urlsafe(64)
    challenge=base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip('=')
    with locked():
        pending={k:v for k,v in read('cloud-pending.json').items() if time.time()-v.get('created_at',0)<1800}
        pending[state]={'provider':which,'client':config,'verifier':verifier,'created_at':time.time()}
        write('cloud-pending.json',pending)
    params={'client_id':config['client_id'],'redirect_uri':config['redirect_uri'],'response_type':'code','state':state,
            'code_challenge':challenge,'code_challenge_method':'S256'}
    if which=='drive':params.update(access_type='offline',prompt='consent',scope='https://www.googleapis.com/auth/drive.file')
    else:params['token_access_type']='offline'
    return PROVIDERS[which][1]+'?'+urlencode(params)


def finish(state, code='', error=''):
    if not state or len(state)>256:raise ValueError('Invalid or expired sign-in. Start Connect cloud storage again.')
    with locked():
        pending=read('cloud-pending.json');attempt=pending.pop(state,None)
        if attempt is None:raise ValueError('Invalid or already-used sign-in. Start Connect cloud storage again.')
        # Consume before exchanging: callbacks cannot be replayed across workers.
        write('cloud-pending.json',pending)
        if time.time()-attempt['created_at']>1800:raise ValueError('Sign-in expired. Start Connect cloud storage again.')
        if error:raise ValueError('Sign-in was cancelled or declined. Your previous connection was kept.')
        if not code or len(code)>8192:raise ValueError('No valid authorization code was returned.')
        which=attempt['provider'];config=attempt['client']
        values={'grant_type':'authorization_code','code':code,'client_id':config['client_id'],
                'redirect_uri':config['redirect_uri'],'code_verifier':attempt['verifier']}
        if which=='drive':values['client_secret']=config['client_secret']
        result=token_request(which,values)
        if not result.get('refresh_token'):raise ValueError('Ongoing access was not granted. Connect again and approve offline access; your previous connection was kept.')
        if which=='dropbox':
            # Same private format as the earlier Dropbox implementation.
            write('dropbox.json',{'app_key':config['client_id'],'refresh_token':result['refresh_token']})
        else:
            write('google-drive.json',{'client_id':config['client_id'],'client_secret':config['client_secret'],
                  'refresh_token':result['refresh_token']})
        return PROVIDERS[which][0]


def drive_token():
    auth=read('google-drive.json')
    if not auth.get('refresh_token'):raise ValueError('Connect Google Drive before exporting to it.')
    values={k:auth[k] for k in ('client_id','client_secret','refresh_token')};values['grant_type']='refresh_token'
    token=token_request('drive',values).get('access_token')
    if not token:raise ValueError('Google Drive did not return access. Reconnect Google Drive.')
    return token


def status(settings):
    which=provider(settings)
    auth=read('google-drive.json' if which=='drive' else 'dropbox.json')
    name=PROVIDERS[which][0]
    if auth.get('refresh_token'):return name+' authorization is saved. Export a bundle to verify upload access.'
    if auth.get('access_token'):return name+' has a temporary connection. Use Connect cloud storage for ongoing access.'
    return name+' is not connected. Use Connect cloud storage after the one-time client setup.'
