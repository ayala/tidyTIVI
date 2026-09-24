# tidyTIVI Dropbox integration privacy

The tidyTIVI Dispatcharr plugin connects directly to Dropbox to upload the backup
and logo bundle you export. Access is limited to the app folder. The integration
requests permissions to write its files and create or reuse download links.
Dropbox also includes basic account information permission; tidyTIVI does not
use that information for advertising or analytics.

Authorization tokens are stored privately on your Dispatcharr server. The
publisher does not operate an authorization relay or receive your tokens,
backups, provider credentials, or download links. Dropbox processes data under
its own policies. The companion downloads the bundle directly from its cloud
link and stores the link and installed files on your device.

The exported bundle contains the provider credentials you selected. Its shared
link permits access to anyone who possesses it. Keep it private. Revoke a shared
link through Dropbox to stop future downloads; this does not erase prior copies.
You can revoke tidyTIVI access in Dropbox's Connected apps settings. Revocation
stops future authorized uploads; existing shared links must be removed separately.

For integration questions, use the repository's GitHub issues. Do not include
credentials, backups, private links, or authorization codes in public reports.
