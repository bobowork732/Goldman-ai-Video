import type { PolicyResponse } from "@goldman-ai-video/shared";

export class PolicyRejectionError extends Error {
  constructor(public readonly policy: PolicyResponse) {
    super(policy.user_safe_message);
    this.name = "PolicyRejectionError";
  }
}
