/**
 * Sintrix KNX Bot — Main chat logic
 *
 * Handles:
 *   - Health check + status indicator
 *   - Mode switching (knx / user / combined)
 *   - Sending messages + SSE streaming
 *   - Message rendering (with lightweight markdown)
 *   - Welcome chip clicks
 *   - Generate PDF / Excel
 *   - File upload integration
 */

import { renderCitations } from './citation-renderer.js';
import { initUpload }       from './file-upload.js';

const API  = window.KNX_API_BASE || '';
const $ = id => document.getElementById(id);

// ── State ─────────────────────────────────────────────────────
let currentMode          = 'knx';   // 'knx' | 'user' | 'combined'
let sessionId            = null;    // uploaded-file session
let isStreaming          = false;
let conversationHistory  = [];      // [{role, content}, ...]

// ── DOM refs ──────────────────────────────────────────────────
const chatWindow  = $('chat-window');
const chatInput   = $('chat-input');
const sendBtn     = $('send-btn');
const statusDot   = $('status-dot');
const statusText  = $('status-text');
const welcome     = $('welcome');
const modeUser    = $('mode-user');
const modeCombined= $('mode-combined');

// ── Health check ──────────────────────────────────────────────
async function checkHealth() {
  try {
    const res = await fetch(`${API}/api/v1/health`);
    if (!res.ok) throw new Error();
    const data = await res.json();
    _setStatus(data.notebooklm ? 'online' : 'offline',
               data.notebooklm ? `Online · ${data.quota_remaining}/${data.quota_limit} queries left`
                                : 'KNX Docs unavailable');
  } catch {
    _setStatus('offline', 'Server unreachable');
  }
}

// Poll health every 30s to keep status fresh
setInterval(checkHealth, 30_000);

function _setStatus(state, text) {
  statusDot.className  = `status-dot ${state}`;
  statusText.textContent = text;
}

// ── Mode switching ────────────────────────────────────────────
document.querySelectorAll('.mode-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    if (btn.disabled) return;
    document.querySelectorAll('.mode-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    currentMode = btn.dataset.mode;
  });
});

// ── Upload integration ────────────────────────────────────────
const upload = initUpload({
  onSessionReady: (sid, filename) => {
    sessionId = sid;
    modeUser.disabled     = false;
    modeCombined.disabled = false;
    // Auto-switch to user mode when file loaded
    document.querySelectorAll('.mode-btn').forEach(b => b.classList.remove('active'));
    modeUser.classList.add('active');
    currentMode = 'user';
  },
  onSessionCleared: () => {
    sessionId = null;
    conversationHistory = [];
    modeUser.disabled     = true;
    modeCombined.disabled = true;
    // Fall back to KNX mode
    document.querySelectorAll('.mode-btn').forEach(b => b.classList.remove('active'));
    document.querySelector('[data-mode="knx"]').classList.add('active');
    currentMode = 'knx';
  },
});

// ── Auto-resize textarea ──────────────────────────────────────
chatInput.addEventListener('input', () => {
  chatInput.style.height = 'auto';
  chatInput.style.height = Math.min(chatInput.scrollHeight, 140) + 'px';
});

// ── Send on Enter (Shift+Enter = newline) ─────────────────────
chatInput.addEventListener('keydown', e => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    _sendMessage();
  }
});

sendBtn.addEventListener('click', _sendMessage);

// ── Welcome chips ─────────────────────────────────────────────
document.querySelectorAll('.chip').forEach(chip => {
  chip.addEventListener('click', () => {
    chatInput.value = chip.textContent.trim();
    chatInput.dispatchEvent(new Event('input'));
    _sendMessage();
  });
});

