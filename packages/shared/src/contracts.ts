import { z } from "zod";

import { safetyFlagsSchema } from "./dtos.js";

export const workerJobTypeSchema = z.enum(["text-to-video", "image-to-video"]);

export const workerJobContractSchema = z.object({
  job_id: z.string(),
  job_type: workerJobTypeSchema,
  model: z.string(),
  params: z.record(z.unknown()),
  safety_flags: safetyFlagsSchema,
  created_at: z.string()
});

export type WorkerJobContract = z.infer<typeof workerJobContractSchema>;
