import { mkdtemp, readFile, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";

import Redis from "ioredis";

import { workerJobContractSchema, type WorkerJobContract } from "@goldman-ai-video/shared";

import { loadRegisteredModels } from "./models/registry.js";
import { applyWatermarkOverlay, resolveWatermarkStyle, type WatermarkStyle } from "./postprocessing/watermark.js";
import { createGenerationProvenance } from "./provenance/metadata.js";
import { runPostGenerationReview } from "./safety/post-generation-review.js";
import { createOutputStorage } from "./storage/output-storage.js";

const REDIS_URL = process.env.REDIS_URL ?? "redis://localhost:6379";
const QUEUE_KEY = process.env.JOB_QUEUE_KEY ?? "video-generation:jobs";

const models = loadRegisteredModels();
const storage = createOutputStorage();

export interface GenerationWorkerConsumer {
  consume(handler: (job: WorkerJobContract) => Promise<void>): Promise<void>;
}

export class RedisGenerationWorkerConsumer implements GenerationWorkerConsumer {
  private readonly redis = new Redis(REDIS_URL);

  async consume(handler: (job: WorkerJobContract) => Promise<void>): Promise<void> {
    for (;;) {
      const entry = await this.redis.brpop(QUEUE_KEY, 0);
      const rawPayload = entry?.[1];

      if (!rawPayload) {
        continue;
      }

      const parsed = workerJobContractSchema.safeParse(JSON.parse(rawPayload));
      if (!parsed.success) {
        console.error("Dropping invalid job payload", parsed.error.issues);
        continue;
      }

      await handler(parsed.data);
    }
  }
}

function clampWorkerParams(params: Record<string, unknown>, maxDuration: number): Record<string, unknown> {
  const duration = Number(params.duration_seconds ?? 4);
  const guidance = Number(params.guidance_scale ?? 7);
  const motion = Number(params.motion_intensity ?? 0.5);

  return {
    ...params,
    duration_seconds: Math.max(1, Math.min(duration, maxDuration)),
    guidance_scale: Math.max(1, Math.min(guidance, 20)),
    motion_intensity: Math.max(0, Math.min(motion, 1))
  };
}

async function tryApplyWatermark(payload: Buffer, style: WatermarkStyle): Promise<Buffer> {
  const dir = await mkdtemp(path.join(tmpdir(), "gai-video-"));
  const input = path.join(dir, "input.mp4");
  const output = path.join(dir, "output.mp4");
  await writeFile(input, payload);

  try {
    await applyWatermarkOverlay(input, output, style);
    return await readFile(output);
  } catch (error) {
    console.warn("Watermark overlay skipped (ffmpeg unavailable or invalid media)", { error });
    return payload;
  } finally {
    await rm(dir, { recursive: true, force: true });
  }
}

async function processJob(job: WorkerJobContract): Promise<void> {
  const registered = models.get(job.model);
  if (!registered) {
    throw new Error(`No registered adapter for model ${job.model}`);
  }

  const { adapter, capability } = registered;
  await adapter.load();

  const objectKey = `${job.job_id}.mp4`;
  const clampedParams = clampWorkerParams(job.params, capability.max_duration_s);
  const estimatedFrames = Math.max(1, Math.round(Number(clampedParams.duration_seconds) * Number(clampedParams.fps ?? 24)));

  let payload: Buffer;

  if (job.job_type === "text-to-video") {
    if (!capability.supports_t2v) {
      throw new Error(`Model ${job.model} does not support text-to-video`);
    }

    const prompt = String(clampedParams.prompt ?? "");
    payload = await adapter.generate_from_text(prompt, clampedParams);
  } else {
    if (!capability.supports_i2v) {
      throw new Error(`Model ${job.model} does not support image-to-video`);
    }

    const image = Buffer.from(String(clampedParams.image_url ?? ""), "utf8");
    const prompt = String(clampedParams.motion_prompt ?? "");
    payload = await adapter.generate_from_image(image, prompt, clampedParams);
  }

  const watermarkStyle = resolveWatermarkStyle((clampedParams.watermark as Partial<WatermarkStyle> | undefined) ?? undefined);
  const watermarkedPayload = await tryApplyWatermark(payload, watermarkStyle);

  const moderation = await runPostGenerationReview(watermarkedPayload, estimatedFrames);
  if (moderation.decision !== "allow") {
    console.warn("Post-generation moderation held asset publication", {
      job_id: job.job_id,
      decision: moderation.decision,
      findings: moderation.findings,
      sampled_frames: moderation.sampled_frames
    });
    return;
  }

  const provenance = createGenerationProvenance(job);
  const provenanceKey = `${job.job_id}.provenance.json`;

  const saved = await storage.putObject(objectKey, watermarkedPayload, "video/mp4");
  await storage.putJson(provenanceKey, provenance);

  console.log("Generated asset published", {
    job_id: job.job_id,
    object_key: saved.objectKey,
    provenance_key: provenanceKey,
    metadata_hash: provenance.job_hash,
    url: saved.publicUrl,
    sampled_frames: moderation.sampled_frames
  });
}

if (process.env.NODE_ENV !== "test") {
  const consumer = new RedisGenerationWorkerConsumer();

  consumer.consume(async (job) => {
    try {
      await processJob(job);
    } catch (error) {
      console.error("Failed to process generation job", { error, job_id: job.job_id });
    }
  });
}
