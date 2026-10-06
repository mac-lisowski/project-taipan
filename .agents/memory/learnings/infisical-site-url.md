# Infisical SITE_URL needs the https:// scheme

Bare domain (`host.up.railway.app`) crashes WebAuthn init with
`TypeError: Invalid URL` at boot. Server never binds the port, so
Railway 502s while the deploy still reports SUCCESS. Fix: set SITE_URL
to the full `https://` URL.
