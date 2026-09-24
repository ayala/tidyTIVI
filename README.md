# tidyTIVI 0.4.2

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
or download [tidyTIVI-0.4.2.zip](https://github.com/ayala/tidyTIVI/releases/download/v0.4.2/tidyTIVI-0.4.2.zip)
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

## Dropbox setup

1. Create a scoped **App folder** app in the [Dropbox App Console](https://www.dropbox.com/developers/apps).
2. Enable `files.content.write`, `sharing.write`, and `sharing.read` scopes.
3. Enter only its **app key** in tidyTIVI and save settings. No app secret is needed.
4. Click **Connect Dropbox**, open the displayed link, approve access, then copy
   Dropbox's code into **One-time connection code**. Save and click Connect Dropbox
   again. The code is cleared after success; refresh the plugin page afterward.
5. Enable **Upload to Dropbox after export** and save. The default bundle path is
   ready to use. Export overwrites that file and returns the download link for
   the companion. Choose a separate path for each recipient/account configuration.

**Dropbox status** shows whether authorization is saved and the next setup step;
it does not claim a live upload has succeeded. Tokens are managed automatically
in `/data/tidytivi/dropbox.json` (owner-only permissions), outside editable plugin
settings. Existing connections migrate without requiring authorization again.
Back up this private file with your installation; never publish it. Save the app
key and start Connect again if a connection attempt expires after 30 minutes.

The plugin uses Dropbox's official [OAuth flow](https://www.dropbox.com/developers/reference/auth-types)
and [sharing API](https://docs.dropboxapi.com/dropbox-api/docs/sharing).
Recipient passwords use masked inputs and remain in Dispatcharr’s database. Dropbox authorization requires the owner's account;
no Dropbox credentials are bundled with this source or APK.

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

Version 0.4.2 passed 27 automated tests. Export, restore, logos, profile categories,
live playback, populated EPG, native Movies/Series and episode lookup were checked
on an unrooted Android TV emulator running TiviMate 5.3.3. Corrupted bundle
downloads were rejected while preserving the prior installation. Physical Fire
TV hardware and a connected Dropbox upload still need end-to-end verification.
The companion opens TiviMate’s Restore prompt; confirmation remains required.
