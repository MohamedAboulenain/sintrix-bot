# Sintrix KNX Bot — RAG4

## Project Purpose
KNX building automation expert chatbot for sintrix.io.
Backend: FastAPI. Frontend: Vanilla HTML/CSS/JS.
AI: Google NotebookLM (via notebooklm-py) + OpenAI GPT-4o.

## Tech Stack
- Python 3.11+ with FastAPI + uvicorn
- notebooklm-py (NotebookLM API wrapper — unofficial, session-auth via Playwright)
- OpenAI API (user-doc queries + PDF/Excel generation)
- PyMuPDF (PDF text extraction), ReportLab (PDF generation)
- openpyxl (Excel read/write)
- Vanilla JS + HTML5 + CSS3 (no frameworks)

## Local Development
1. Create .env from .env.example and fill in secrets
2. pip install -r requirements.txt
3. playwright install chromium        (for notebooklm-py auth)
4. notebooklm login                   (one-time browser auth, saves session)
5. uvicorn backend.main:app --reload --port 8000
6. Open http://localhost:8000         (Home page)
7. Open http://localhost:8000/knx-bot (KNX Bot)

## Key Env Vars
- NOTEBOOKLM_NOTEBOOK_ID  — copy from NotebookLM notebook URL
- OPENAI_API_KEY           — for user-doc Q&A and PDF/Excel generation
- NLM_DAILY_QUOTA          — max NotebookLM queries/day (default 50)
- CORS_ORIGINS             — comma-separated list (default includes localhost:8000)

## Architecture Notes
- FastAPI serves the frontend via StaticFiles mount at "/" for local dev
- Route GET /knx-bot explicitly returns frontend/knx-bot/index.html
- All API routes are prefixed /api/v1/
- Sessions are file-based JSON in data/sessions/ with 24h TTL
- User uploads go to data/temp_uploads/ and expire with sessions

## Chat Modes
- knx:      Query NotebookLM "Sintrix KNX Bot" notebook directly
- user:     Query user-uploaded PDF/Excel via OpenAI
- combined: NotebookLM answer + user-doc context merged by OpenAI

## Conversation History
- Frontend (`knx-bot.js`) accumulates `{role, content}` pairs in `conversationHistory[]`
- Each chat POST includes `history: conversationHistory.slice(-20)` (last 20 messages)
- History resets when user removes uploaded document (clean slate per document)
- OpenAI modes: history is inserted as native messages between system prompt and current user message (last 10 messages)
- NotebookLM mode: last 6 history messages are prepended as plain-text context block (library has no native multi-turn)

## Generation (Auto-detect)
- `_detectGenerationIntent()` in knx-bot.js auto-routes to PDF/Excel without explicit buttons
- Triggers on action verbs (generate, create, make, etc.) + file type keywords
- File upload badge clears automatically after any message is sent

## Deployment
- Docker + docker-compose: `docker-compose up -d`
- Requires `.env` file in project root (never committed)
- Nginx reverse proxy handles HTTPS + static serving in production
- Production server: `gunicorn backend.main:app -k uvicorn.workers.UvicornWorker`
- `notebooklm login` must be run once on the production host before starting

## File Structure
backend/
  main.py            — FastAPI app, lifespan, static mount, routers
  config.py          — Pydantic BaseSettings (reads .env)
  routers/
    health.py        — GET  /api/v1/health
    chat.py          — POST /api/v1/chat  (SSE streaming)
    upload.py        — POST /api/v1/upload
    generate.py      — POST /api/v1/generate/pdf|excel
  services/
    notebooklm_service.py — notebooklm-py async wrapper + quota tracking
    openai_service.py     — GPT-4o calls for user-doc Q&A and generation
    pdf_service.py        — PyMuPDF extract + ReportLab write
    excel_service.py      — openpyxl extract + write
  session/
    manager.py       — create/load/expire file-based sessions

frontend/
  index.html              — Home / landing page
  knx-bot/
    index.html            — KNX Bot chat UI
    css/
      main.css            — shared design tokens + nav + global styles
      knx-bot.css         — bot page layout and components
    js/
      particles.js        — canvas particle system (two layers)
      knx-bot.js          — chat logic, SSE, mode switching
      file-upload.js      — drag-drop upload, progress badge
      citation-renderer.js — citation chips rendered after stream

## Design System
- Background primary:   #0a0e27  (dark navy)
- Background secondary: #0f1535
- Background card:      #131a3a
- Accent cyan:          #22d3ee
- Accent cyan dim:      #06b6d4
- Text primary:         #e2e8f0
- Text muted:           #64748b
- Border:               rgba(34,211,238,0.2)
- Font:                 system-ui / -apple-system stack
- Nav height:           64px (fixed, glass effect)
- Particle canvas:      two layers, rising dots + floating orbs

## Commands
- Start server:   uvicorn backend.main:app --reload --port 8000
- Health check:   curl http://localhost:8000/api/v1/health
- View API docs:  http://localhost:8000/docs
