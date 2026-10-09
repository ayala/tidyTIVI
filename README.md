# tidyTIVI 0.5.13

Export one native TiviMate 5.3.3 backup containing all selected Dispatcharr
profiles. Exporting/restoring requires no Android worker or root. A matching private codec seed and template must be provisioned once before native
export works. They are not distributed in this repository; this is an experimental
release for provisioned installations. The research codec now also supports
independently generated 5.3.3 backups; exporter template provisioning remains
required.

## Install in Dispatcharr

In Dispatcharr’s plugin repositories, add this manifest URL:

```text
https://raw.githubusercontent.com/ayala/tidyTIVI/main/manifest.json
```

Then install tidyTIVI from the repository,
or download [tidyTIVI-0.5.13.zip](https://github.com/ayala/tidyTIVI/releases/download/v0.5.13/tidyTIVI-0.5.13.zip)
and upload it through Plugins. Enable tidyTIVI, select the profiles and provider
accounts, then preview before exporting. No provider is selected automatically.
Python 3.9+ and the dependency in `requirements.txt` are required in Dispatcharr’s
Python environment. Native export also requires the private provisioning below.

## Source selection and XC priority

**XC priority is an order, not a rating, percentage or channel limit.** The default
`100` is just a starting value. It only matters when a curated channel has assigned
streams from more than one enabled XC provider:

- Lower numbers win: Trex `1` is preferred over Strong `2`.
- Equal numbers follow that channel’s Dispatcharr stream order.
- With only one XC provider enabled, leaving `100` is fine.
- Disabled providers are never selected, regardless of their priority number.

Selected XC streams take precedence over direct M3U/custom streams. If no selected
XC stream is assigned, tidyTIVI uses an eligible direct stream in Dispatcharr
stream order. This choice happens during export; it is not playback failover.

**Include provider: custom** controls standalone, manually added streams.
Dispatcharr creates a locked internal `custom` account for these one-off URLs;
it is not an M3U playlist that you have to create or import. Leave this toggle
and **Include custom and M3U fallback streams** enabled to include those channels
when they belong to your selected profiles. Streams stored without any account
are also eligible when the fallback setting is enabled.

When adding another FAST M3U source (for example GL or Rakuten), assign its streams
to channels in your Dispatcharr profiles, reopen tidyTIVI settings, enable that
source’s **Include provider** toggle, save, and export. Sources are discovered
dynamically; provider names are not hardcoded. Only the channels in your selected
profiles are exported, not the entire FAST catalogue. The unfiltered **Master**
playlist option applies to XC providers only.

Direct streams retain their external URLs and do not use the export XC credentials
or Dispatcharr’s playback proxy. Known private/local addresses are excluded; the
URLs must work from the receiving device’s network.

## What the export contains

- One live playlist per profile: DirecTV, Sky, Movistar Plus. Each contains its
  original curated groups, such as Local, Movies, Sports and Lifestyle. All
  selected profiles are included in one backup.
- Optional combined mode uses one live playlist with prefixed profile groups.
- Selected XC providers are preferred over M3U/custom streams. Set **XC priority**
  per account: lower numbers win; equal priority follows Dispatcharr stream order.
  Select the non-XC **Include provider** sources you want to use for FAST/custom
  fallback. **Include custom and M3U fallback streams** is on by default; unselected
  M3U accounts are never used. Custom streams without an account can be included.
  Known private/local HTTP addresses are reported as excluded. Other direct URLs
  must be independently reachable by the receiver; expiring links may need a new
  export. XC credential overrides never rewrite direct M3U/FAST URLs.
- **Include hidden provider master playlists** is on by default. Each selected XC
  account gets a separate **Provider · Master** native live-TV connection with its
  complete, unfiltered live catalogue and original category names. It starts
  disabled and excluded from global All channels/favorites. Enable it under
  **TiviMate → Settings → Playlists** when needed; native updates fetch future
  provider changes. It uses the final recipient XC credentials. Movies/Series
  stay in their existing full-provider VOD connections; no duplicate VOD library.
  This option does not add additional EPG source URLs.
  **Keep my settings requires companion 0.7.0-rc.5 or later** to add/maintain
  master playlists. Existing enabled state, favorites and native updates are
  preserved by that companion; older companions do not import these masters.
- Direct provider streams; no remote access to Dispatcharr is required.
- Provider catch-up flags and retention are preserved per selected live stream
  in both the backup and local M3U playlists. Replacement XC accounts use their
  own advertised archive support. EPG history and actual archive playback still
  depend on the guide feed and provider.
- Full original XC Movies and Series are always included from each selected
  provider, using the recipient credentials when supplied. Dispatcharr VOD
  filters, renamed categories, titles and artwork are not applied. VOD-only XC
  playlists retain provider category IDs and enable native playlist updates,
  including newly added categories. There is no curated VOD toggle.
  Provider account selection scopes both live TV and VOD.
  An unselected provider is never used as a fallback. Profiles with no usable
  assigned streams are omitted and explicitly reported; a fully empty live
  selection stops the export. Replacement credentials apply to XC live and VOD; direct FAST/M3U URLs keep their own access details.
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
Dispatcharr → Export → companion Update. Automatic refresh is disabled for the
curated live playlists and enabled for the separate native XC VOD playlists.
Movies and series update directly from the provider in TiviMate; no new export
or companion update is needed for new provider content. Series episodes are
resolved through the provider when opened. TiviMate must run and refresh its
playlists to receive updates.

Dispatcharr/tidyVOD curation remains local. Testing in TiviMate 5.3.3 showed
that changing an original VOD category's name in a backup is overwritten on
playlist refresh. tidyTIVI therefore preserves original provider names. Native
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

### Exported profile and category names

Each profile has optional **exported playlist name** and **channel group prefix**
settings. For Sky, a playlist name of `United Kingdom` and prefix `UK:` exports
`UK: Local` from either `Local` or `Sky: Local`. An existing `UK:` is not duplicated.
Blank fields preserve the original names. ALL CAPS is applied after prefixing.
These settings do not rename Dispatcharr profiles, channels, or tidyCH logo mappings.
Save the settings and export a fresh bundle, then update and restore on the receiver.

## Background exports

**Export bundle** starts a background process so a large XC catalog or Dropbox upload cannot time out the browser request. Use **Actions → Export status**, or open **Docs** for automatically refreshed progress. A second click while an export is running does not start another export. Wait for **Export complete / Dropbox updated** before updating the companion. Restarting Dispatcharr interrupts an active export; start it again afterward.

Export stages and completion/failure appear automatically as Dispatcharr popups. The latest export status is also retained in the notification bell for administrators, including after a page reload. You do not need to run Export status to receive completion.

## Preserving receiver history (companion preview)

Plugin 0.5.13 includes stable profile/category identities for the
[0.7.0-rc.5 companion preview](https://github.com/ayala/tidyTIVI-companion/releases/tag/v0.7.0-rc.5).
The preview updates existing tidyTIVI playlists in place using a fresh receiver
backup, preserving favorites, watch progress, hidden playlists/groups and
personal preferences. Dispatcharr curation and the account supplied in the
export take precedence. Matching VOD uses the provider's native XC IDs; titles
unavailable to the exported account retain their stored history but are hidden
by TiviMate. Different providers' IDs are not interchangeable.

The flow remains export → Dropbox → companion Update → native TiviMate Restore.
Choose **Keep my settings** to create a fresh backup in TiviMate under
**Settings → General → Back up data → Internal shared storage → Save**, then
return to the companion. It detects that new backup and merges your export.
**Replace everything** skips this step. No Accessibility permission or root is
required. The preview targets TiviMate 5.3.3 and existing tidyTIVI profile
playlists; ambiguous matches stop the update. The stable 0.6.1
companion still uses replacement restore; installing plugin 0.5.13 alone does
not add preservation to that older APK.

## Connect with a setup file

Requires companion **0.7.0-rc.6 or later**. After uploading an export to Dropbox,
open **Docs** on the tidyTIVI card and click **Download setup file**. Send
`tidytivi-setup.json` to the recipient privately and save it in Files on their phone.
On the TV, open **Connect**, scan its QR with a phone on the same Wi-Fi, and tap
**Choose setup file**. Selecting the file connects automatically; no URL paste
or cloud login is needed. Future updates use the saved link.

The file contains the permanent bundle link, not the backup or logos. Anyone with
it can download the export, so do not publish it. If you change the bundle link,
create a new setup file and connect again. Manual link entry remains available.
