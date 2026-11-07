import { posix, resolve, sep } from "node:path";

export type Resolved = { kind: "bad" } | { kind: "path"; pathname: string };

/**
 * Turns a raw request target into a normalised, decoded URL path that stays
 * inside the site. Malformed percent-encoding, NUL bytes, and any path that
 * leaves the root after decoding are "bad" (the server answers 400).
 */
export function resolveRequest(rawUrl: string, root: string): Resolved {
  let pathname: string;

  try {
    pathname = decodeURIComponent(new URL(rawUrl, "http://localhost").pathname);
  } catch {
    return { kind: "bad" };
  }

  if (pathname.includes("\0") || pathname.includes("\\")) return { kind: "bad" };

  const clean = posix.normalize(pathname);
  const absolute = resolve(root, `.${clean}`);

  if (absolute !== root && !absolute.startsWith(root + sep)) return { kind: "bad" };

  return { kind: "path", pathname: clean };
}
