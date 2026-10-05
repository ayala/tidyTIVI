# TiviMate 5.3.3 backup format: verified findings

The tested files use the following envelope. Offsets are zero-based.

| Bytes | Content | Evidence |
| --- | --- | --- |
| 0 | `01` | All four original backups and a newly created backup |
| 1–16 | 16-byte random salt | Verified against independently salted native backups |
| 17–20 | Big-endian `100000` | PBKDF2-HMAC-SHA256 iteration count, independently verified |
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

## Native key derivation

The v1 derivation was recovered and verified in October 2026 against four
independently salted backups and fresh backups from stock TiviMate 5.3.3.
The key is PBKDF2-HMAC-SHA256 with 100,000 iterations and 32 output bytes.
Its salt is the header's 16 random bytes followed by the application's fixed
16-byte format suffix. The format password and suffix are interoperability
constants, not a user's account password, activation token or Dropbox token.
The native Python and Java codecs authenticate the envelope before using the
payload and encode new backups with fresh random salt and IV.

Legacy provisioned header/key pairs remain supported by the plugin exporter.
Existing seed and template files stay private and are never included in release
packages. The native decoder does not require a per-receiver seed or root.

## Preservation scope

A receiving device's fresh native backup is the authoritative source of its
personal state. The experimental companion merges curation into a disposable
copy, retains receiver IDs and preference files, and hands the resulting backup
to stock TiviMate's native Restore confirmation. A publisher's original backup
alone cannot preserve newer receiver history.

The automatic capture prototype uses a user-enabled accessibility service.
It has been tested on the Android TV emulator; physical Firestick setup and
compatibility remain unverified. See [research evidence](docs/INCREMENTAL-RESEARCH.md).
These findings cover TiviMate 5.3.3, database schema 60, and the v1 envelope only.
