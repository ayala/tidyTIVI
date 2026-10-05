"""TiviMate v1 backup-envelope interoperability parameters.

These are application-format constants, not an XC account, Dropbox token,
private provisioned backup key, or user password. A per-file key is derived
from its salt. Never treat TMB encryption as recipient access control.
"""
PASSWORD_UTF16_HEX = '020030006200300060000d001600190037002a002f00020062000600040001001c000d00020001004000020004006c00040037000600'
SALT_SUFFIX_HEX = '6b39486d3478527051326e5662543777'
