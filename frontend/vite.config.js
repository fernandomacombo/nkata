import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

const frontendDir = path.dirname(fileURLToPath(import.meta.url));
const repoDir = path.resolve(frontendDir, "..");
const certDir = path.join(repoDir, ".dev-certs");
const certPath = path.join(certDir, "nkata-dev-cert.pem");
const keyPath = path.join(certDir, "nkata-dev-key.pem");

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, frontendDir, "");
  const httpsMode = mode === "https";
  const apiTarget = env.NKATA_DEV_API_TARGET || "http://127.0.0.1:8000";

  if (httpsMode && (!fs.existsSync(certPath) || !fs.existsSync(keyPath))) {
    throw new Error(
      "Certificado HTTPS do NKATA não encontrado. Execute primeiro: powershell -ExecutionPolicy Bypass -File ..\\scripts\\setup-dev-https.ps1",
    );
  }

  const proxiedResource = () => ({
    target: apiTarget,
    // Preserva Host/Origin públicos (ex.: 192.168.0.102:5173). Assim o
    // Django consegue construir URLs absolutas que continuam no mesmo origin
    // HTTPS visto pelo iPhone, em vez de expor 127.0.0.1:8000 ao browser.
    changeOrigin: false,
    secure: false,
    configure(proxy) {
      proxy.on("proxyReq", (proxyReq) => {
        proxyReq.setHeader("X-Forwarded-Proto", httpsMode ? "https" : "http");
      });
    },
  });

  return {
    plugins: [react()],
    server: {
      host: "0.0.0.0",
      port: 5173,
      strictPort: true,
      https: httpsMode
        ? {
            cert: fs.readFileSync(certPath),
            key: fs.readFileSync(keyPath),
          }
        : undefined,
      proxy: {
        "/api": proxiedResource(),
        "/media": proxiedResource(),
      },
    },
    preview: {
      host: "0.0.0.0",
      port: 4173,
      strictPort: true,
      https: httpsMode
        ? {
            cert: fs.readFileSync(certPath),
            key: fs.readFileSync(keyPath),
          }
        : undefined,
      proxy: {
        "/api": proxiedResource(),
        "/media": proxiedResource(),
      },
    },
  };
});
