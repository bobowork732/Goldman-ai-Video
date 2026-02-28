export function renderJobList(jobs) {
  const rows = jobs
    .map((job) => `
      <tr>
        <td>${job.id}</td>
        <td>${job.job_type}</td>
        <td>${job.model}</td>
        <td>${renderStatus(job.status)}</td>
        <td>${job.asset_id ? `<button data-open-preview="${job.asset_id}">Preview</button>` : '-'}</td>
      </tr>
    `)
    .join('');

  return `
    <table class="jobs-table">
      <thead>
        <tr>
          <th>ID</th>
          <th>Type</th>
          <th>Model</th>
          <th>Status</th>
          <th>Result</th>
        </tr>
      </thead>
      <tbody>${rows || '<tr><td colspan="5">No jobs yet.</td></tr>'}</tbody>
    </table>
  `;
}

function renderStatus(status) {
  const map = {
    queued: '<span class="badge warn">queued</span>',
    processing: '<span class="badge warn">processing</span>',
    completed: '<span class="badge ok">completed</span>',
    failed: '<span class="badge block">failed</span>'
  };
  return map[status] || status;
}
