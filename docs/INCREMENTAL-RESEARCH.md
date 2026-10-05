# Non-destructive curation update tests — 2026-10-05

Experimental research only. The released companion still uses full backup restore.
No production export, release or receiver configuration was changed by this test.

## Tested on the non-rooted TiviMate 5.3.3 Android TV emulator

A separate local M3U test playlist was added to the existing configuration.
It initially contained Alpha Before and Beta Before with stable stream URLs
and XMLTV identifiers. Alpha Before was added to Favorites using TiviMate's UI.
The file was changed to rename both channels, reverse their order, rename their
groups and add New Gamma. Settings → Playlists → Update playlist succeeded.

- Renames, group changes, order and the new channel appeared.
- Alpha After still offered Remove from Favorites, proving its favorite survived.
- Disabling the test playlist, refreshing it, and returning to its settings left
  Enable playlist switched off. Re-enabled afterward for the next test.
- A provider movie was played and sought beyond 02:06, then stopped.
- The local live playlist was refreshed again. The movie resumed beyond that
  saved position (02:21 observed), rather than restarting at zero.
- Existing provider VOD and other live playlists remained present throughout.
- No backup restore was used. TiviMate was stopped afterward to end playback.

## Limits

These tests cover a newly added ordinary M3U playlist. They do not establish a
universal in-place merge into an existing XC playlist or an older tidyTIVI backup.
Older exports use custom_name, custom live groups and explicit EPG bindings in
the backup database. A refreshed M3U cannot be assumed to replace these overrides.
The old M3Us also use tidytivi-ID as names; they must not be presented as a ready
non-destructive import format.

A separate playlist can preserve the existing installation, but does not move
favorites from an existing playlist into the newly added one. Stream URL/account
changes, deletion/re-addition, renamed hidden groups, episode watched flags,
all appearance/playback preferences, new EPG sources and full logo behavior were
not comprehensively tested. Physical Firestick verification remains outstanding.

At this stage of the research, the codec was provisioned for one salt/header.
The subsequent findings below supersede that codec limitation.

## Existing exported playlist migration test — 2026-10-05

Saved the complete running emulator as snapshot `pre-inplace-20261005` and
copied the installed bundle to a private research directory before testing.
The existing United States playlist referenced
`file:///sdcard/Download/tidyTIVI/current/lineup-1.m3u`. Its database reported
257 channels; the older installed file contained 256 entries. This mismatch
means this was a migration compatibility test, not a synchronized export test.

Changed only the first M3U entry's display name to `INPLACE RENAME TEST`,
retaining every stream URL, XMLTV ID and group attribute. Native Update playlist
reported failure. Opening Playlist URL, entering the bare local path and
accepting it reported “Playlist is processed / Channels: 256”. TiviMate then
showed “No channels” in the existing United States All channels view.
This does not establish the internal cause or whether channel rows were
deleted versus hidden; it establishes that this migration is not safe to ship.

Loaded the saved emulator snapshot and restored the original M3U file.
Verified United States again reported 257 channels and All channels displayed
CBS, NBC, FOX, ABC, NY1, MY 9, CW and News 12 with EPG listings.
No production plugin, cloud bundle or companion release was changed.

**Release gate:** do not enable a files-only refresh for existing backup-created
playlists on the strength of ordinary-M3U tests. An in-place migration must
first pass against the actual exported database layout, preserve channel
identity and favorites, apply changed names/groups/order, and retain EPG.
Physical Firestick testing of this migration has not been performed.

## Receiver backup merge and automatic capture research

The v1 backup key derivation was verified against four independently salted
backups and a fresh stock-emulator backup. Python and Java implementations
authenticate before decoding, and encode with fresh salt and IV. No user
account credentials or per-user authorization tokens are format constants.

A merge of a fresh receiver backup retained receiver playlist/channel IDs,
favorites, disabled playlist state, movie resume records and preferences while
changing channel/group names. Restoring through a content URI on the stock
emulator displayed the renamed CBS favorite and its original EPG. This does
not yet constitute complete end-to-end companion verification.

The user rejected a manual fresh-backup step. That UI has been removed from
the experimental companion. A separate accessibility helper successfully
created a fresh native backup on the non-rooted emulator using TiviMate's UI.
The companion integration is being tested. Accessibility must be enabled once;
ADB was used to enable it on the test emulator. This is not evidence that
Fire OS exposes the same setup UI. No physical Firestick verification has
been completed. Do not publish this as a one-button production solution yet.

### Integrated companion result

The experimental companion automatically captured the stock emulator's fresh
backup, merged the actual Dropbox bundle (four profiles, 616 channels), and
opened the native Restore confirmation. No manual backup creation or selection
was used. After confirmation, native TiviMate showed CBS in Favorites, the
existing movie in History with Resume available, and United Kingdom's Enable
playlist switch still off. All non-database backup entries matched the exact
automatic receiver snapshot byte for byte. Database checks retained original
playlist IDs and enable state, existing channel favorite/watch/audio fields,
and complete movies/series/category tables. SQLite integrity was OK.

