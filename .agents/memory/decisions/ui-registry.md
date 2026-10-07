# UI components come from shadcn registries

Web UI primitives come from the official shadcn registry in the
`base-nova` style (Base UI primitives). reui.io is registered as a
second registry `@reui` in `apps/web/components.json` for composites
(blocks, data tables). Bare primitives stay on official shadcn; reUI
defers them there by design. reUI pro items return 401 without a
license. Only product-specific display pieces (Panel, Stat,
Sparkline) are written by hand.

Chosen 2026-10-08 after the user rejected hand-rolled primitives.
Options considered: reUI (chosen add-on), HeroUI v3, daisyUI 5,
MUI/Mantine/AntD (rejected: clash with Tailwind tokens + design).
