# Dropbox connection

## Plugin users

**Already connected?** Skip sign-in. Your saved connection remains in place.

1. Save or close Settings, then click **Docs** on the **tidyTIVI card**.
2. Click **Connect Dropbox** to open authorization and approve access.
3. Paste Dropbox’s one-time code on that same setup page and click **Finish connection**.
4. Return to tidyTIVI Settings, enable **Upload after export**, and save.

If Dropbox does not open automatically, click **Open Dropbox**. You can also
expand **Copy the full link instead** to copy the complete authorization URL.
You do not need to copy anything from the notification popup.

Export your bundle, then use **Connect** in the companion to provide its download
link once. Future exports update the same link when the bundle filename is unchanged.

No app registration, client secret, callback address, localhost tunnel, or hosted
relay is required. Authorization codes expire after 30 minutes and are consumed
once. Use **Connect Dropbox** to restart or **Cancel connection** to discard an
attempt. Failed or cancelled connections preserve the previous authorization.

## Already connected: get the companion download link

Click **Docs** on the tidyTIVI card, then **Get companion link** and **Copy download link**.
Paste it into the companion’s **Connect** screen or scan its QR and paste it on
your phone. This is the bundle download link, not the Dropbox authorization URL.
No new Dropbox sign-in is required. If no link is found, export with **Upload after
export** enabled first. The lookup uses your currently configured bundle filename.

## Who handles app registration?

The tidyTIVI publisher has already registered the shared Dropbox application.
Plugin users only follow the connection steps above. Publisher-only maintenance
is documented separately in [PUBLISHER-SETUP.md](PUBLISHER-SETUP.md).
See [PRIVACY.md](PRIVACY.md) for what is stored and shared.

## Troubleshooting

- **App has few users warning:** tidyTIVI is a new Dropbox integration. Check the
  app name is tidyTIVI before continuing. This notice may appear during development.
- **No Connect button in Settings:** save or close Settings, then click **Docs** on the tidyTIVI card. The connection button is on that setup page.
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

## Older Actions workflow (optional)

The recommended steps above replace the older workflow. For compatibility,
**Actions → Connect Dropbox** still starts authorization. You can then click
**Docs** to access the complete link and finish on the setup page. Alternatively,
paste the code in **Settings → One-time connection code**, save, and choose
**Actions → Finish connection**. The code field is not needed when using the setup page.
