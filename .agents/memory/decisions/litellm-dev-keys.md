# LiteLLM dev keys are repo-private defaults

The litellm-gateway spec pinned the master key dev default to
`sk-1234`. LiteLLM v1.104.0 refuses to boot on an unset, empty, or
publicly-known master key, and `sk-1234` is upstream's documented
example, so the spec value cannot boot the pinned image.

Both compose stacks therefore commit repo-private dev defaults:

- `LITELLM_MASTER_KEY`: `sk-taipan-dev-4f8a2c91e6b3d705`
- `LITELLM_SALT_KEY`: `sk-taipan-salt-9b1c64e2a8d3f704`

Same class as `POSTGRES_PASSWORD`: committed, dev-only, overridable
through the environment; production reads Railway variables. No
`LITELLM_DANGEROUSLY_PERMIT_WEAK_OR_UNSET_MASTER_KEY` anywhere. The
salt default stays stable forever: rotation has no in-place path, and
losing the salt makes stored provider credentials unreadable.

If a future LiteLLM release starts rejecting these too, generate a
fresh random hex value and commit it the same way.
