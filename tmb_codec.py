"""TiviMate 5.3.3 codec for a privately provisioned header/key pair.

This is NOT a universal decoder: backups with a different salt require their
own key. Reuse the provisioned salt and a fresh random CTR IV for each export.
No Android runtime is required. Do not commit or publicly distribute seed files.
"""
import io
import hmac
import json
import os
from pathlib import Path
import zipfile
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes


def load_seed(path):
    data = json.loads(Path(path).read_text())
    if data.get('schema') != 'tidytivi.codec-seed.v1' or data.get('target_version') != '5.3.3':
        raise ValueError('Unsupported codec seed.')
    header, key = bytes.fromhex(data['header']), bytes.fromhex(data['key'])
    if len(header) != 21 or header[0] != 1 or len(key) != 32:
        raise ValueError('Unsupported TiviMate envelope or key length.')
    return header, key


def validate_zip(payload):
    try:
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            if 'TvPlayer.db' not in archive.namelist() or archive.testzip() is not None:
                raise ValueError('Invalid TiviMate ZIP payload.')
    except zipfile.BadZipFile:
        raise ValueError('Invalid TiviMate ZIP payload.') from None


def decode(blob, seed):
    header, key = seed
    if len(blob) < 69 or blob[:21] != header:
        raise ValueError('This backup uses a different salt/header; the provisioned key cannot decode it.')
    if not hmac.compare_digest(hmac.digest(key, blob[:-32], 'sha256'), blob[-32:]):
        raise ValueError('Backup authentication failed.')
    decryptor = Cipher(algorithms.AES(key), modes.CTR(blob[21:37])).decryptor()
    payload = decryptor.update(blob[37:-32]) + decryptor.finalize()
    validate_zip(payload)
    return payload


def encode(payload, seed):
    validate_zip(payload)
    header, key = seed
    iv = os.urandom(16)
    encryptor = Cipher(algorithms.AES(key), modes.CTR(iv)).encryptor()
    body = header + iv + encryptor.update(payload) + encryptor.finalize()
    return body + hmac.digest(key, body, 'sha256')
