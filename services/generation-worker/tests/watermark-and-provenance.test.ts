import assert from "node:assert/strict";
import test from "node:test";

import type { WorkerJobContract } from "@goldman-ai-video/shared";

import { createGenerationProvenance } from "../src/provenance/metadata.ts";
import { buildWatermarkFilter, resolveWatermarkStyle } from "../src/postprocessing/watermark.ts";

test("watermark filter includes required drawtext with tenant/brand text", () => {
  const style = resolveWatermarkStyle({ text: "Tenant-A Confidential", opacity: 0.25, x_margin: 16, y_margin: 16 });
  const filter = buildWatermarkFilter(style);

  assert.match(filter, /drawtext=/);
  assert.match(filter, /Tenant-A Confidential/);
  assert.match(filter, /fontcolor=white@/);
});

test("provenance metadata persists core lineage for text-to-video jobs", () => {
  const job: WorkerJobContract = {
    job_id: "job-t2v-1",
    job_type: "text-to-video",
    model: "zeroscope-v2-xl",
    params: { prompt: "a sunrise over mountains", model_version: "v2.1" },
    safety_flags: {},
    created_at: new Date().toISOString()
  };

  const provenance = createGenerationProvenance(job);

  assert.equal(provenance.job_id, job.job_id);
  assert.equal(provenance.model_id, job.model);
  assert.equal(provenance.model_version, "v2.1");
  assert.equal(provenance.lineage.job_type, "text-to-video");
  assert.ok(provenance.job_hash.length >= 64);
});

test("provenance metadata persists lineage for image-to-video jobs", () => {
  const job: WorkerJobContract = {
    job_id: "job-i2v-1",
    job_type: "image-to-video",
    model: "zeroscope-v2-xl",
    params: {
      image_url: "https://example.com/image.png",
      motion_prompt: "gentle camera pan",
      parent_asset_id: "asset-seed-1",
      model_version: "v2.1"
    },
    safety_flags: {},
    created_at: new Date().toISOString()
  };

  const provenance = createGenerationProvenance(job);

  assert.equal(provenance.lineage.job_type, "image-to-video");
  assert.equal(provenance.lineage.parent_asset_id, "asset-seed-1");
  assert.ok(provenance.job_hash.length >= 64);
});
