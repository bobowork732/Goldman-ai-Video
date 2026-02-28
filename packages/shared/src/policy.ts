import { z } from "zod";

export const policyCategorySchema = z.enum(["violence", "sexual", "hate", "illegal"]);

export const policyDecisionSchema = z.enum(["allow", "flag", "block"]);

export const policyReasonSchema = z.object({
  category: policyCategorySchema,
  code: z.string().min(1),
  message: z.string().min(1),
  actionable: z.string().min(1)
});

export const policyResponseSchema = z.object({
  decision: policyDecisionSchema,
  reasons: z.array(policyReasonSchema),
  user_safe_message: z.string().min(1),
  review_required: z.boolean().default(false)
});

export type PolicyCategory = z.infer<typeof policyCategorySchema>;
export type PolicyDecision = z.infer<typeof policyDecisionSchema>;
export type PolicyReason = z.infer<typeof policyReasonSchema>;
export type PolicyResponse = z.infer<typeof policyResponseSchema>;
