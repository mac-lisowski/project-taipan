# next typegen before tsc on clean checkout

Next 16 emits `LayoutProps`/`PageProps` global types into
`.next/types` only. On a clean checkout `tsc --noEmit` fails
(TS2304). Run `pnpm exec next typegen` before `tsc`; it is fast.
