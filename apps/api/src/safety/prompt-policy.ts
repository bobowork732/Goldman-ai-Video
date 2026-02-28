import { policyResponseSchema, type PolicyResponse } from "@goldman-ai-video/shared";

const policyKeywordMap: Record<string, { category: "violence" | "sexual" | "hate" | "illegal"; code: string; message: string; actionable: string; decision: "flag" | "block" }> = {
  "kill": { category: "violence", code: "violence_explicit", message: "Prompt appears to request explicit violence.", actionable: "Remove violent intent and graphic harm terms.", decision: "block" },
  "bloodbath": { category: "violence", code: "violence_graphic", message: "Prompt appears to request graphic violence.", actionable: "Use non-graphic action descriptions.", decision: "block" },
  "nude": { category: "sexual", code: "sexual_explicit", message: "Prompt appears sexually explicit.", actionable: "Use non-explicit descriptions.", decision: "block" },
  "slur": { category: "hate", code: "hate_abusive", message: "Prompt appears to contain hateful/abusive content.", actionable: "Remove hateful language and targeting.", decision: "block" },
  "meth recipe": { category: "illegal", code: "illegal_instruction", message: "Prompt appears to request illegal instruction.", actionable: "Remove instructions for illegal activity.", decision: "block" },
  "weapon": { category: "violence", code: "violence_context", message: "Prompt includes weapon-related context.", actionable: "If benign, add clear non-violent context.", decision: "flag" }
};

export function classifyPromptPolicy(prompt: string): PolicyResponse {
  const normalized = prompt.toLowerCase();
  const reasons = Object.entries(policyKeywordMap)
    .filter(([needle]) => normalized.includes(needle))
    .map(([, rule]) => ({
      category: rule.category,
      code: rule.code,
      message: rule.message,
      actionable: rule.actionable,
      decision: rule.decision
    }));

  if (reasons.length === 0) {
    return policyResponseSchema.parse({
      decision: "allow",
      reasons: [],
      user_safe_message: "Request passed prompt safety checks.",
      review_required: false
    });
  }

  const block = reasons.some((r) => r.decision === "block");

  return policyResponseSchema.parse({
    decision: block ? "block" : "flag",
    reasons: reasons.map(({ category, code, message, actionable }) => ({ category, code, message, actionable })),
    user_safe_message: block
      ? "Your prompt could not be processed due to safety policy restrictions."
      : "Your prompt requires additional review before generation.",
    review_required: !block
  });
}
