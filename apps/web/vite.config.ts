/// <reference types="vitest/config" />
import { fileURLToPath } from "node:url";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { defineConfig } from "vite";

const fixtures = fileURLToPath(new URL("../../data/fixtures", import.meta.url));

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: { alias: { "@fixtures": fixtures } },
  server: {
    fs: { allow: [".", fixtures] },
    proxy: { "/api": process.env.VITE_API_PROXY ?? "http://localhost:8000" },
  },
  test: { environment: "jsdom", setupFiles: ["src/test/setup.ts"], globals: true },
});
