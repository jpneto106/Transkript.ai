import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Em produção o app é servido pela própria API (mesma origem), então base "./".
export default defineConfig({
  plugins: [react()],
  base: "./",
  server: {
    port: 5173,
  },
  build: {
    outDir: "dist",
  },
});
