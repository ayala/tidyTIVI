"""TiviMate 5.3.3 authenticated backup-envelope codec.

Native v1 backups use PBKDF2-HMAC-SHA256 with a per-file salt and a format
salt suffix, AES-256-CTR and HMAC-SHA256. Legacy provisioned seeds remain
supported for existing installations. Never distribute user seed files.
"""
import io
import hmac
import hashlib
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


def derive_seed(blob):
    """Derive a key from a v1 envelope without a device or account seed."""
    from .tmb_format import PASSWORD_UTF16_HEX, SALT_SUFFIX_HEX
    if len(blob) < 69 or blob[0] != 1:
        raise ValueError('Unsupported TiviMate envelope.')
    iterations = int.from_bytes(blob[17:21], 'big')
    if iterations != 100000:
        raise ValueError('Unsupported TiviMate derivation parameters.')
    password = bytes.fromhex(PASSWORD_UTF16_HEX).decode('utf-16le').encode('utf-8')
    key = hashlib.pbkdf2_hmac('sha256', password, blob[1:17] + bytes.fromhex(SALT_SUFFIX_HEX), iterations, 32)
    return blob[:21], key


def decode_native(blob):
    return decode(blob, derive_seed(blob))


def encode_native(payload):
    header = b'\x01' + os.urandom(16) + (100000).to_bytes(4, 'big')
    return encode(payload, derive_seed(header + bytes(48)))
