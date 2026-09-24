"""Build the public plugin ZIP and Dispatcharr repository manifest."""
from pathlib import Path
import datetime, hashlib, json, zipfile
root=Path(__file__).resolve().parent.parent
import sys
sys.path.insert(0,str(root))
from dropbox_upload import PUBLISHER_APP_KEY
if not PUBLISHER_APP_KEY: raise SystemExit('Publisher Dropbox app key is required before packaging.')
meta=json.loads((root/'plugin.json').read_text()); version=meta['version']
release=root/'releases'/('v'+version); release.mkdir(parents=True,exist_ok=True)
archive=release/f'tidyTIVI-{version}.zip'
files=['__init__.py','plugin.py','plugin.json','database.py','exporter.py','tmb_codec.py',
       'logos.py','logo_bundle.py','accounts.py','vod.py','dropbox_upload.py',
       'CLOUD-SETUP.md','PUBLISHER-SETUP.md','PRIVACY.md','requirements.txt','README.md','FORMAT.md','logo.png','logo.svg','LICENSE']
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
    for name in files:z.write(root/name,'tidytivi/'+name)
blob=archive.read_bytes(); sha=hashlib.sha256(blob).hexdigest()
(release/'SHA256SUMS').write_text(f'{sha}  {archive.name}\n')
entry=dict(slug='tidytivi',name='tidyTIVI',description=meta['description'],author=meta['author'],
           latest_version=version,last_updated=datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
           license=meta['license'],repo_url=meta['repo_url'],latest_url=archive.relative_to(root).as_posix(),
           latest_sha256=sha,latest_md5=hashlib.md5(blob).hexdigest(),latest_size=(len(blob)+1023)//1024,
           icon_url='logo.png',min_dispatcharr_version=meta['min_dispatcharr_version'])
manifest=dict(registry_name='tidyTIVI Plugin Repo',registry_url=meta['repo_url'],
              root_url='https://raw.githubusercontent.com/ayala/tidyTIVI/refs/heads/main',plugins=[entry])
(root/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(archive)
