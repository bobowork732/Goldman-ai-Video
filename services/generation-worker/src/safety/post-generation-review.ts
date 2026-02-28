export interface ModerationFinding {
  category: "violence" | "sexual" | "hate" | "illegal";
  confidence: number;
  reason: string;
}

export interface PostGenerationReviewResult {
  decision: "allow" | "flag" | "block";
  sampled_frames: number[];
  findings: ModerationFinding[];
}

function sampleFramesForModeration(totalFrames: number): number[] {
  const indexes = new Set<number>([0, Math.max(0, Math.floor(totalFrames * 0.25)), Math.max(0, Math.floor(totalFrames * 0.5)), Math.max(0, Math.floor(totalFrames * 0.75)), Math.max(0, totalFrames - 1)]);
  return [...indexes].sort((a, b) => a - b);
}

export async function runPostGenerationReview(videoPayload: Buffer, estimatedFrames: number): Promise<PostGenerationReviewResult> {
  const sampledFrames = sampleFramesForModeration(Math.max(1, estimatedFrames));
  const text = videoPayload.toString("utf8").toLowerCase();
  const findings: ModerationFinding[] = [];

  if (text.includes("kill") || text.includes("gore")) {
    findings.push({ category: "violence", confidence: 0.91, reason: "Generated output metadata suggests graphic violence." });
  }

  if (text.includes("nude") || text.includes("porn")) {
    findings.push({ category: "sexual", confidence: 0.95, reason: "Generated output metadata suggests sexual explicitness." });
  }

  if (text.includes("slur")) {
    findings.push({ category: "hate", confidence: 0.9, reason: "Generated output metadata suggests hateful language." });
  }

  if (text.includes("meth recipe") || text.includes("how to make bomb")) {
    findings.push({ category: "illegal", confidence: 0.97, reason: "Generated output metadata suggests illegal instructions." });
  }

  if (findings.length === 0) {
    return { decision: "allow", sampled_frames: sampledFrames, findings: [] };
  }

  const block = findings.some((f) => f.confidence >= 0.9);
  return {
    decision: block ? "block" : "flag",
    sampled_frames: sampledFrames,
    findings
  };
}
