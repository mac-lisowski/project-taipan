# `bl` on PATH is Blaxel, not Bailian

- `~/.local/bin/bl` is the Blaxel CLI (sandboxes/agents). It shadows the
  Bailian CLI.
- Bailian `bl` lives at `~/.nvm/versions/node/v24.18.0/bin/bl` (v2.1.0,
  upgraded from 0.1.108 on 2026-10-05). Call it by full path or it hits
  Blaxel.
- npm global prefix is `~/.local`, so `npm i -g bailian-cli` collides with
  the Blaxel binary. Install with
  `--prefix ~/.nvm/versions/node/v24.18.0` instead.
- Bailian image generation adds an "AI 生成" watermark by default;
  `bl config set --key watermark --value false` disables it, or crop.
