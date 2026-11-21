# YouTube Video Summarizer App - Detailed Plan

## Overview

A self-hosted web application that processes YouTube videos (and optional local files), extracts transcripts via Whisper AI, generates AI-powered summaries, and maintains a searchable history with full-text search across all transcribed content.

The app is designed for **single-user deployment** but with extensible architecture for multi-tenancy later. All data persists in a local SQLite database. The entire stack is containerized via Docker Compose.

---

## Goals

| Goal | Description |
|------|-------------|
| **Searchable history** | Every processed video is stored and searchable by title, description, and **full transcript text** |
| **OpenRouter LLM support** | Configurable API key supports free and paid models through OpenRouter (Claude, Gemini, Llama, Mistral, etc.) |
| **One-command Docker deploy** | `docker compose up -d` from `~/docker-compose/youtube-summarizer/` starts the full stack |
| **Transcript + summary viewing** | UI shows transcript with timestamps + summary side-by-side |
| **Full-text search** | Search box queries across ALL stored transcripts, highlighting matching moments |
| **Local-first data** | SQLite database lives in `~/docker-compose/youtube-summarizer/data/` — no external services required beyond OpenRouter API |

---

## Feature Set (MVP)

### Core Features

1. **📥 YouTube Video Processing**
   - Paste YouTube URL → process
   - Extract native captions via `yt-dlp` (fast, no audio download)
   - Fallback: download audio → `faster-whisper` transcription (if no captions)
   - Progress tracking via Server-Sent Events (SSE)

2. **🤖 AI Summarization**
   - Configurable OpenRouter model selection (dropdown UI)
   - Default free model: `anthropic/claude-3-haiku-20240307`
   - Other options: `google/gemini-1.5-flash`, `mistral/mistral-large-2402`, `meta-llama/llama-3.1-8b-instruct`
   - Summary stored in DB with model name referenced

3. **📚 Searchable History**
   - Grid/list view of all processed videos
   - Each card: video title, date processed, video duration, word count of transcript
   - Click to expand: transcript + summary collapsible view
   - Each entry links back to original YouTube URL (opens in new tab)

4. **🔍 Full-Text Search**
   - Search box at top of history page
   - Queries across all stored transcript text via SQLite FTS5
   - Results show: matching video entries + timestamp links
   - Click a result → jumps to that moment in the transcript view

5. **⚙️ Configuration**
   - `.env` file with `OPENROUTER_API_KEY`
   - Model selector in UI (fetches available models from OpenRouter API at startup)
   - Optional: `WHISPER_MODEL_SIZE` (default: `base`, options: `tiny`, `base`, `small`, `medium`, `large`)

### Bonus (Phase 2)

- Local file upload (mp4/mp3 → extract audio → transcribe)
- User authentication (simple password hash)
- Folder/collection organization
- Export summaries as Markdown/JSON
- API endpoints for external integration

---

## Tech Stack

| Layer | Technology | Notes |
|-------|-----------|-------|
| **Frontend** | React 18 + Vite + TypeScript | Vanilla CSS or Tailwind CDN |
| **UI State** | React Hook Form + Zod validation | For URL input, model selector |
| **Backend** | Python 3.11 + FastAPI | Async support, automatic OpenAPI docs |
| **Transcription** | `faster-whisper` | Runs locally — no GPU required for base model |
| **YouTube DL** | `yt-dlp` | Extracts native captions; fallback to audio |
| **LLM** | OpenRouter API (`https://openrouter.ai/api/v1`) | Single key for multiple models |
| **Database** | SQLite 3 + FTS5 | Full-text search virtual table |
| **Container** | Python + Nginx multi-stage Docker | Small final image |
| **Orchestration** | Docker Compose v2 | Single `docker compose up` |

### OpenRouter Models (free tier priority)

| Model ID | Provider | Context Window | Cost/1K tokens |
|----------|----------|----------------|----------------|
| `anthropic/claude-3-haiku-20240307` | Anthropic | 200K | very low (free tier available) |
| `google/gemini-1.5-flash` | Google | 1M | free tier generous |
| `mistral/mistral-large-2402` | Mistral | 128K | moderate |
| `meta-llama/llama-3.1-8b-instruct` | Meta | 8K | free tier |

---

## Environment Configuration

### `.env` File (placed in `~/docker-compose/youtube-summarizer/`)

```env
# OpenRouter API Key (REQUIRED)
# Get free key at: https://openrouter.ai
OPENROUTER_API_KEY=your_openrouter_key_here

# Default model for summarization (change via UI or .env)
# Free tier recommendations:
# - anthropic/claude-3-haiku-20240307 (fast, cheap)
# - google/gemini-1.5-flash (very generous free tier)
OPENROUTER_DEFAULT_MODEL=anthropic/claude-3-haiku-20240307

# Whisper model size (runs locally, no API key needed)
# Options: tiny, base, small, medium, large
# Larger = better accuracy but slower + more CPU/Memory
WHISPER_MODEL_SIZE=base

# Application
APP_NAME=youtube-summarizer
APP_URL=http://localhost:8000
```

### Docker Compose Volume Mapping

