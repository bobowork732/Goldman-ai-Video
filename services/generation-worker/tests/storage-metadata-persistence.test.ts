import assert from "node:assert/strict";
import { mkdtemp, readFile, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import test from "node:test";

import { LocalOutputStorage } from "../src/storage/output-storage.ts";

test("metadata persistence for text-to-video provenance sidecar", async () => {
  const root = await mkdtemp(path.join(tmpdir(), "gai-storage-t2v-"));
  process.env.LOCAL_STORAGE_DIR = root;
  const storage = new LocalOutputStorage();

  await storage.putJson("job-t2v-1.provenance.json", { job_type: "text-to-video", job_hash: "abc123" });
  const saved = JSON.parse(await readFile(path.join(root, "job-t2v-1.provenance.json"), "utf8"));

  assert.equal(saved.job_type, "text-to-video");
  assert.equal(saved.job_hash, "abc123");
  await rm(root, { recursive: true, force: true });
});

test("metadata persistence for image-to-video provenance sidecar", async () => {
  const root = await mkdtemp(path.join(tmpdir(), "gai-storage-i2v-"));
  process.env.LOCAL_STORAGE_DIR = root;
  const storage = new LocalOutputStorage();

  await storage.putJson("job-i2v-1.provenance.json", { job_type: "image-to-video", parent_asset_id: "asset-seed-1" });
  const saved = JSON.parse(await readFile(path.join(root, "job-i2v-1.provenance.json"), "utf8"));

  assert.equal(saved.job_type, "image-to-video");
  assert.equal(saved.parent_asset_id, "asset-seed-1");
  await rm(root, { recursive: true, force: true });
});
