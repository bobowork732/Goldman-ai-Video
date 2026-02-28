export const API_BASE_URL = localStorage.getItem('apiBaseUrl') || 'http://localhost:3001';

export const MODEL_OPTIONS = [
  { id: 'zeroscope-v2-xl', label: 'ZeroScope v2 XL', maxDuration: 8 }
];

export const CLIENT_CONSTRAINTS = {
  promptMinLength: 1,
  promptMaxLength: 600,
  maxImageSizeBytes: 10 * 1024 * 1024,
  allowedImageTypes: ['image/png', 'image/jpeg', 'image/webp'],
  durationMin: 1,
  durationMaxDefault: 8
};
