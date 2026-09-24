"""Update an app-created Drive ZIP in place, verify it, then create an unlisted link."""
import hashlib
import json
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode,urlparse
from urllib.request import Request,urlopen
from .cloud_auth import drive_token


def upload_bundle(path, settings):
    path=Path(path);name=str(settings.get('cloud_filename') or 'tidytivi-latest.zip').strip()
    if not name.endswith('.zip') or '/' in name or '\\' in name or len(name)>200:
        raise ValueError('Google Drive bundle name must be a .zip filename without folders.')
    token=drive_token()
    def call(url,method='GET',data=None,headers=None,raw=False):
        h={'Authorization':'Bearer '+token};h.update(headers or {})
        body=data
        if isinstance(data,dict):body=json.dumps(data).encode();h['Content-Type']='application/json'
        try:
            with urlopen(Request(url,data=body,headers=h,method=method),timeout=120) as r:
                content=r.read()
                return (r.status,dict(r.headers),content) if raw else (json.loads(content) if content else {})
        except HTTPError as ex:
            if raw and ex.code==308:return (308,dict(ex.headers),b'')
            raise ValueError('Google Drive request failed. The local export is intact; check account access, sharing policy and storage.') from None
        except Exception:raise ValueError('Google Drive could not be reached. The local export is intact.') from None
    api='https://www.googleapis.com/drive/v3/files'
    escaped=name.replace('\\','\\\\').replace("'","\\'")
    query="trashed = false and name = '"+escaped+"' and appProperties has { key='tidytivi' and value='bundle-v1' }"
    found=call(api+'?'+urlencode({'q':query,'fields':'files(id)','pageSize':2})).get('files',[])
    if len(found)>1:raise ValueError('More than one managed Drive bundle has this name. Choose a unique bundle filename.')
    existing=found[0]['id'] if found else None
    url='https://www.googleapis.com/upload/drive/v3/files'+('/'+existing if existing else '')+'?'+urlencode({'uploadType':'resumable','fields':'id,size,md5Checksum,webContentLink'})
    metadata={} if existing else {'name':name,'mimeType':'application/zip','appProperties':{'tidytivi':'bundle-v1'}}
    _,headers,_=call(url,'PATCH' if existing else 'POST',metadata,{'X-Upload-Content-Type':'application/zip','X-Upload-Content-Length':str(path.stat().st_size)},True)
    session=next((v for k,v in headers.items() if k.lower()=='location'),'')
    parsed=urlparse(session)
    if parsed.scheme!='https' or parsed.hostname not in ('www.googleapis.com','content.googleapis.com') or parsed.username:
        raise ValueError('Google Drive returned an invalid upload session.')
    size=path.stat().st_size
    if not size:raise ValueError('Cannot upload an empty bundle.')
    result=None;digest=hashlib.md5();offset=0
    with path.open('rb') as source:
        while offset<size:
            chunk=source.read(8*1024*1024);digest.update(chunk);end=offset+len(chunk)
            status,h,body=call(session,'PUT',chunk,{'Content-Type':'application/zip','Content-Range':f'bytes {offset}-{end-1}/{size}'},True)
            if end<size:
                acknowledged=next((v for k,v in h.items() if k.lower()=='range'),'')
                if status!=308 or acknowledged!=f'bytes=0-{end-1}':raise ValueError('Google Drive upload was interrupted; retry the export.')
            elif status in (200,201):result=json.loads(body)
            else:raise ValueError('Google Drive did not finish the upload; retry the export.')
            offset=end
    if not result or result.get('md5Checksum')!=digest.hexdigest() or int(result.get('size',-1))!=size:
        raise ValueError('Google Drive uploaded content verification failed.')
    fid=result['id']
    permissions=call(api+'/'+fid+'/permissions?fields=permissions(id,type,role,allowFileDiscovery)').get('permissions',[])
    if not any(p.get('type')=='anyone' and p.get('role')=='reader' for p in permissions):
        call(api+'/'+fid+'/permissions','POST',{'type':'anyone','role':'reader','allowFileDiscovery':False})
    info=call(api+'/'+fid+'?fields=webContentLink')
    link=info.get('webContentLink','')
    p=urlparse(link)
    if p.scheme!='https' or p.hostname not in ('drive.google.com','drive.usercontent.google.com'):
        raise ValueError('Google Drive did not provide a supported download link.')
    return {'status':'ok','provider':'Google Drive','file_id':fid,'download_url':link,'bytes':size}
