# TiviMate 5.3.3 backup format: verified findings

The tested files use the following envelope. Offsets are zero-based.

| Bytes | Content | Evidence |
| --- | --- | --- |
| 0 | `01` | All four original backups and a newly created backup |
| 1–16 | 16-byte salt candidate | Changes between native backups; derivation not yet recovered |
| 17–20 | Big-endian `100000` | Consistent with a password-derivation iteration count; not independently confirmed |
| 21–36 | 16-byte AES-CTR initial counter | Successfully decrypted the complete ZIP |
| 37 through 33 bytes before EOF | AES-256-CTR encrypted ZIP | ZIP entry CRCs verified |
| Last 32 bytes | HMAC-SHA256 of all preceding file bytes | Verified with the same 32-byte key used for AES |

The ZIP contains `ar.tvplayer.tv_preferences.xml`,
`ar.tvplayer.tv_playlist_categories_prefs.xml`, and `TvPlayer.db` in the tested
backup. Preserve preference files when replacing the database.

## Independently generated backup proof

A derived 256-bit key was recovered from the authorized research app's memory
while it produced a backup. No premium activation mechanism was modified.

Python then authenticated and decrypted that backup, changed one channel's
`custom_name` in SQLite, rebuilt the ZIP, encrypted it using the same 21-byte
header and a fresh random 16-byte initial counter, and appended a newly computed
HMAC. Stock, unrooted TiviMate 5.3.3 restored the resulting file and displayed
`tidyTIVI Standalone Proof` in the channel guide.

Root was needed for this initial research/provisioning step. Neither export nor
recipient restoration needs root or an Android worker after provisioning.

## Scope

The original password/key-derivation procedure has NOT been recovered. The
codec seed pairs one known header with its corresponding derived key. It can
produce arbitrarily many backups with that header and fresh random initial
counters. It cannot decode arbitrary native backups with different salts.

The seed and matching template are private installation files, excluded from
source and release packages. This is tested against version 5.3.3, database
schema 60. Compatibility with other versions or account contexts is untested.
