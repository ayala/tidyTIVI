# tidyTIVI 0.5.6

Export one native TiviMate 5.3.3 backup containing all selected Dispatcharr
profiles. Exporting/restoring requires no Android worker or root. A matching private codec seed and template must be provisioned once before native
export works. They are not distributed in this repository; this is an experimental
release for provisioned installations, not a universal backup decoder.

## Install in Dispatcharr

In Dispatcharr’s plugin repositories, add this manifest URL:

```text
https://raw.githubusercontent.com/ayala/tidyTIVI/main/manifest.json
```

Then install tidyTIVI from the repository,
or download [tidyTIVI-0.5.6.zip](https://github.com/ayala/tidyTIVI/releases/download/v0.5.6/tidyTIVI-0.5.6.zip)
and upload it through Plugins. Enable tidyTIVI, select the profiles and provider
accounts, then preview before exporting. No provider is selected automatically.
Python 3.9+ and the dependency in `requirements.txt` are required in Dispatcharr’s
Python environment. Native export also requires the private provisioning below.

## What the export contains

- One live playlist per profile: DirecTV, Sky, Movistar Plus. Each contains its
  original curated groups, such as Local, Movies, Sports and Lifestyle. All
  selected profiles are included in one backup.
- Optional combined mode uses one live playlist with prefixed profile groups.
- Direct provider streams; no remote access to Dispatcharr is required.
- Provider catch-up flags and retention are preserved per selected live stream
  in both the backup and local M3U playlists. Replacement XC accounts use their
  own advertised archive support. EPG history and actual archive playback still
  depend on the guide feed and provider.
- Curated VOD is enabled by default. Current enabled Dispatcharr movie/series
  categories, cleaned titles and assigned artwork are copied. VOD-only XC
  connections retain native Movies/Series and episode lookup without splitting
  the live-TV groups. Provider account selection scopes both live TV and VOD.
  An unselected provider is never used as a fallback. Profiles with no usable
  assigned streams are omitted and explicitly reported; a fully empty live
  selection stops the export. Replacement credentials apply to both live and VOD.
- Only EPG sources assigned to included live channels.
- Complete tidyCH GitHub logo folders, under `logos/us`, `logos/uk`, `logos/es`,
  etc. Original filenames are preserved. Exact per-channel aliases live in
  `logos/_matched`; no source-repository renaming is needed. Unavailable assigned
  image URLs are reported without dropping their channels. A failure to fetch
  the complete mapped repository folder stops the export.
- Optional replacement export credentials per provider. The source Dispatcharr
  accounts are never changed. Replacement accounts are checked for every
  exported live/movie/series ID; they must be compatible with the source
  provider's catalogue. This does not translate arbitrary providers' stream IDs.

Each export directory contains `tidytivi.tmb`, `lineup.m3u`, the country logo
folders, `manifest.json`, and `tidytivi-latest.zip`. The ZIP is the companion
app's download. Its manifest checks the size and SHA-256 of every payload file.
All these files can contain or grant access to provider credentials. Keep the
bundle and download link private.

## Dropbox sync

No app registration, public server address, or tunnel is needed for users.
Click **Docs** on the tidyTIVI card to open its local setup page. Click
**Connect Dropbox**; Dropbox opens in another tab. If your browser blocks the tab,
click **Open Dropbox** or use **Copy the full link instead**. Approve access,
copy Dropbox’s one-time code into the setup page, and click **Finish connection**.
The page uses your existing Dispatcharr login; it never needs a hardcoded server
address or a tunnel. The **Setup guide** link opens the GitHub documentation.

Enable **Upload after export**
and choose a bundle filename. Future exports renew authorization automatically
and overwrite the bundle while retaining its download link.

**Dropbox status** reports saved authorization; a successful export verifies upload
access. **Cancel connection** cancels a pending attempt without disconnecting an
existing account. Use different filenames for recipients. Keep bundle links private.
See [CLOUD-SETUP.md](CLOUD-SETUP.md) for publisher maintenance and migration details.

## Firestick companion

Download the APK from the separate [companion repository](https://github.com/ayala/tidyTIVI-companion/releases/latest).
Sideload `tidyTIVI-companion.apk` on an Android-based Fire TV with TiviMate already
installed and activated. Save the Dropbox download link once. On first use,
allow the app's requested file access. Press **Update TiviMate**: it downloads
and verifies the bundle, installs all files, scans logos, and opens TiviMate's
native restore prompt. Confirm Restore there. TiviMate also needs permission
to read the shared logo directory.

The companion requires no root and no emulator. It does not silently dismiss
TiviMate's confirmation or install/activate TiviMate itself. It retains the
previous installed bundle until the new download passes verification. Failed
or tampered downloads do not replace it. Restoring replaces TiviMate's setup,
so export all profiles you want together.

Files are installed under `/sdcard/Download/tidyTIVI/current`. The included local
`lineup.m3u` and profile-specific `lineup-ID.m3u` files make the live playlists independent of both internal
Dispatcharr and an always-running companion service. Update curation through
Dispatcharr → Export → companion Update. Automatic provider playlist refresh is
disabled. A manual refresh may overwrite VOD curation or channel settings.

VOD scanning/rules stay on Dispatcharr. The receiver gets a fresh snapshot each
export; series episodes are resolved through their provider when opened. Native
fallback streams are not added. Original channel numbers use the optional name
prefix; reliable custom native numbering has not been established.

## Private provisioning and development

`/data/tidytivi/codec-seed.json` and `/data/tidytivi/template.tmb` must match.
Python `cryptography` is required. These private files are excluded from the
plugin package. See FORMAT.md for codec scope.

Run tests with `PYTHONPATH=. python -m unittest discover -s tests -v` from this
folder. Companion source and build instructions are maintained in
[tidyTIVI-companion](https://github.com/ayala/tidyTIVI-companion).

## Verification and limits

Version 0.5.1 passed 36 automated tests. Two real exports uploaded to Dropbox with
the same download link. Companion 0.5.0 downloaded the cloud bundle on an unrooted
Android TV emulator and opened the native restore confirmation. All 823 installed
payload files matched manifest sizes and SHA-256 hashes. Export, restore, logos, profile categories,
live playback, populated EPG, native Movies/Series and episode lookup were checked
on an unrooted Android TV emulator running TiviMate 5.3.3. Corrupted bundle
downloads were rejected while preserving the prior installation. Physical Fire
TV hardware still needs end-to-end verification.
The companion opens TiviMate’s Restore prompt; confirmation remains required.

## 0.5.2 lineup ordering fix

All channels now uses ascending Dispatcharr lineup order rather than reversing
it. Category manual ordering and channel names are unchanged. Re-export and
restore the updated bundle to apply the fix; existing backups retain the old
positions. TiviMate’s displayed category counters still restart at 1.

Verified 0.5.2 with 37 passing tests and a fresh Dropbox export restored through
companion 0.6.0. The native All channels view now starts CBS, NBC, FOX, ABC, NY1,
MY 9, CW, matching the Dispatcharr lineup. Physical Fire TV remains untested.

## Uppercase channel groups

Enable **ALL CAPS channel groups** in tidyTIVI settings, then export and restore.
This optional setting defaults off and changes live-TV category labels only,
including profile groups in combined mode. For example, Sports becomes SPORTS
and En Español becomes EN ESPAÑOL. Channel names, playlist names, lineup order,
VOD categories and the source Dispatcharr configuration are unchanged. TiviMate’s
built-in All channels and Favorites labels are not renamed.

## Other logo repositories

The [tv-logo/tv-logos repository](https://github.com/tv-logo/tv-logos) is compatible
with the current folder importer and its PNG logos. Set tidyCH’s GitHub repository
to `tv-logo/tv-logos` and map the exact profile names to its country folders, e.g.:

```text
DirecTV|us|countries/united-states
Sky|uk|countries/united-kingdom
Movistar Plus|es|countries/spain
```

Channel logos must already be assigned in Dispatcharr. tidyTIVI copies each full
mapped folder and creates exact per-channel aliases from those assignments; it
does not re-match channels by filename. Mapped files are exported under paths such
as `logos/us/united-states/`, with channel aliases under `logos/_matched/`.
Only selected profiles’ mapped folders are copied, not the entire repository.
The US folder is currently approximately 44 MB and the UK folder 22 MB, so these
packs can be larger than custom profile packs. Follow the repository’s attribution
and usage terms when redistributing its logos. This compatibility check does not
change your existing logo repository or mappings.
