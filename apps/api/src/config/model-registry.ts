import { readFileSync } from "node:fs";
import path from "node:path";

import { load } from "js-yaml";

import { modelRegistrySchema, type ModelCapability } from "@goldman-ai-video/shared";

const MODEL_CONFIG_PATH = path.resolve(process.cwd(), "services/generation-worker/config/models.yaml");

let cachedModels: ModelCapability[] | undefined;

export function getModelRegistry(): ModelCapability[] {
  if (cachedModels) {
    return cachedModels;
  }

  const raw = readFileSync(MODEL_CONFIG_PATH, "utf-8");
  const parsed = load(raw);
  const registry = modelRegistrySchema.parse(parsed);
  cachedModels = registry.models;
  return cachedModels;
}

export function getModelCapability(modelId: string): ModelCapability | undefined {
  return getModelRegistry().find((entry) => entry.id === modelId);
}
