import {
  submitTextToVideo,
  submitImageToVideo,
  pollJob,
  getAsset,
  getAssetProvenance,
  downloadAsset
} from './api-client.js';
import { MODEL_OPTIONS, CLIENT_CONSTRAINTS } from './config.js';
import { renderJobList } from './components/job-list.js';
import { renderSafetyError } from './components/safety-feedback.js';
import { renderPreviewPage } from './pages/preview-page.js';
import { validateImageJob, validateTextJob } from './validators.js';

const state = {
  tab: 'text',
  jobs: [],
  selectedAsset: null,
  selectedProvenance: null,
  lastErrorHtml: ''
};

const app = document.getElementById('app');

function render() {
  app.innerHTML = `
    <div class="container">
      <header class="header">
        <div class="brand">
          <h1>Goldman AI Video Studio</h1>
          <p>Create compliant generated videos with traceable safety and provenance.</p>
        </div>
        <nav class="nav">
          <button data-tab="text" class="${state.tab === 'text' ? 'active' : ''}">Text to Video</button>
          <button data-tab="image" class="${state.tab === 'image' ? 'active' : ''}">Image to Video</button>
          <button data-tab="jobs" class="${state.tab === 'jobs' ? 'active' : ''}">Jobs</button>
          <button data-tab="preview" class="${state.tab === 'preview' ? 'active' : ''}">Preview</button>
        </nav>
      </header>

      <main class="grid">
        ${state.tab === 'text' ? renderTextForm() : ''}
        ${state.tab === 'image' ? renderImageForm() : ''}
        ${state.tab === 'jobs' ? `<div class="card"><h2>Job Status & Progress</h2>${renderJobList(state.jobs)}</div>` : ''}
        ${state.tab === 'preview' ? renderPreviewPage(state) : ''}
      </main>
      ${state.lastErrorHtml || ''}
      <div class="footer-note">Brand watermark and generated-content labels are always visible in previews.</div>
    </div>
  `;

  wireEvents();
}

function modelOptions() {
  return MODEL_OPTIONS.map((m) => `<option value="${m.id}">${m.label} (max ${m.maxDuration}s)</option>`).join('');
}

function renderTextForm() {
  return `
    <div class="card">
      <h2>Text to Video</h2>
      <form id="text-form">
        <label>Prompt</label>
        <textarea name="prompt" maxlength="${CLIENT_CONSTRAINTS.promptMaxLength}" required></textarea>
        <label>Duration (seconds)</label>
        <input name="duration_seconds" type="number" min="1" max="8" value="4" required />
        <label>Style / Model</label>
        <select name="model">${modelOptions()}</select>
        <label><input type="checkbox" name="enterprise_mode"/> Enterprise watermark mode</label>
        <label>Tenant Watermark Text (optional)</label>
        <input name="tenant_watermark_text" type="text" placeholder="Tenant Confidential" />
        <button class="primary" type="submit">Submit text-to-video job</button>
      </form>
    </div>
  `;
}

function renderImageForm() {
  return `
    <div class="card">
      <h2>Image to Video</h2>
      <form id="image-form">
        <label>Image Upload (PNG/JPEG/WEBP, ≤ 10MB)</label>
        <input name="image" type="file" accept="image/png,image/jpeg,image/webp" required />
        <label>Motion Prompt</label>
        <textarea name="motion_prompt" maxlength="${CLIENT_CONSTRAINTS.promptMaxLength}" required></textarea>
        <label>Duration (seconds)</label>
        <input name="duration_seconds" type="number" min="1" max="8" value="4" required />
        <label>Style / Model</label>
        <select name="model">${modelOptions()}</select>
        <label><input type="checkbox" name="enterprise_mode"/> Enterprise watermark mode</label>
        <label>Tenant Watermark Text (optional)</label>
        <input name="tenant_watermark_text" type="text" placeholder="Tenant Confidential" />
        <button class="primary" type="submit">Submit image-to-video job</button>
      </form>
    </div>
  `;
}

