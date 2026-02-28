import { CLIENT_CONSTRAINTS, MODEL_OPTIONS } from './config.js';

function findModel(modelId) {
  return MODEL_OPTIONS.find((m) => m.id === modelId);
}

export function validateTextJob(form) {
  const errors = [];
  if (!form.prompt || form.prompt.trim().length < CLIENT_CONSTRAINTS.promptMinLength) {
    errors.push('Prompt is required.');
  }
  if (form.prompt && form.prompt.length > CLIENT_CONSTRAINTS.promptMaxLength) {
    errors.push(`Prompt must be <= ${CLIENT_CONSTRAINTS.promptMaxLength} characters.`);
  }

  const model = findModel(form.model);
  const maxDuration = model?.maxDuration ?? CLIENT_CONSTRAINTS.durationMaxDefault;
  const duration = Number(form.duration_seconds);
  if (Number.isNaN(duration) || duration < CLIENT_CONSTRAINTS.durationMin || duration > maxDuration) {
    errors.push(`Duration must be between ${CLIENT_CONSTRAINTS.durationMin} and ${maxDuration} seconds.`);
  }

  return errors;
}

export function validateImageJob(form) {
  const errors = validateTextJob({
    prompt: form.motion_prompt,
    model: form.model,
    duration_seconds: form.duration_seconds
  });

  if (!form.imageFile) {
    errors.push('Image file is required.');
  } else {
    if (!CLIENT_CONSTRAINTS.allowedImageTypes.includes(form.imageFile.type)) {
      errors.push('Image type must be PNG, JPEG, or WEBP.');
    }
    if (form.imageFile.size > CLIENT_CONSTRAINTS.maxImageSizeBytes) {
      errors.push('Image size must be <= 10MB.');
    }
  }

  return errors;
}
