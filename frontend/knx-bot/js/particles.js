/* ═══════════════════════════════════════════════════════════════
   Sintrix — Connected Particle Network (Synced & Persistent)
   ═══════════════════════════════════════════════════════════════ */
(function () {
  'use strict';

  const canvas = document.getElementById('bot-particles');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  let W, H, particles = [], mouse = { x: -9999, y: -9999 };

  const COUNT = 100, SPEED = 0.15, CONNECT_DIST = 140, MOUSE_REPEL = 100;

  function resize() {
    W = canvas.width = window.innerWidth;
    H = canvas.height = window.innerHeight;
  }

  function mkParticle(existing = null) {
    return {
      x: existing ? existing.x : Math.random() * W,
      y: existing ? existing.y : Math.random() * H,
      vx: existing ? existing.vx : (Math.random() - 0.5) * SPEED,
      vy: existing ? existing.vy : (Math.random() - 0.5) * SPEED,
      r: existing ? existing.r : Math.random() * 1.8 + 0.6,
      alpha: existing ? existing.alpha : Math.random() * 0.5 + 0.2
    };
  }

  function init() {
    resize();
    const stored = sessionStorage.getItem(STORAGE_KEY);
    if (stored) {
      try {
        const data = JSON.parse(stored);
        particles = data.map(p => mkParticle(p));
      } catch (e) {
        particles = Array.from({ length: COUNT }, mkParticle);
      }
    } else {
      particles = Array.from({ length: COUNT }, mkParticle);
    }
  }

  function saveState() {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(particles.map(p => ({
      x: p.x, y: p.y, vx: p.vx, vy: p.vy, r: p.r, alpha: p.alpha
    }))));
  }

  let frameCount = 0;
  function draw() {
    ctx.clearRect(0, 0, W, H);

    // Radial glow orbs (Synced with Reference)
    const orbs = [
      { x: W * 0.2, y: H * 0.3, r: 280, c: 'rgba(34,211,238,0.04)' },
      { x: W * 0.8, y: H * 0.7, r: 220, c: 'rgba(6,182,212,0.03)' }
    ];
    orbs.forEach(o => {
      const g = ctx.createRadialGradient(o.x, o.y, 0, o.x, o.y, o.r);
      g.addColorStop(0, o.c);
      g.addColorStop(1, 'transparent');
      ctx.fillStyle = g;
      ctx.beginPath();
      ctx.arc(o.x, o.y, o.r, 0, Math.PI * 2);
      ctx.fill();
    });

    // Move & repel
    particles.forEach(p => {
      const dx = p.x - mouse.x, dy = p.y - mouse.y;
      const dist = Math.sqrt(dx * dx + dy * dy);
      if (dist < MOUSE_REPEL) {
        const force = (MOUSE_REPEL - dist) / MOUSE_REPEL * 0.8;
        p.vx += (dx / dist) * force;
        p.vy += (dy / dist) * force;
      }
      p.vx *= 0.98; p.vy *= 0.98;
      p.x += p.vx; p.y += p.vy;

      if (p.x < 0) p.x = W; if (p.x > W) p.x = 0;
      if (p.y < 0) p.y = H; if (p.y > H) p.y = 0;
    });

    // Connections
    for (let i = 0; i < particles.length; i++) {
      for (let j = i + 1; j < particles.length; j++) {
        const a = particles[i], b = particles[j];
        const dx = a.x - b.x, dy = a.y - b.y;
        const d = Math.sqrt(dx * dx + dy * dy);
        if (d < CONNECT_DIST) {
          ctx.strokeStyle = `rgba(34,211,238,${0.15 * (1 - d / CONNECT_DIST)})`;
          ctx.lineWidth = 0.7;
          ctx.beginPath();
          ctx.moveTo(a.x, a.y);
          ctx.lineTo(b.x, b.y);
          ctx.stroke();
        }
      }
    }

    // Dots
    particles.forEach(p => {
      ctx.fillStyle = `rgba(34,211,238,${p.alpha})`;
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
      ctx.fill();
    });

    if (frameCount++ % 10 === 0) saveState();
    requestAnimationFrame(draw);
  }

  window.addEventListener('resize', resize);
  window.addEventListener('mousemove', e => {
    const rect = canvas.getBoundingClientRect();
    mouse.x = e.clientX - rect.left;
    mouse.y = e.clientY - rect.top;
  });
  window.addEventListener('mouseleave', () => { mouse.x = -9999; mouse.y = -9999; });

  init();
  draw();
})();