// ── Generation intent detection ───────────────────────────────
function _detectGenerationIntent(text) {
  const lower = text.toLowerCase();
  const hasVerb = /\b(generate|create|make|produce|export|write|build|draft|prepare|give me)\b/.test(lower);
  if (!hasVerb) return null;
  if (/\b(excel|spreadsheet|xlsx?|sheet)\b/.test(lower)) return 'excel';
  if (/\b(pdf|report|document|letter|summary)\b/.test(lower)) return 'pdf';
  return null;
}

async function _generateFile(type, prompt, capturedSession) {
  const endpoint = type === 'pdf' ? 'generate/pdf' : 'generate/excel';
  const { bubble } = _appendBotTyping();

  try {
    const res = await fetch(`${API}/api/v1/${endpoint}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ prompt, session_id: capturedSession }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Generation failed.' }));
      throw new Error(err.detail);
    }
    const blob  = await res.blob();
    const url   = URL.createObjectURL(blob);
    const a     = document.createElement('a');
    const cd    = res.headers.get('Content-Disposition') || '';
    const match = cd.match(/filename="([^"]+)"/);
    a.href     = url;
    a.download = match ? match[1] : `sintrix_knx.${type === 'pdf' ? 'pdf' : 'xlsx'}`;
    a.click();
    URL.revokeObjectURL(url);
    bubble.innerHTML = _markdownToHtml(`✅ **${type.toUpperCase()} generated:** ${a.download}`);
  } catch (err) {
    bubble.innerHTML = `<em style="color:var(--error)">⚠️ ${_esc(err.message)}</em>`;
  }
  _scrollToBottom();
}

// ── Send message ──────────────────────────────────────────────
async function _sendMessage() {
  const text = chatInput.value.trim();
  if (!text || isStreaming) return;

  _hideWelcome();
  _appendUserMessage(text);
  chatInput.value = '';
  chatInput.style.height = 'auto';

  // Capture session before any clearing, then clear the badge
  const capturedSession = sessionId;
  if (capturedSession) upload.clear();

  // Route to file generation if intent is detected
  const genType = _detectGenerationIntent(text);
  if (genType) {
    await _generateFile(genType, text, capturedSession);
    return;
  }

  // Record user turn in history before sending
  conversationHistory.push({ role: 'user', content: text });

  isStreaming = true;
  sendBtn.disabled = true;

  const { bubble, bodyEl } = _appendBotTyping();

  try {
    const res = await fetch(`${API}/api/v1/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message: text,
        mode: currentMode,
        session_id: capturedSession,
        history: conversationHistory.slice(-20),
      }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Request failed.' }));
      throw new Error(err.detail || 'Request failed.');
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let fullText = '';
    let citations = [];
    let buffer = '';

    // Remove typing dots
    bubble.innerHTML = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      const lines = buffer.split('\n');
      buffer = lines.pop(); // keep incomplete line

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue;
        const raw = line.slice(6).trim();
        if (!raw) continue;
        try {
          const event = JSON.parse(raw);
          if (event.token !== undefined) {
            fullText += event.token;
            bubble.innerHTML = _markdownToHtml(fullText);
            _scrollToBottom();
          }
          if (event.done) {
            citations = event.citations || [];
            if (event.quota_warning) {
              const warn = document.createElement('div');
              warn.className = 'quota-banner';
              warn.textContent = `⚠️ ${event.quota_remaining} KNX queries remaining today`;
              bodyEl.appendChild(warn);
            }
          }
        } catch { /* skip malformed */ }
      }
    }

    // Record assistant reply in history
    if (fullText) conversationHistory.push({ role: 'assistant', content: fullText });

    // Render citations below the bubble
    if (citations.length > 0) {
      renderCitations(citations, bodyEl);
    }

  } catch (err) {
    bubble.innerHTML = `<em style="color:var(--error)">⚠️ ${_esc(err.message)}</em>`;
  } finally {
    isStreaming = false;
    sendBtn.disabled = false;
    _scrollToBottom();
  }
}

// ── DOM helpers ───────────────────────────────────────────────
function _hideWelcome() {
  if (welcome) welcome.style.display = 'none';
}

