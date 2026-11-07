import assert from "node:assert/strict";
import { resolve } from "node:path";
import { test } from "node:test";

import { resolveRequest } from "./static-path.ts";

const root = resolve("/srv/dist");

test("normal paths pass through", () => {
  assert.deepEqual(resolveRequest("/docs/introduction/?q=1", root), { kind: "path", pathname: "/docs/introduction/" });
});

test("malformed percent-encoding is rejected, not thrown", () => {
  assert.deepEqual(resolveRequest("/%E0%A4%A", root), { kind: "bad" });
});

test("traversal and backslashes are rejected after decoding", () => {
  for (const url of ["/%2e%2e/%2e%2e/etc/passwd", "/..%2f..%2fsecret", "/a/..%5c..%5csecret", "/x%00.html"]) {
    const got = resolveRequest(url, root);
    assert.ok(got.kind === "bad" || !got.pathname.includes(".."), url);
  }
});
