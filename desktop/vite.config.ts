import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import tsconfigPaths from "vite-tsconfig-paths";

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss(), tsconfigPaths()],
  resolve: {
    extensions: [".mjs", ".js", ".mts", ".ts", ".jsx", ".tsx", ".json"],
  },
  // Tauri expects a fixed port in dev mode
  server: {
    port: 5173,
    strictPort: true,
  },
  // For production, output to dist/
  build: {
    outDir: "dist",
    emptyOutDir: true,
  },
  // Prevent Vite from clearing the terminal
  clearScreen: false,
});
