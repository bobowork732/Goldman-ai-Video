import { API_BASE_URL } from './config.js';

async function request(path, options = {}) {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options
  });

  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const error = new Error(data?.message || 'Request failed');
    error.status = res.status;
    error.data = data;
    throw error;
  }
  return data;
}

export function submitTextToVideo(payload) {
  return request('/jobs/text-to-video', { method: 'POST', body: JSON.stringify(payload) });
}

export function submitImageToVideo(payload) {
  return request('/jobs/image-to-video', { method: 'POST', body: JSON.stringify(payload) });
}

export function getJob(jobId) {
  return request(`/jobs/${jobId}`);
}

export function getAsset(assetId) {
  return request(`/assets/${assetId}`);
}

export function getAssetProvenance(assetId) {
  return request(`/assets/${assetId}/provenance`);
}

export async function pollJob(jobId, onTick, intervalMs = 2000) {
  let active = true;
  while (active) {
    const job = await getJob(jobId);
    onTick(job);
    if (job.status === 'completed' || job.status === 'failed') break;
    await new Promise((r) => setTimeout(r, intervalMs));
  }
  return () => { active = false; };
}

export function downloadAsset(url) {
  const a = document.createElement('a');
  a.href = url;
  a.download = '';
  a.target = '_blank';
  a.rel = 'noopener';
  a.click();
}
