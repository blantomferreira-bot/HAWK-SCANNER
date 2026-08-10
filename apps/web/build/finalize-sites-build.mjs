import { createHash } from "node:crypto";
import { readFile, readdir, rename, writeFile } from "node:fs/promises";
import { extname, join, resolve } from "node:path";

const distDirectory = resolve(import.meta.dirname, "..", "dist");
const chunksDirectory = resolve(distDirectory, "client", "_next", "static", "chunks");
const textExtensions = new Set([".html", ".js", ".json", ".mjs"]);

async function textFiles(directory) {
  const entries = await readdir(directory, { withFileTypes: true });
  const nested = await Promise.all(entries.map(async (entry) => {
    const path = join(directory, entry.name);
    return entry.isDirectory() ? textFiles(path) : [path];
  }));
  return nested.flat().filter((path) => textExtensions.has(extname(path)));
}

const dashboardChunk = (await readdir(chunksDirectory)).find((name) => name.startsWith("dashboard-shell-") && name.endsWith(".js"));
if (!dashboardChunk) throw new Error("Dashboard client chunk was not generated.");

const dashboardPath = join(chunksDirectory, dashboardChunk);
const contentHash = createHash("sha256").update(await readFile(dashboardPath)).digest("hex").slice(0, 12);
const versionedChunk = dashboardChunk.replace(/\.js$/, `-${contentHash}.js`);

for (const path of await textFiles(distDirectory)) {
  const content = await readFile(path, "utf8");
  if (content.includes(dashboardChunk)) await writeFile(path, content.replaceAll(dashboardChunk, versionedChunk));
}

await rename(dashboardPath, join(chunksDirectory, versionedChunk));
await writeFile(resolve(distDirectory, "client", "_headers"), "/_next/static/*\n  Cache-Control: public, max-age=0, must-revalidate\n");
