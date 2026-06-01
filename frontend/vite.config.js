import react from "@vitejs/plugin-react";
import fs from "node:fs";
import process from "node:process";
import { defineConfig, loadEnv } from "vite";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const httpsKey = env.VITE_HTTPS_KEY;
  const httpsCert = env.VITE_HTTPS_CERT;
  const httpsPfx = env.VITE_HTTPS_PFX;
  const httpsPassphrase = env.VITE_HTTPS_PASSPHRASE;
  const https = httpsPfx
    ? {
        pfx: fs.readFileSync(httpsPfx),
        passphrase: httpsPassphrase,
      }
    : httpsKey && httpsCert
    ? {
        key: fs.readFileSync(httpsKey),
        cert: fs.readFileSync(httpsCert),
      }
    : undefined;

  return {
    plugins: [react()],
    server: {
      host: "0.0.0.0",
      port: 5174,
      https,
      proxy: {
        "/api": {
          target: "http://127.0.0.1:8000",
          changeOrigin: true,
        },
      },
    },
  };
});
