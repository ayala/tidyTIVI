# Dropbox connection

## Plugin users

1. Open **Actions → Connect Dropbox** and open its sign-in link.
2. Approve tidyTIVI access to its dedicated Dropbox app folder.
3. Copy the displayed code into **Settings → One-time connection code**, then save.
4. Open **Actions → Finish connection**.
5. Enable **Upload after export**, save, and export. Enter the resulting download
   link in the companion once. Later exports retain that link for the same file.

No app registration, client secret, callback address, localhost tunnel, or hosted
relay is required. Authorization codes expire after 30 minutes and are consumed
once. Use **Connect Dropbox** to restart or **Cancel connection** to discard an
attempt. Failed or cancelled connections preserve the previous authorization.

## Who handles app registration?

The tidyTIVI publisher has already registered the shared Dropbox application.
Plugin users only follow the connection steps above. Publisher-only maintenance
is documented separately in [PUBLISHER-SETUP.md](PUBLISHER-SETUP.md).
See [PRIVACY.md](PRIVACY.md) for what is stored and shared.

## Troubleshooting

- **App has few users warning:** tidyTIVI is a new Dropbox integration. Check the
  app name is tidyTIVI before continuing. This notice may appear during development.
- **No Connect button in Settings:** save and switch to the **Actions** tab.
- **Expired or already-used code:** start Connect Dropbox again and use the new code.
- **Saved authorization but upload fails:** keep the local export, check Dropbox
  storage and authorization, then retry. Status alone does not verify an upload.

## Migration and private state

Existing Dropbox connections retain their original app keys and saved refresh
tokens. New sign-ins use the shared publisher key. Legacy explicit app-key settings
remain supported for compatibility, but are not exposed to ordinary users.
An installation previously selecting Google Drive has automatic upload disabled
on migration. Connect Dropbox, then explicitly enable upload. Google resources
and existing private Google authorization files are not deleted.

Back up `/data/tidytivi/dropbox.json` privately. It contains renewable authorization
and is stored with owner-only permissions. Never publish it. User tokens remain
on Dispatcharr; the companion receives only a download link. Cloud uploads go
directly from Dispatcharr to Dropbox. No additional service handles user files.

The bundle contains provider credentials. Anyone possessing its shared link can
read it; keep it private. Failed uploads preserve the local export. Bundle size
and SHA-256 checks protect the companion installation against incomplete files.
