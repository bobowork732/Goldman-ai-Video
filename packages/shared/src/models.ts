import { z } from "zod";

export const modelCapabilitySchema = z.object({
  id: z.string().min(1),
  adapter: z.string().min(1),
  supports_t2v: z.boolean(),
  supports_i2v: z.boolean(),
  max_duration_s: z.number().positive()
});

export const modelRegistrySchema = z.object({
  models: z.array(modelCapabilitySchema).min(1)
});

export type ModelCapability = z.infer<typeof modelCapabilitySchema>;
export type ModelRegistry = z.infer<typeof modelRegistrySchema>;
