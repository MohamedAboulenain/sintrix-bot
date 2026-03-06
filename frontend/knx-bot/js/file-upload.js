/**
 * File Upload handler
 *
 * Exports:
 *   initUpload({ onSessionReady, onSessionCleared })
 *
 * Handles:
 *   - Click-to-open file dialog
 *   - Drag-and-drop anywhere on the page
 *   - Upload progress badge
 *   - File removal / session clearing
 */

const API_BASE = window.KNX_API_BASE || '';

export function initUpload({ onSessionReady, onSessionCleared }) {
  const uploadBtn      = document.getElementById('upload-btn');
  const fileInput      = document.getElementById('file-input');
  const uploadBadge    = document.getElementById('upload-badge');
  const badgeName      = document.getElementById('badge-name');
  const progressBar    = document.getElementById('badge-progress-bar');
  const badgeRemove    = document.getElementById('badge-remove');
  const dropOverlay    = document.getElementById('drop-overlay');

  let dragCounter = 0;

  // ── Click to upload ─────────────────────────────────────────
  uploadBtn.addEventListener('click', () => fileInput.click());

  fileInput.addEventListener('change', () => {
    const file = fileInput.files[0];
    if (file) _startUpload(file);
    fileInput.value = '';
  });

  // ── Drag and drop ───────────────────────────────────────────
  document.addEventListener('dragenter', e => {
    if (!_hasFiles(e)) return;
    dragCounter++;
    dropOverlay.classList.add('active');
  });

  document.addEventListener('dragleave', () => {
    dragCounter--;
    if (dragCounter <= 0) {
      dragCounter = 0;
      dropOverlay.classList.remove('active');
    }
  });

  document.addEventListener('dragover', e => { e.preventDefault(); });

  document.addEventListener('drop', e => {
    e.preventDefault();
    dragCounter = 0;
    dropOverlay.classList.remove('active');
    const file = e.dataTransfer.files[0];
    if (file) _startUpload(file);
  });

  // ── Remove badge ────────────────────────────────────────────
  badgeRemove.addEventListener('click', () => {
    _clearBadge();
    onSessionCleared();
  });

  // ── Upload logic ────────────────────────────────────────────
  async function _startUpload(file) {
    const allowed = ['.pdf', '.xlsx', '.xls'];
    const ext = file.name.slice(file.name.lastIndexOf('.')).toLowerCase();
    if (!allowed.includes(ext)) {
      _showError(`Unsupported file type "${ext}". Use PDF or Excel.`);
      return;
    }

    _showBadge(file.name, 0);

    const formData = new FormData();
    formData.append('file', file);

    try {
      // Simulate initial progress while uploading
      _setProgress(30);

      const res = await fetch(`${API_BASE}/api/v1/upload`, {
        method: 'POST',
        body: formData,
      });

      _setProgress(80);

      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Upload failed.' }));
        throw new Error(err.detail || 'Upload failed.');
      }

      const data = await res.json();
      _setProgress(100);

      setTimeout(() => {
        progressBar.style.display = 'none';
      }, 600);

      onSessionReady(data.session_id, file.name);

    } catch (err) {
      _clearBadge();
      _showError(err.message || 'Upload failed.');
    }
  }

  function _showBadge(filename, progress) {
    badgeName.textContent = filename;
    progressBar.style.display = 'block';
    progressBar.style.width = progress + '%';
    uploadBadge.style.display = 'flex';
  }

  function _setProgress(pct) {
    progressBar.style.width = pct + '%';
  }

  function _clearBadge() {
    uploadBadge.style.display = 'none';
    badgeName.textContent = '';
    progressBar.style.width = '0%';
    progressBar.style.display = 'block';
  }

  function _showError(msg) {
    // Briefly show error in upload btn
    const orig = uploadBtn.textContent;
    uploadBtn.textContent = `❌ ${msg.slice(0, 40)}`;
    uploadBtn.style.color = 'var(--error)';
    setTimeout(() => {
      uploadBtn.textContent = orig;
      uploadBtn.style.color = '';
    }, 3500);
  }

  function _hasFiles(e) {
    return e.dataTransfer && e.dataTransfer.types &&
           (e.dataTransfer.types.includes('Files') ||
            e.dataTransfer.types.includes('application/x-moz-file'));
  }

  // Programmatic clear — called by knx-bot after a message is sent
  function clear() {
    _clearBadge();
    onSessionCleared();
  }

  return { clear };
}
