import assert from "node:assert/strict";
import { dirname, resolve } from "node:path";
import { test } from "node:test";
import { fileURLToPath } from "node:url";
import { createServer } from "vite";


test("development server does not grant arbitrary websites cross-origin access", async () => {
  const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
  const server = await createServer({ configFile: false, root, server: { host: "127.0.0.1", port: 0 } });
  try {
    await server.listen();
    const { port } = server.httpServer.address();
    const response = await fetch(`http://127.0.0.1:${port}/`, { headers: { Origin: "https://evil.test" } });
    assert.equal(response.status, 200);
    assert.equal(response.headers.get("access-control-allow-origin"), null);
  } finally {
    await server.close();
  }
});