```yaml
volumes:
  - ./data:/app/data     # SQLite database persists here
  - ./frontend/dist:/usr/share/nginx/html  # frontend build
```

---

## Database Schema (SQLite)

### `videos` table

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| url | TEXT | Original YouTube URL |
| video_id | TEXT | YouTube video ID (extracted from URL) |
| title | TEXT | Video title (from captions/metadata) |
| created_at | DATETIME | When first processed |
| updated_at | DATETIME | When last processed |

### `transcriptions` table

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| video_id | INTEGER | FK → videos.id |
| full_text | TEXT | Complete Whisper transcript (may be large) |
| text | TEXT | **FTS5 content** — used for full-text search |

> **FTS5 Virtual Table**: A separate FTS5 table `transcriptions_fts` is created on the `text` column of `transcriptions`. This enables `MATCH` queries for full-text search.

### `summaries` table

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| video_id | INTEGER | FK → videos.id |
| summary_text | TEXT | The AI-generated summary |
| model_used | TEXT | OpenRouter model ID that generated this summary |
| created_at | DATETIME | When summary was generated |

### Indexes

- `idx_summaries_video_id` on `summaries.video_id`
- FTS5 index on `transcriptions.text`

---

## API Endpoints

### Backend (FastAPI) — `GET /api/docs` auto-generates Swagger

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `GET /` | `/` | None | Main UI (serves React app) |
| `POST /api/process` | `/process` | None | Start video processing (returns job ID) |
| `GET /api/history` | `/history` | None | List all processed videos |
| `GET /api/search` | `/search` | None | Full-text search across transcripts |
| `GET /api/transcript/{video_id}` | `/transcript/{id}` | None | Get transcript + summary for a video |
| `GET /api/models` | `/models` | None | List available OpenRouter models (fetched at startup) |

### `POST /api/process`

**Request:**
```json
{
  "url": "https://www.youtube.com/watch?v=VIDEO_ID",
  "model": "anthropic/claude-3-haiku-20240307"  // optional, uses default if omitted
}
```

**Response (202):**
```json
{
  "job_id": "unique-job-id",
  "status": "processing",
  "message": "Processing started — check /api/status/{job_id} or /history"
}
```

The backend processes synchronously ( Whisper + OpenRouter call), but returns a job ID for async polling if needed.

### `GET /api/history`

**Response:**
```json
[
  {
    "id": 1,
    "title": "How to bake bread",
    "video_id": "abcd1234",
    "url": "https://www.youtube.com/watch?v=abcd1234",
    "created_at": "2024-01-15T10:30:00Z",
    "transcript_words": 1245,
    "summary_length": "150 words"
  },
  ...
]
```

### `GET /api/search?q=query`

**Response:**
```json
{
  "query": "ransomware",
  "hits": [
    {
      "video_id": 1,
      "title": "How to bake bread",
      "matched_text": "...ransomware...",
      "timestamp_start": 123.5,
      "timestamp_end": 127.2,
      "snippet": "...ransomware protection measures...",
      "url": "https://www.youtube.com/watch?v=abcd1234"
    }
  ]
}
```

### `GET /api/transcript/{video_id}`

**Response:**
```json
{
  "video": {
    "id": 1,
    "title": "How to bake bread",
    "url": "https://www.youtube.com/watch?v=abcd1234"
  },
  "transcript": [
    {"timestamp": 0.0, "text": "Hello and welcome..."},
    {"timestamp": 5.3, "text": "Today we're going to talk about..."},
    ...
  ],
  "summary": "Summary goes here...",
  "model_used": "anthropic/claude-3-haiku-20240307"
}
```

---

## Docker Compose Configuration

### Folder Structure (per user requirement)

```
~/docker-compose/
└── youtube-summarizer/
    ├── docker-compose.yml
    ├── .env
    ├── Dockerfile
    ├── requirements.txt
    ├── app/
    │   ├── main.py
    │   ├── routes.py
    │   └── ...
    └── frontend/
        ├── vite.config.js
        ├── src/
        │   ├── main.jsx
        │   ├── App.jsx
        │   └── ...
        └── index.html
```

### `~/docker-compose/youtube-summarizer/docker-compose.yml`

```yaml
version: "3.9"

services:
  backend:
    build: .
    container_name: yt_summarizer_backend
    restart: unless-stopped
    ports:
      - "8000:8000"
    env_file:
      - .env
    volumes:
      - ./data:/app/data:cached
    depends_on:
      - none  # No external deps; Whisper runs locally, OpenRouter is HTTP

  frontend:
    image: nginx:alpine
    container_name: yt_summarizer_frontend
    restart: unless-stopped
    ports:
      - "3000:80"
    volumes:
      - ./frontend/dist:/usr/share/nginx/html:ro
    depends_on:
      - backend

# Optional: add a Redis cache for processing jobs if going async later
# redis:
#   image: redis:7-alpine
#   container_name: yt_summarizer_redis
#   restart: unless-stopped
#   ports:
#     - "6379:6379"
```

### `~/docker-compose/youtube-summarizer/Dockerfile`

