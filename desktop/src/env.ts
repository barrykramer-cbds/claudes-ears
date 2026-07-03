import { z } from "zod";

const Env = z.object({
  // Sidecar base URL — Electron main injects the real one; empty = same-origin via the vite proxy.
  VITE_API_BASE_URL: z.union([z.url(), z.literal("")]).default(""),
  VITE_USE_MOCK: z
    .enum(["true", "false"])
    .default("false")
    .transform((v) => v === "true"),
});

export const env = Env.parse(import.meta.env);
