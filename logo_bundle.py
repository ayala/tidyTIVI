"""Copy complete tidyCH country folders and exact channel aliases."""
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path, PurePosixPath
import re
import time
from urllib.parse import quote
from urllib.request import Request, urlopen


def download(url):
    for attempt in range(3):
        try:
            with urlopen(Request(url,headers={'User-Agent':'tidyTIVI/0.4.0'}),timeout=45) as response:
                data=response.read(20*1024*1024+1)
            if len(data)>20*1024*1024: raise ValueError('File exceeds 20 MB.')
            return data
        except Exception:
            if attempt==2: raise ValueError('A required logo repository file could not be downloaded; export stopped.') from None
            time.sleep(attempt+1)


def build_country_logos(job, output):
    output=Path(output)
    config=job.get('logo_repository') or {}
    repo=config.get('repository','').removeprefix('https://github.com/').rstrip('/')
    if not re.fullmatch(r'[\w.-]+/[\w.-]+',repo): raise ValueError('Configure the tidyCH GitHub logo repository first.')
    try:
        metadata=json.loads(download('https://api.github.com/repos/'+repo))
        branch=metadata['default_branch']
        tree=json.loads(download('https://api.github.com/repos/'+repo+'/git/trees/'+quote(branch,safe='')+'?recursive=1'))
        if tree.get('truncated'):raise ValueError()
    except Exception:
        raise ValueError('Could not list the complete GitHub logo repository.') from None
    mappings={f['profile']:f for f in config.get('folders',[])}
    targets={}
    for profile in job['profiles']:
        mapping=mappings.get(profile['name'])
        if not mapping:raise ValueError('No tidyCH logo folder mapping for '+profile['name'])
        country=mapping.get('country','').lower()
        if not re.fullmatch('[a-z]{2,3}',country):raise ValueError('Invalid country code in tidyCH logo mapping.')
        folder=mapping['directory'].strip('/')
        if '..' in PurePosixPath(folder).parts:raise ValueError('Invalid tidyCH logo folder.')
        prefix=folder+'/'
        entries=[e['path'] for e in tree['tree'] if e['type']=='blob' and e['path'].startswith(prefix)]
        if not entries:raise ValueError('Mapped logo folder is empty for '+profile['name'])
        for path in entries:
            relative=country+'/'+PurePosixPath(folder).name+'/'+path[len(prefix):]
            url='https://raw.githubusercontent.com/'+repo+'/'+quote(branch,safe='')+'/'+quote(path,safe='/')
            if relative in targets and targets[relative]!=url:raise ValueError('Conflicting country logo paths.')
            targets[relative]=url
    channels=[c for p in job['profiles'] for c in p['channels'] if c.get('logo_url')]
    urls=list(dict.fromkeys(list(targets.values())+[c['logo_url'] for c in channels]))
    required=set(targets.values())
    def fetch(url):
        try:return url,download(url)
        except ValueError:
            if url in required:raise
            return url,None
    with ThreadPoolExecutor(max_workers=6) as pool:images=dict(pool.map(fetch,urls))
    def save(name,data):
        target=output/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data);target.chmod(0o600)
    for name,url in targets.items():save(name,images[url])
    aliases={}
    missing=[]
    for channel in channels:
        data=images[channel['logo_url']]
        if data is None:
            missing.append({'id':channel['id'],'name':channel['name'],'reason':'Assigned image URL could not be downloaded'})
            continue
        if data.startswith(b'\x89PNG\r\n\x1a\n'):ext='.png'
        elif data.startswith(b'\xff\xd8\xff'):ext='.jpg'
        elif data[:4]==b'RIFF' and data[8:12]==b'WEBP':ext='.webp'
        else:raise ValueError('Unsupported assigned logo image for channel '+str(channel['id']))
        name='_matched/tidytivi-'+str(channel['id'])+ext
        if name in aliases and aliases[name]!=data:raise ValueError('Conflicting channel logo assignments.')
        aliases[name]=data
    for name,data in aliases.items():save(name,data)
    return {'country_files':len(targets),'matched_files':len(aliases),'countries':sorted({x.split('/')[0] for x in targets}),'missing_assigned_logos':missing}
