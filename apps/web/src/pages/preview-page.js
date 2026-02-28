export function renderPreviewPage(state) {
  const asset = state.selectedAsset;
  const provenance = state.selectedProvenance;

  if (!asset) {
    return '<div class="card"><h2>Result Preview</h2><p>Select a completed asset to preview and download.</p></div>';
  }

  return `
    <div class="card">
      <h2>Result Preview</h2>
      <div class="preview-frame">
        <video class="preview-video" controls src="${asset.url}"></video>
        <div class="generated-label">Generated Content · AI Synthesized</div>
      </div>
      <p class="hint">Job: ${asset.job_id} · Asset: ${asset.id}</p>
      <button class="primary" data-download-asset="${asset.url}">Download</button>
      ${provenance ? `
      <div class="hint">
        Provenance hash: <code>${provenance.metadata_hash}</code><br/>
        Model: ${provenance.model_id} (${provenance.model_version})
      </div>` : ''}
    </div>
  `;
}
