import { fileURLToPath } from "node:url";
import { defineConfig } from "vitest/config";

export default defineConfig({
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
  test: {
    // Build output carries stale copies of the source tree; only src
    // is under test.
    exclude: ["**/node_modules/**", "**/dist/**", "**/.next/**"],
  },
});
