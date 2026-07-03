import { z } from "zod";

const Env = z.object({
  // Sidecar base URL — Electron main injects the real port; default for `vite dev`.
  VITE_API_BASE_URL: z.url().default("http://127.0.0.1:8765"),
  VITE_USE_MOCK: z
    .enum(["true", "false"])
    .default("false")
    .transform((v) => v === "true"),
});

export const env = Env.parse(import.meta.env);
