const NEGATIVE_PROMPT_PRESETS: Record<string, string> = {
  standard: "graphic violence, nudity, hate symbols, illegal activity instructions",
  strict: "graphic violence, gore, nudity, sexual content, hate symbols, extremist imagery, illegal activity instructions"
};

export function getNegativePromptPreset(level: "standard" | "strict" = "standard"): string {
  return NEGATIVE_PROMPT_PRESETS[level];
}

export function clampGenerationParams(params: {
  duration_seconds: number;
  max_duration_s: number;
  guidance_scale?: number;
  motion_intensity?: number;
}): { duration_seconds: number; guidance_scale: number; motion_intensity: number } {
  const guidance = params.guidance_scale ?? 7;
  const motion = params.motion_intensity ?? 0.5;

  return {
    duration_seconds: Math.max(1, Math.min(params.duration_seconds, params.max_duration_s)),
    guidance_scale: Math.max(1, Math.min(guidance, 20)),
    motion_intensity: Math.max(0, Math.min(motion, 1))
  };
}
