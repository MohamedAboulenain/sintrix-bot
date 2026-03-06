/**
 * Citation renderer
 * Exports renderCitations(citations, containerEl)
 * Each citation: { number, source, excerpt }
 */

export function renderCitations(citations, containerEl) {
  if (!citations || citations.length === 0) return;

  const wrapper = document.createElement('div');
  wrapper.className = 'citations';

  citations.forEach(c => {
    const chip = document.createElement('div');
    chip.className = 'citation-chip';
    chip.title = c.excerpt || c.source;

    const num = document.createElement('span');
    num.className = 'citation-num';
    num.textContent = `[${c.number}]`;

    const src = document.createElement('span');
    src.textContent = c.source ? _shorten(c.source) : 'KNX Spec';

    chip.appendChild(num);
    chip.appendChild(src);
    wrapper.appendChild(chip);
  });

  containerEl.appendChild(wrapper);
}

function _shorten(name, max = 32) {
  return name.length > max ? name.slice(0, max - 1) + '…' : name;
}
