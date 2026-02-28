export function renderSafetyError(error) {
  const data = error?.data;
  if (!data || !Array.isArray(data.reasons)) {
    return `<div class="error-box">${error.message || 'Unable to submit request.'}</div>`;
  }

  const items = data.reasons
    .map((r) => `<li><strong>${r.category}</strong>: ${r.message}<br/><span class="hint">Hint: ${r.actionable}</span></li>`)
    .join('');

  return `
    <div class="error-box">
      <div><strong>${data.user_safe_message || 'Your request was blocked by safety policy.'}</strong></div>
      <ul>${items}</ul>
    </div>
  `;
}
