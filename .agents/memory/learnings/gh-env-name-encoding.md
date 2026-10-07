# gh --env 404s on environment names with spaces and slashes

The deploy environment is named `project-taipan / dev`. `gh secret
list --env "project-taipan / dev"` fails with HTTP 404: gh encodes
the spaces as %20 but leaves the slash raw, so the URL path splits at
the wrong place. Raw `gh api` calls work when the whole name is
encoded as `project-taipan%20%2F%20dev`.

Setting secrets through the raw API needs sealed-box encryption:
GET `.../environments/<env>/secrets/public-key`, encrypt with pynacl
`SealedBox`, PUT `{"encrypted_value", "key_id"}`. `uv run --with
pynacl python` covers it. Reading variables needs no encryption:
GET `.../variables` returns values.
