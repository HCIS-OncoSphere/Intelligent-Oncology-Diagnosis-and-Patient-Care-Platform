import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
// API_URL lets you point the dev proxy at a backend on another port, e.g. API_URL=http://localhost:8001
export default defineConfig({ plugins: [react()], server: { port: 5173, proxy: { "/api": process.env.API_URL || "http://127.0.0.1:8000", "/media": process.env.API_URL || "http://127.0.0.1:8000" } } });
