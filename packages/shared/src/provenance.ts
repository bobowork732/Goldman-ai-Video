import { z } from "zod";

export const assetProvenanceSchema = z.object({
  model_id: z.string(),
  model_version: z.string(),
  generated_at: z.string(),
  job_id: z.string(),
  job_hash: z.string(),
  lineage: z.object({
    job_type: z.string(),
    parent_asset_id: z.string().optional()
  })
});

export type AssetProvenance = z.infer<typeof assetProvenanceSchema>;