function _appendUserMessage(text) {
  const msg = document.createElement('div');
  msg.className = 'msg user';
  msg.innerHTML = `
    <div class="msg-avatar">You</div>
    <div class="msg-body">
      <div class="msg-bubble">${_esc(text)}</div>
    </div>`;
  chatWindow.appendChild(msg);
  _scrollToBottom();
}

function _appendBotTyping() {
  const msg = document.createElement('div');
  msg.className = 'msg bot';

  const body = document.createElement('div');
  body.className = 'msg-body';

  const bubble = document.createElement('div');
  bubble.className = 'msg-bubble';
  bubble.innerHTML = `<div class="typing-dots"><span></span><span></span><span></span></div>`;

  body.appendChild(bubble);
  msg.innerHTML = `<div class="msg-avatar">KNX</div>`;
  msg.appendChild(body);
  chatWindow.appendChild(msg);
  _scrollToBottom();
  return { bubble, bodyEl: body };
}

function _scrollToBottom() {
  chatWindow.scrollTop = chatWindow.scrollHeight;
}

// ── Lightweight markdown → HTML ───────────────────────────────
function _markdownToHtml(md) {
  return md
    // Code blocks
    .replace(/```[\w]*\n?([\s\S]*?)```/g, (_, code) =>
      `<pre><code>${_esc(code.trim())}</code></pre>`)
    // Tables — must run before newline transforms
    .replace(/^\|(.+)\|\s*\n\|[-:\s|]+\|\s*\n((?:\|.+\|[ \t]*\n?)*)/gm, (_, headerRow, bodyRows) => {
      const headers = headerRow.split('|').map(h => h.trim()).filter(Boolean);
      const headerHtml = `<thead><tr>${headers.map(h => `<th>${_esc(h)}</th>`).join('')}</tr></thead>`;
      const rows = bodyRows.trim().split('\n').filter(r => r.trim()).map(row => {
        const cells = row.split('|').map(c => c.trim()).filter(Boolean);
        return `<tr>${cells.map(c => `<td>${_esc(c)}</td>`).join('')}</tr>`;
      }).join('');
      return `<div class="table-wrapper"><table class="md-table">${headerHtml}<tbody>${rows}</tbody></table></div>`;
    })
    // Inline code
    .replace(/`([^`]+)`/g, (_, c) => `<code>${_esc(c)}</code>`)
    // Bold
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    // Italic
    .replace(/\*(.+?)\*/g,     '<em>$1</em>')
    // H2 / H3
    .replace(/^### (.+)$/gm,   '<h3>$1</h3>')
    .replace(/^## (.+)$/gm,    '<h2>$1</h2>')
    .replace(/^# (.+)$/gm,     '<h1>$1</h1>')
    // Bullet lists
    .replace(/^[*-] (.+)$/gm,  '<li>$1</li>')
    .replace(/(<li>[\s\S]*?<\/li>)/g, '<ul>$1</ul>')
    // Numbered lists
    .replace(/^\d+\. (.+)$/gm, '<li>$1</li>')
    // Line breaks (double newline = paragraph)
    .replace(/\n{2,}/g, '</p><p>')
    .replace(/\n/g, '<br>')
    // Wrap in paragraph if not starting with a block element
    .replace(/^(?!<[hup]|<pre|<ul|<ol|<div)(.+)/s, '<p>$1</p>');
}

function _esc(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

// ── Mobile keyboard fix (Visual Viewport API) ─────────────────
// iOS Safari doesn't resize the layout viewport when the soft keyboard opens.
// visualViewport.height gives the actual usable height on both iOS and Android.
if (window.visualViewport) {
  const _setAppHeight = () =>
    document.documentElement.style.setProperty('--app-height', window.visualViewport.height + 'px');
  window.visualViewport.addEventListener('resize', _setAppHeight);
  _setAppHeight();
}

// ── Init ──────────────────────────────────────────────────────
checkHealth();
