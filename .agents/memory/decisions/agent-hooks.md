# Agent hooks: .agents/hooks + .claude manifest

Hook scripts live once in `.agents/hooks/` (tool-agnostic bash+jq).
`.claude/settings.json` is the single manifest: Claude reads it
natively, Devin and Grok via their `.claude` compat layers. No
`.devin/hooks.v1.json` - Devin reads both and hooks would fire
twice. ZCode gets its own `.zcode/config.json` (hooks.enabled).
