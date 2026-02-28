import { createHash } from "node:crypto";

import type { WorkerJobContract } from "@goldman-ai-video/shared";

export interface GenerationProvenance {
  model_id: string;
  model_version: string;
  generated_at: string;
  job_id: string;
  job_hash: string;
  lineage: {
    job_type: string;
    parent_asset_id?: string;
  };
}

export function createGenerationProvenance(job: WorkerJobContract): GenerationProvenance {
  const generatedAt = new Date().toISOString();
  const modelVersion = String(job.params.model_version ?? process.env.DEFAULT_MODEL_VERSION ?? "v1");
  const rawHash = JSON.stringify({
    job_id: job.job_id,
    model: job.model,
    model_version: modelVersion,
    params: job.params,
    generated_at: generatedAt
  });

  return {
    model_id: job.model,
    model_version: modelVersion,
    generated_at: generatedAt,
    job_id: job.job_id,
    job_hash: createHash("sha256").update(rawHash).digest("hex"),
    lineage: {
      job_type: job.job_type,
      parent_asset_id: typeof job.params.parent_asset_id === "string" ? job.params.parent_asset_id : undefined
    }
  };
}
