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
    build: {
      rollupOptions: {
        output: {
          manualChunks(id) {
            if (!id.includes("node_modules")) return undefined;

            if (
              id.includes("node_modules/react/") ||
              id.includes("node_modules/react-dom/") ||
              id.includes("node_modules/scheduler/")
            ) {
              return "vendor-react";
            }
            if (id.includes("recharts") || id.includes("d3-")) {
              return "vendor-charts";
            }
            if (
              id.includes("react-markdown") ||
              id.includes("remark-") ||
              id.includes("rehype-") ||
              id.includes("highlight.js") ||
              id.includes("hast-util") ||
              id.includes("mdast-util") ||
              id.includes("micromark") ||
              id.includes("unified") ||
              id.includes("unist-")
            ) {
              return "vendor-markdown";
            }
            if (id.includes("node_modules/lucide-react/")) {
              return "vendor-icons";
            }
            if (id.includes("node_modules/framer-motion/")) {
              return "vendor-animation";
            }
            if (id.includes("axios") || id.includes("react-router-dom") || id.includes("@remix-run")) {
              return "vendor-app";
            }

            return undefined;
          },
        },
      },
    },
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