```dockerfile
# Build stage: install deps + app
FROM python:3.11-slim AS builder

WORKDIR /app

# Install system deps (ffmpeg for Whisper, yt-dlp)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app source
COPY app/ ./app/

# Runtime stage
FROM python:3.11-slim

WORKDIR /app

# Copy from builder
COPY --from=builder /app /app
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Environment
ENV PYTHONUNBUFFERED=1

# Run
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### `~/docker-compose/youtube-summarizer/requirements.txt`

```text
fastapi>=0.109.0
uvicorn[standard]>=3.25.0
httpx>=0.27.0     # for OpenRouter API calls
yt-dlp>=2024.2.2  # YouTube metadata + captions
faster-whisper>=1.1.0  # Local transcription
pydantic>=2.7.0   # Env validation (optional)
```

### Frontend (`frontend/`)

Standard Vite + React app. Key components:

1. **`App.jsx`** — route layout:
   - `/` → Home/processing page
   - `/history` → Searchable history gallery
   - `/search` → Search page (or query param on history)

2. **`Home.jsx`** — YouTube URL input form:
   - Input field for URL
   - Model selector dropdown (fetched from `/api/models` at load)
   - "Process" button → calls `POST /api/process`
   - Shows SSE progress stream

3. **`History.jsx`** — Grid of video cards:
   - Each card: title, date, duration preview
   - Click → opens modal with transcript + summary
   - Search box at top → calls `GET /api/search?q=`

4. **`SearchResults.jsx`** — displays search hits with timestamp links

5. **`Settings.jsx`** — model config:
   - Shows current default model
   - Allows changing `OPENROUTER_DEFAULT_MODEL`
   - Fetches available models from OpenRouter API

---

## Deployment Instructions

### Prerequisites

1. **Docker** + **Docker Compose** (v2+) installed
2. **OpenRouter API key** — sign up at <https://openrouter.ai>, get free key
3. **Git** (to clone the repo)

### Step-by-Step

```bash
# 1. Create the app directory
mkdir -p ~/docker-compose/youtube-summarizer

# 2. Clone this repo (or copy the plan files)
git clone <your-repo-url> ~/docker-compose/youtube-summarizer
# OR copy files manually from this plan

# 3. Edit .env with your OpenRouter key
cd ~/docker-compose/youtube-summarizer
cp .env.example .env
# Edit .env — add your OPENROUTER_API_KEY

# 4. Start the stack
docker compose up -d

# 5. Wait ~30s, then open:
open http://localhost:3000   # frontend
# OR: open http://localhost:8000/api/docs  # backend Swagger UI
```

### First-Time Setup

1. The app fetches available OpenRouter models at startup → populates the UI dropdown
2. Default model: `anthropic/claude-3-haiku-20240307`
3. Process your first YouTube URL:
   - Paste URL → select model (or use default)
   - Click "Process"
   - Watch SSE progress bar
   - After ~30-60s (depends on transcript length + API), summary appears
4. Browse history → search across all transcripts

### To Update / Restart

```bash
# Pull any image updates (if using remote registry)
docker compose pull

# Restart
docker compose up -d --build

# View logs
docker compose logs -f backend
```

---

## Future Considerations (Phase 2+)

| Feature | Value |
|---------|-------|
| **Multi-user** | Add Auth0/Google OAuth or simple password hash; per-user DB rows |
| **Folder collections** | Organize videos into named collections / tags |
| **Export** | Download summaries as Markdown/JSON; OAuth for sharing |
| **RSS subscription** | Auto-fetch new videos from subscribed channels (no API quota) |
| **Vector search** | PGVector or Qdrant for semantic search (upgrade from SQLite FTS5) |
| **Admin UI** | User management, quota tracking, model usage stats |
| **Mobile app** | PWA or native React Native companion |

---

## Success Criteria (MVP)

- [ ] `docker compose up -d` starts both services healthy
- [ ] YouTube URL processes end-to-end: transcript → summary → stored in DB
- [ ] History page shows all processed videos
- [ ] Search box queries across transcript text and returns matching videos with timestamps
- [ ] Model selector in UI works (changes which OpenRouter model is used)
- [ ] `.env` config is the only required user setup (no code changes for new models)

---

## Quick Reference: OpenRouter Model Switching

To use a different model:

1. **Via UI**: Open Settings → select from dropdown (fetches from OpenRouter API)
2. **Via `.env`**: Change `OPENROUTER_DEFAULT_MODEL=mistral/mistral-large-2402` and restart
3. **Per-processing**: The `POST /api/process` endpoint accepts optional `model` field — overrides default for that one video

**Free tier tip**: `anthropic/claude-3-haiku-20240307` and `google/gemini-1.5-flash` are the most generous free options. Monitor your OpenRouter dashboard for usage.

---

## Plan Document Location

`/home/rohit/.opencode/plan/youtube-summarizer-plan.md`

This plan can be used to:
- Build the actual application
- Assign tasks to subagents
- Reference architecture during development
- Onboard new team members

Would you like me to:
1. **Start building** the actual app files (but I'd need to switch from Plan mode — let me know if you want this)
2. **Modify anything** in this plan before proceeding
3. **Create a sub-agent** to start implementation based on this plan