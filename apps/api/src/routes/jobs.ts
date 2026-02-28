import { Router } from "express";
import { v4 as uuidv4 } from "uuid";

import {
  createImageToVideoJobRequestSchema,
  createTextToVideoJobRequestSchema,
  jobStatusResponseSchema,
  type JobStatusResponse,
  type ModelCapability,
  workerJobContractSchema
} from "@goldman-ai-video/shared";

import { getModelCapability } from "../config/model-registry.js";
import { resolveTenantWatermarkConfig, type TenantWatermarkConfig } from "../enterprise/watermark-policy.js";
import type { JobQueue } from "../queue/job-queue.js";
import { clampGenerationParams, getNegativePromptPreset } from "../safety/generation-controls.js";
import { screenImageInput } from "../safety/image-screening.js";
import { PolicyRejectionError } from "../safety/policy-error.js";
import { classifyPromptPolicy } from "../safety/prompt-policy.js";
import { getJob, saveJob } from "../store/job-store.js";

function validateModelCapability(model: string, mode: "text-to-video" | "image-to-video", durationSeconds: number): ModelCapability {
  const capability = getModelCapability(model);

  if (!capability) {
    throw new Error(`Unsupported model: ${model}`);
  }

  if (mode === "text-to-video" && !capability.supports_t2v) {
    throw new Error(`Model ${model} does not support text-to-video`);
  }

  if (mode === "image-to-video" && !capability.supports_i2v) {
    throw new Error(`Model ${model} does not support image-to-video`);
  }

  if (durationSeconds > capability.max_duration_s) {
    throw new Error(`Model ${model} supports max duration of ${capability.max_duration_s}s`);
  }

  return capability;
}

function getWatermarkConfig(options: { enterprise_mode?: boolean; tenant_watermark?: TenantWatermarkConfig }) {
  return resolveTenantWatermarkConfig(options.tenant_watermark, Boolean(options.enterprise_mode));
}

export function createJobsRouter(jobQueue: JobQueue): Router {
  const router = Router();

  router.post("/text-to-video", async (req, res, next) => {
    try {
      const payload = createTextToVideoJobRequestSchema.parse(req.body);
      const capability = validateModelCapability(payload.model, "text-to-video", payload.duration_seconds);

      const promptPolicy = classifyPromptPolicy(payload.prompt);
      if (promptPolicy.decision === "block") {
        throw new PolicyRejectionError(promptPolicy);
      }

      const controls = clampGenerationParams({
        duration_seconds: payload.duration_seconds,
        guidance_scale: payload.guidance_scale,
        motion_intensity: payload.motion_intensity,
        max_duration_s: capability.max_duration_s
      });

      const watermark = getWatermarkConfig({ enterprise_mode: payload.enterprise_mode, tenant_watermark: payload.tenant_watermark });
      const now = new Date().toISOString();
      const id = uuidv4();

      const job: JobStatusResponse = {
        id,
        status: "queued",
        job_type: "text-to-video",
        model: payload.model,
        created_at: now,
        updated_at: now
      };

      jobStatusResponseSchema.parse(job);
      saveJob(job);

      const workerJob = workerJobContractSchema.parse({
        job_id: id,
        job_type: "text-to-video",
        model: payload.model,
        params: {
          prompt: payload.prompt,
          duration_seconds: controls.duration_seconds,
          guidance_scale: controls.guidance_scale,
          motion_intensity: controls.motion_intensity,
          negative_prompt: getNegativePromptPreset(promptPolicy.review_required ? "strict" : "standard"),
          fps: payload.fps,
          resolution: payload.resolution,
          policy_review_required: promptPolicy.review_required,
          watermark
        },
        safety_flags: payload.safety_flags ?? {},
        created_at: now
      });

      await jobQueue.enqueue(workerJob);
      return res.status(202).json(job);
    } catch (error) {
      return next(error);
    }
  });

  router.post("/image-to-video", async (req, res, next) => {
    try {
      const payload = createImageToVideoJobRequestSchema.parse(req.body);
      const capability = validateModelCapability(payload.model, "image-to-video", payload.duration_seconds);

      const promptPolicy = classifyPromptPolicy(payload.motion_prompt);
      if (promptPolicy.decision === "block") {
        throw new PolicyRejectionError(promptPolicy);
      }

      const imagePolicy = await screenImageInput(payload.image_url);
      if (imagePolicy.decision === "block") {
        throw new PolicyRejectionError(imagePolicy);
      }

      const controls = clampGenerationParams({
        duration_seconds: payload.duration_seconds,
        guidance_scale: payload.guidance_scale,
        motion_intensity: payload.motion_intensity,
        max_duration_s: capability.max_duration_s
      });

      const watermark = getWatermarkConfig({ enterprise_mode: payload.enterprise_mode, tenant_watermark: payload.tenant_watermark });
      const now = new Date().toISOString();
      const id = uuidv4();

      const job: JobStatusResponse = {
        id,
        status: "queued",
        job_type: "image-to-video",
        model: payload.model,
        created_at: now,
        updated_at: now
      };

      jobStatusResponseSchema.parse(job);
      saveJob(job);

      const workerJob = workerJobContractSchema.parse({
        job_id: id,
        job_type: "image-to-video",
        model: payload.model,
        params: {
          image_url: payload.image_url,
          motion_prompt: payload.motion_prompt,
          duration_seconds: controls.duration_seconds,
          guidance_scale: controls.guidance_scale,
          motion_intensity: controls.motion_intensity,
          negative_prompt: getNegativePromptPreset(promptPolicy.review_required || imagePolicy.review_required ? "strict" : "standard"),
          fps: payload.fps,
          resolution: payload.resolution,
          policy_review_required: promptPolicy.review_required || imagePolicy.review_required,
          watermark
        },
        safety_flags: payload.safety_flags ?? {},
        created_at: now
      });

      await jobQueue.enqueue(workerJob);
      return res.status(202).json(job);
    } catch (error) {
      return next(error);
    }
  });

  router.get("/:id", (req, res) => {
    const job = getJob(req.params.id);

    if (!job) {
      return res.status(404).json({ message: "Job not found" });
    }

    return res.json(job);
  });

  return router;
}