function wireEvents() {
  app.querySelectorAll('[data-tab]').forEach((el) => {
    el.addEventListener('click', () => {
      state.tab = el.dataset.tab;
      render();
    });
  });

  const textForm = document.getElementById('text-form');
  if (textForm) textForm.addEventListener('submit', onTextSubmit);

  const imageForm = document.getElementById('image-form');
  if (imageForm) imageForm.addEventListener('submit', onImageSubmit);

  app.querySelectorAll('[data-open-preview]').forEach((el) => {
    el.addEventListener('click', async () => {
      await openPreview(el.dataset.openPreview);
    });
  });

  const downloadBtn = app.querySelector('[data-download-asset]');
  if (downloadBtn) {
    downloadBtn.addEventListener('click', () => downloadAsset(downloadBtn.dataset.downloadAsset));
  }
}

async function onTextSubmit(e) {
  e.preventDefault();
  state.lastErrorHtml = '';

  const form = new FormData(e.currentTarget);
  const payload = {
    prompt: String(form.get('prompt') || ''),
    duration_seconds: Number(form.get('duration_seconds')),
    model: String(form.get('model')),
    enterprise_mode: Boolean(form.get('enterprise_mode')),
    tenant_watermark: form.get('tenant_watermark_text')
      ? { text: String(form.get('tenant_watermark_text')) }
      : undefined
  };

  const errors = validateTextJob(payload);
  if (errors.length) {
    state.lastErrorHtml = `<div class="error-box"><strong>Please fix:</strong><ul>${errors.map((v) => `<li>${v}</li>`).join('')}</ul></div>`;
    render();
    return;
  }

  try {
    const job = await submitTextToVideo(payload);
    state.jobs.unshift(job);
    state.tab = 'jobs';
    render();
    await trackJob(job.id);
  } catch (error) {
    state.lastErrorHtml = renderSafetyError(error);
    render();
  }
}

async function onImageSubmit(e) {
  e.preventDefault();
  state.lastErrorHtml = '';

  const form = new FormData(e.currentTarget);
  const imageFile = form.get('image');
  const payload = {
    image_url: imageFile?.name ? `https://upload.local/${encodeURIComponent(imageFile.name)}` : '',
    imageFile,
    motion_prompt: String(form.get('motion_prompt') || ''),
    duration_seconds: Number(form.get('duration_seconds')),
    model: String(form.get('model')),
    enterprise_mode: Boolean(form.get('enterprise_mode')),
    tenant_watermark: form.get('tenant_watermark_text')
      ? { text: String(form.get('tenant_watermark_text')) }
      : undefined
  };

  const errors = validateImageJob(payload);
  if (errors.length) {
    state.lastErrorHtml = `<div class="error-box"><strong>Please fix:</strong><ul>${errors.map((v) => `<li>${v}</li>`).join('')}</ul></div>`;
    render();
    return;
  }

  try {
    const requestPayload = {
      image_url: payload.image_url,
      motion_prompt: payload.motion_prompt,
      duration_seconds: payload.duration_seconds,
      model: payload.model,
      enterprise_mode: payload.enterprise_mode,
      tenant_watermark: payload.tenant_watermark
    };

    const job = await submitImageToVideo(requestPayload);
    state.jobs.unshift(job);
    state.tab = 'jobs';
    render();
    await trackJob(job.id);
  } catch (error) {
    state.lastErrorHtml = renderSafetyError(error);
    render();
  }
}

async function trackJob(jobId) {
  await pollJob(jobId, (job) => {
    const idx = state.jobs.findIndex((j) => j.id === job.id);
    if (idx >= 0) state.jobs[idx] = job;
    else state.jobs.unshift(job);
    render();
  }, 2500);
}

async function openPreview(assetId) {
  try {
    const asset = await getAsset(assetId);
    const provenance = await getAssetProvenance(assetId).catch(() => null);
    state.selectedAsset = asset;
    state.selectedProvenance = provenance;
    state.tab = 'preview';
    render();
  } catch (error) {
    state.lastErrorHtml = renderSafetyError(error);
    render();
  }
}

render();
