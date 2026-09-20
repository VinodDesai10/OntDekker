import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: ["./vitest.setup.ts"],
    include: ["src/__tests__/**/*.test.{ts,tsx}"],
    environmentOptions: {
      jsdom: {
        // A base URL is required for jsdom to enable localStorage and cookies
        url: "http://localhost",
      },
    },
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
});
