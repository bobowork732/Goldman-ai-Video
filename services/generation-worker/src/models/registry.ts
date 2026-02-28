import { readFileSync } from "node:fs";
import path from "node:path";

import { load } from "js-yaml";

import { modelRegistrySchema, type ModelCapability } from "@goldman-ai-video/shared";

import type { GenerationModelAdapter } from "./base_adapter.js";
import { ZeroScopeV2XLAdapter } from "./zeroscope_v2_xl_adapter.js";

type AdapterFactory = () => GenerationModelAdapter;

const adapterFactories: Record<string, AdapterFactory> = {
  ZeroScopeV2XLAdapter: () => new ZeroScopeV2XLAdapter()
};

const configPath = path.resolve(process.cwd(), "services/generation-worker/config/models.yaml");

export interface RegisteredModel {
  capability: ModelCapability;
  adapter: GenerationModelAdapter;
}

export function loadRegisteredModels(): Map<string, RegisteredModel> {
  const raw = readFileSync(configPath, "utf-8");
  const parsed = load(raw);
  const registry = modelRegistrySchema.parse(parsed);

  return new Map(
    registry.models.map((capability) => {
      const factory = adapterFactories[capability.adapter];
      if (!factory) {
        throw new Error(`No adapter factory configured for ${capability.adapter}`);
      }

      return [capability.id, { capability, adapter: factory() }];
    })
  );
}
