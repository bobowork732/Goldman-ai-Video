export interface GenerationModelAdapter {
  readonly modelId: string;
  load(): Promise<void>;
  generate_from_text(prompt: string, params: Record<string, unknown>): Promise<Buffer>;
  generate_from_image(image: Buffer, prompt: string, params: Record<string, unknown>): Promise<Buffer>;
}
