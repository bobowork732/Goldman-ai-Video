import { z } from "zod";

export const safetyFlagsSchema = z.record(z.boolean()).default({});

const tenantWatermarkSchema = z.object({
  text: z.string().min(1).optional(),
  opacity: z.number().min(0).max(1).optional(),
  x_margin: z.number().int().nonnegative().optional(),
  y_margin: z.number().int().nonnegative().optional(),
  font_size: z.number().int().positive().optional()
}).optional();

export const createTextToVideoJobRequestSchema = z.object({
  prompt: z.string().min(1),
  model: z.string().min(1),
  duration_seconds: z.number().positive(),
  guidance_scale: z.number().positive().optional(),
  motion_intensity: z.number().min(0).max(1).optional(),
  fps: z.number().int().positive().optional(),
  resolution: z.string().optional(),
  enterprise_mode: z.boolean().optional(),
  tenant_watermark: tenantWatermarkSchema,
  safety_flags: safetyFlagsSchema.optional()
});

export const createImageToVideoJobRequestSchema = z.object({
  image_url: z.string().url(),
  motion_prompt: z.string().min(1),
  model: z.string().min(1),
  duration_seconds: z.number().positive(),
  guidance_scale: z.number().positive().optional(),
  motion_intensity: z.number().min(0).max(1).optional(),
  fps: z.number().int().positive().optional(),
  resolution: z.string().optional(),
  enterprise_mode: z.boolean().optional(),
  tenant_watermark: tenantWatermarkSchema,
  safety_flags: safetyFlagsSchema.optional()
});

export const jobStatusSchema = z.enum(["queued", "processing", "completed", "failed"]);

export const jobStatusResponseSchema = z.object({
  id: z.string(),
  status: jobStatusSchema,
  job_type: z.enum(["text-to-video", "image-to-video"]),
  model: z.string(),
  created_at: z.string(),
  updated_at: z.string(),
  asset_id: z.string().optional(),
  error: z.string().optional()
});

export type CreateTextToVideoJobRequest = z.infer<typeof createTextToVideoJobRequestSchema>;
export type CreateImageToVideoJobRequest = z.infer<typeof createImageToVideoJobRequestSchema>;
export type JobStatusResponse = z.infer<typeof jobStatusResponseSchema>;
export type SafetyFlags = z.infer<typeof safetyFlagsSchema>;
