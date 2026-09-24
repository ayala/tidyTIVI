# Publisher maintenance — not required for plugin users

The distribution contains tidyTIVI's public Dropbox app key, not an app secret.
The publisher maintains one Scoped App with App folder access, public clients
(PKCE) allowed, and files.content.write, sharing.read, sharing.write scopes.
No redirect URI is needed. Enable additional users in the Dropbox app console.
Dropbox development status has user limits; follow its production review process
as adoption grows. Production approval must not be claimed before it is granted.
See https://docs.dropboxapi.com/dropbox-api/docs/developer-resources/developer-guide


The shared tidyTIVI app has been registered and additional users enabled. It is
currently in development status, not production-approved. Its public app key is
included in the plugin. No user should be directed to this setup document merely
to connect Dropbox. Dropbox currently requires production review as the app
reaches 50 linked users; the console may display a 500-user development limit.
Maintain the privacy-policy URL and app branding in the console.
