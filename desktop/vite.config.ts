import { fileURLToPath, URL } from "node:url";
import { defineConfig } from "vitest/config";
import react, { reactCompilerPreset } from "@vitejs/plugin-react";
import babel from "@rolldown/plugin-babel";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [react(), babel({ presets: [reactCompilerPreset()] }), tailwindcss()],
  resolve: {
    alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) },
  },
  build: { outDir: "dist" },
  server: {
    // Same-origin dev: the renderer fetches relative paths; vite forwards to the sidecar.
    proxy: Object.fromEntries(
      ["/jobs", "/library"].map((p) => [p, { target: "http://127.0.0.1:8765", changeOrigin: true }]),
    ),
  },
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    css: true,
  },
});
