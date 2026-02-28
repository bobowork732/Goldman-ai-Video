import { randomUUID } from "node:crypto";

import type { GenerationModelAdapter } from "./base_adapter.js";

export class ZeroScopeV2XLAdapter implements GenerationModelAdapter {
  readonly modelId = "zeroscope-v2-xl";

  async load(): Promise<void> {
    // Placeholder: load tokenizer/weights/runtime into GPU memory.
  }

  async generate_from_text(prompt: string, params: Record<string, unknown>): Promise<Buffer> {
    const payload = {
      mode: "text-to-video",
      model: this.modelId,
      prompt,
      params,
      generation_id: randomUUID()
    };

    return Buffer.from(JSON.stringify(payload), "utf8");
  }

  async generate_from_image(_image: Buffer, _prompt: string, _params: Record<string, unknown>): Promise<Buffer> {
    throw new Error(`${this.modelId} adapter does not support image-to-video yet`);
  }
}
