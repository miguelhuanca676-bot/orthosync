import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { resolve } from "node:path";

// Dos páginas: index.html (pública, HTML puro para buen SEO) y app.html (la aplicación con inicio de sesión)
export default defineConfig({
  plugins: [react(), tailwindcss()],
  build: { rollupOptions: { input: Object.fromEntries(["index", "app", "privacidad", "terminos", "cookies", "creditos", "verificar"].map((n) => [n, resolve(__dirname, `${n}.html`)])) } },
  server: { proxy: { "/api": "http://localhost:8000" } },
});