Remaining release gates include robust category identity across splits and
removals, repeated updates, interruption handling, broader personal-settings
fixtures, and physical Firestick accessibility availability. Prefix-normalized
name matching and reserved exact matches fixed the observed category conflict,
but membership heuristics alone are not a durable stable group identifier.
The experimental APK keeps version 0.6.1 and has not been published.

The home-screen tagline was removed and a 28 dp gap added between logo and
Connect. The updated layout is installed on the emulator.

### Stable categories and repeat-merge regression

New exports include `group_mappings` in the bundle manifest, keyed by Dispatcharr
profile and category IDs. The companion records their receiver database IDs
after merging, so subsequent category renames do not depend on shared channel
membership. It validates saved IDs against the receiver playlist and raw group
name, retires obsolete managed groups without deleting their personal options,
and removes stale managed memberships while retaining personal-group links.

`python3 tests/run_android_merge.py emulator-5560` in the companion checkout
builds a synthetic Android SQLite test APK. The test passed on 2026-10-05 for
repeated merges, arbitrary rename with stable ID, replacement by a distinct
category using the same name, retirement, and resurrection of the old category.
Favorites, hidden group/playlist flags, and movie resume persisted. The runner
uses a unique per-run result marker so prior log output cannot count as a pass.
The plugin's 60 tests also pass, including export mapping-to-database validation.

This metadata has not yet been deployed to Dispatcharr or published. Legacy
bundles still need a first-match migration; ambiguous legacy matches abort.
The Python research merger is a reference for the initial merge and does not
yet implement the Android merger's manifest ledger and retirement behavior.

A second complete download → automatic backup → merge → native restore was
performed against the real emulator installation. The second merged backup
retained the same playlist/channel IDs, enable flags, favorites, watch-time
and audio-offset fields, and byte-equivalent rows across the four VOD tables.
It contained 620 total channels (616 current curated, one retired, three
independent test channels), with SQLite integrity OK. Native restore was
confirmed. This real second-cycle bundle was still the legacy cloud export;
the new stable category metadata is covered by the synthetic Android tests
until an updated plugin export is generated.

### Real export and account gate

An isolated server export completed with four profiles, 616 channels, 51 stable
category mappings and 1,427 payload files. It did not replace the installed
plugin or cloud bundle. Its XC account/server differs from the emulator's
existing native VOD connection. The Android merger rejected it before mutation
as designed; do not describe this as a successful end-to-end metadata migration.
The receiving-account-versus-export-account behavior has been raised with the
user before implementing an account transition.

The exact fresh backup from the second previous update was audited against its
merged backup: 26 non-curation tables were unchanged, including episode resume,
program history, reminders, recordings, searches and the full VOD tables. All
non-database ZIP entries matched exactly. Channel full-text-search shadow
tables changed as expected when SQLite rebuilt the channel search index.

The user subsequently selected **use the account supplied in the export**.
The account gate is being replaced by a transaction that matches each exported
VOD provider to its existing receiver connection, retains native XC-ID-backed
rows and personal fields, updates movie URLs and connection credentials, adds
new catalogue entries and soft-retires unavailable entries without deleting
their saved history.

The synthetic Android account-switch regression passed, including new titles,
unavailable titles, hidden VOD categories, movie favorites/resume and episode
resume. A full real-catalogue Android merge and immediate repeat also passed:
616 curated channels, 51 category identities, 198,318 active movies and 45,860
active series. Every existing movie, series, channel and playlist ID and its
personal fields were retained. Episode progress was unchanged, the receiver XC
connection matched the exported account, and SQLite integrity passed. Native
restore/playback with that account is the next verification step; this work is
not yet released.

### End-to-end exported-account verification

The real bundle was uploaded after saving a private local restore copy of the
previous Dropbox payload. Dropbox content-hash verification passed and the
shared link was unchanged. The stock companion downloaded it, captured a fresh
TiviMate backup automatically, merged 616 channels and the exported XC account,
and opened the native Restore confirmation. Restore completed successfully.
CBS remained a favorite and played with working EPG. A movie and a series
episode also played under the exported account. A different series encountered
an emulator MediaCodecVideoDecoderException; it was not counted as playback
success.

The actual companion-produced backup retained every old channel/playlist/VOD ID
and audited personal fields, all episode progress and every non-database ZIP
entry. One previous movie was absent from the new account's provider catalogue:
its database history was retained but TiviMate hid the unavailable title.

A further complete Dropbox → automatic backup → merge → Restore cycle retained
the newly created movie and episode history. Native TiviMate displayed Resume
for the movie, Remove from My list, and Resume S1 E1 for the series. All movie,
series, category and episode-progress rows matched the fresh pre-update backup
exactly. SQLite integrity passed. Physical Firestick preservation and one-time
accessibility setup remain unverified; the companion is a preview release.
