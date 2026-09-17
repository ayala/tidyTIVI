"""Build exact per-channel local logos from Dispatcharr's assigned image URLs."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen
import zipfile
import time


def build_logo_pack(profile, output):
    channels = [c for c in profile['channels'] if c.get('logo_url')]
    urls = list(dict.fromkeys(c['logo_url'] for c in channels))
    def fetch(url):
        for attempt in range(3):
            try:
                with urlopen(Request(url, headers={'User-Agent':'Mozilla/5.0 tidyTIVI/0.3.2'}), timeout=45) as response:
                    data = response.read(10 * 1024 * 1024 + 1)
                if len(data) > 10 * 1024 * 1024:
                    raise ValueError('oversized image')
                if data.startswith(b'\x89PNG\r\n\x1a\n'): extension = '.png'
                elif data.startswith(b'\xff\xd8\xff'): extension = '.jpg'
                elif data[:4] == b'RIFF' and data[8:12] == b'WEBP': extension = '.webp'
                else: raise ValueError('unsupported image')
                return data, extension
            except Exception as exc:
                if attempt == 2:
                    ids = ', '.join(str(c['id']) for c in channels if c['logo_url'] == url)
                    raise ValueError('Assigned logo download failed for channel IDs '+ids+' ('+type(exc).__name__+').') from None
                time.sleep(attempt + 1)
    with ThreadPoolExecutor(max_workers=6) as pool:
        images = dict(zip(urls, pool.map(fetch, urls)))
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as archive:
        for channel in channels:
            data, extension = images[channel['logo_url']]
            archive.writestr('logos/tidytivi-'+str(channel['id'])+extension, data)
    Path(output).chmod(0o600)
    return len(channels)
