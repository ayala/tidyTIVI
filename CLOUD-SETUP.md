# Cloud connection setup

Choose Dropbox or Google Drive, click **Connect cloud storage**, open the returned
sign-in link, and approve access. The browser returns automatically; no code or
token needs to be pasted. Authorization is retained privately on the Dispatcharr
server for future exports. You can connect both services and select which receives
the next export. Switching services produces a different companion download link.

## One-time registration (installation owner)

The public plugin does not ship OAuth client credentials. Register a Dropbox app
and/or a Google OAuth client once for this installation, then provision
`/data/tidytivi/cloud-clients.json`, owned by the Dispatcharr user, mode `0600`:

```json
{
  "dropbox": {
    "client_id": "YOUR_DROPBOX_APP_KEY",
    "redirect_uri": "http://127.0.0.1:19191/api/plugins/tidytivi/cloud/callback/"
  },
  "drive": {
    "client_id": "YOUR_GOOGLE_WEB_CLIENT_ID",
    "client_secret": "YOUR_GOOGLE_CLIENT_SECRET",
    "redirect_uri": "http://127.0.0.1:19191/api/plugins/tidytivi/cloud/callback/"
  }
}
```

The exact return URL must also be registered with the provider. The route is
installed in each Dispatcharr web worker by plugin discovery; restart the web
workers once after installing this version if the callback is not found.

**Dropbox:** Create a scoped App folder app at
https://www.dropbox.com/developers/apps. Enable `files.content.write`,
`sharing.read`, and `sharing.write`. Register the return URL above. The plugin uses
PKCE and does not need an app secret. Existing Dropbox authorizations remain usable.

**Google Drive:** In Google Cloud, enable the Drive API, configure the OAuth consent
screen, and create a **Web application** OAuth client with the return URL above.
The requested scope is `https://www.googleapis.com/auth/drive.file`, limited to
files made/opened by this app. Add your account as a test user while testing.
External apps left in Google's Testing publishing status generally receive
refresh tokens that expire after seven days for this scope; configure production
publishing appropriately for ongoing unattended use. Follow any review requirements
shown by Google rather than assuming a test connection is permanent.

Google references: https://developers.google.com/identity/protocols/oauth2/web-server
and https://developers.google.com/identity/protocols/oauth2#expiration

## Internal HTTP server: temporary localhost connection

Google does not accept a plain HTTP private-IP return URL. You do not need to
publish Dispatcharr to the internet. On the computer where you will sign in, open
an SSH tunnel to the Dispatcharr host:

```sh
ssh -N -L 127.0.0.1:19191:127.0.0.1:9191 YOUR_DISPATCHARR_SSH_HOST
```

Keep it running until the browser says the connection succeeded. Sign in through
that computer's browser; `127.0.0.1` refers to that same computer. Close the tunnel
afterward. Automatic exports and Firestick downloads do not use the tunnel.
An existing HTTPS hostname reachable by your browser is another option; register
its exact callback URL instead. The Firestick does not need this setup.

## Export and receive

Save the cloud provider, filename, and **Upload after export** setting. Export a
bundle; the result includes an unlisted download URL. Copy it to the companion
once. Use companion 0.5.0 or later for Drive links and download confirmation pages.
Use separate filenames for recipients. Dropbox retains the legacy destination
folder if one was configured. Drive manages an app-created ZIP by filename and
updates its file ID in place to retain its link. Duplicate managed filenames are
rejected instead of overwriting an arbitrary file.

The bundle contains provider credentials. The generated link grants file access to
anyone who has it; do not post it publicly. Drive organizational policy or download
quotas can prevent sharing/downloads. SHA checks in the receiver validate the
bundle after either service delivers it. Cloud failures keep the local export.

## Private state and rollback

Back up `/data/tidytivi/cloud-clients.json`, `google-drive.json`, and `dropbox.json`
privately. Pending authorization attempts expire after 30 minutes and are consumed
once; failed/cancelled reconnections leave the previous connection intact. State
is independent of editable plugin settings. Never commit these files to GitHub.
The existing 0.4.2 Dropbox copy/paste flow remains callable for compatibility but
is replaced by the common cloud actions in the UI.

## Validation limits

OAuth exchanges and upload behavior are covered with mocked provider responses.
The callback is tested through Dispatcharr, and the companion's Drive link parser
has local tests. Real Google/Dropbox consent, account uploads and physical Fire TV
downloads still require end-to-end verification after registration and sign-in.
