import { policyResponseSchema, type PolicyResponse } from "@goldman-ai-video/shared";

export async function screenImageInput(imageUrl: string): Promise<PolicyResponse> {
  const lowered = imageUrl.toLowerCase();

  if (lowered.includes("nsfw") || lowered.includes("violence") || lowered.includes("illegal")) {
    return policyResponseSchema.parse({
      decision: "block",
      reasons: [
        {
          category: lowered.includes("nsfw") ? "sexual" : lowered.includes("violence") ? "violence" : "illegal",
          code: "image_input_blocked",
          message: "Image screening detected policy-sensitive content.",
          actionable: "Upload a policy-compliant image input."
        }
      ],
      user_safe_message: "The uploaded image cannot be used for generation due to safety policy.",
      review_required: false
    });
  }

  return policyResponseSchema.parse({
    decision: "allow",
    reasons: [],
    user_safe_message: "Image screening passed.",
    review_required: false
  });
}
