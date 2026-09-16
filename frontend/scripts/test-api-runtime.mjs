import assert from "node:assert/strict";
import test from "node:test";

import { resolveApiBaseUrl } from "../src/services/apiRuntime.js";

test("HTTPS usa a origem aberta mesmo quando ficou um IP antigo no ambiente", () => {
  assert.equal(
    resolveApiBaseUrl("https://192.168.0.101:5173", {
      protocol: "https:",
      hostname: "localhost",
      origin: "https://localhost:5173",
    }),
    "https://localhost:5173",
  );
});

test("HTTPS no telemovel usa o mesmo IP para aplicação e API", () => {
  assert.equal(
    resolveApiBaseUrl("", {
      protocol: "https:",
      hostname: "192.168.0.101",
      origin: "https://192.168.0.101:5173",
    }),
    "https://192.168.0.101:5173",
  );
});

test("desenvolvimento HTTP continua a usar o Django na porta 8000", () => {
  assert.equal(
    resolveApiBaseUrl("", {
      protocol: "http:",
      hostname: "localhost",
      origin: "http://localhost:5173",
    }),
    "http://localhost:8000",
  );
});
