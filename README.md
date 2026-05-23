<div align="center">

# 🎴 GitHub Dev Card Generator

### *Turn any GitHub username into a beautifully themed, AI-generated developer card.*

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Gemini](https://img.shields.io/badge/Gemini-2.5%20Flash-4285F4?logo=google&logoColor=white)](https://ai.google.dev/)
[![MCP](https://img.shields.io/badge/MCP-FastMCP-7C3AED)](https://modelcontextprotocol.io/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

</div>

---

## 📌 Overview

**GitHub Dev Card Generator** is a full-stack AI application that transforms any public GitHub profile into a personalized, shareable HTML "dev card." Users enter a username, and the system:

1. Pulls the user's profile, repositories, and language statistics from the GitHub REST API.
2. Sends a structured prompt to **Gemini 2.5 Flash** to infer the developer's *vibe*, *top skills*, *fun fact*, and *card theme*.
3. Renders a self-contained, themed HTML card and saves it to disk.
4. Streams the result back to the frontend for instant preview.

The project showcases a modern AI-engineering stack: **Google ADK + MCP tooling** as the original agentic backbone, **FastAPI** for the REST surface, and a **vanilla Nginx-served frontend** for a zero-build UI. All services are containerized and orchestrated with **Docker Compose**.

> ⚡ The hot path bypasses the agent for reliability and speed — Gemini is only invoked once per card (for analysis), making generation fast and rate-limit friendly. The agent and MCP server remain available for agent-driven workflows.

---

## ✨ Features

- 🔍 **GitHub profile scraping** — fetches profile, top 6 repos by stars, and top 5 most-used languages.
- 🧠 **AI personality analysis** — Gemini 2.5 Flash classifies the developer's vibe, skills, and theme.
- 🎨 **5 dynamic themes** — `hacker`, `builder`, `researcher`, `designer`, `open-source-hero` — each with its own palette.
- ⬇️ **Download as JPG or PDF** — render the card client-side with `html2canvas` + `jsPDF` and save it locally.
- 🔗 **Unique share link per generation** — every click of *Generate* produces a fresh `…-<id>.html` URL so links are never recycled.
- 📣 **One-click social sharing** — round icon buttons for WhatsApp, X (Twitter), Facebook, LinkedIn, Telegram, Reddit, Instagram (copy-to-clipboard) and Email.
- 💾 **Persistent cards** — saved as self-contained HTML at `/static/cards/<username>-<share_id>.html` (plus a `<username>.html` fragment for backward compatibility).
- 🛡 **Graceful degradation** — if Gemini fails or is rate-limited, a sensible fallback analysis is used (no 500 errors).
- 🔁 **Retry with exponential backoff** — built-in handling for Gemini's `429 RESOURCE_EXHAUSTED`.
- 🧩 **MCP-compatible** — the underlying tools are exposed via a FastMCP server for use by any MCP client.
- 🐳 **One-command deploy** — `docker-compose up` and you're live on `localhost:80`.

---

## 🧰 Tech Stack

| Layer | Technology |
|---|---|
| **Frontend** | HTML5, CSS3 (custom theming), vanilla JavaScript, served by **Nginx (alpine)** |
| **Backend API** | **FastAPI** + **Uvicorn** (Python 3.12, async) |
| **AI / LLM** | **Google Gemini 2.5 Flash** via `google-genai` SDK |
| **Agent framework** | **Google ADK** (`LlmAgent`) — optional agentic flow |
| **Tool protocol** | **Model Context Protocol (MCP)** via **FastMCP** over stdio |
| **HTTP client** | `httpx` (async) for GitHub REST calls |
| **Config** | `python-dotenv` for `.env` loading |
| **Containerization** | **Docker** + **Docker Compose** |
| **Package manager** | `uv` (inside backend Dockerfile) |

---

## 🏗 Architecture

```
                ┌──────────────────────┐
                │      User Browser    │
                └──────────┬───────────┘
                           │  HTTP (POST /generate)
                           ▼
        ┌──────────────────────────────────┐
        │   Frontend  (Nginx + index.html) │   :80
        └──────────────────────────────────┘
                           │
                           │  fetch → http://backend:8080
                           ▼
        ┌──────────────────────────────────┐
        │   FastAPI Backend  (main.py)     │   :8080
        │   ┌──────────────────────────┐   │
        │   │   pipeline.build_card()  │   │   ◄── direct, deterministic path
        │   └─────────────┬────────────┘   │
        └─────────────────┼────────────────┘
                          │
            ┌─────────────┼──────────────┐
            ▼             ▼              ▼
   ┌────────────┐  ┌─────────────┐  ┌──────────────┐
   │  GitHub    │  │   Gemini    │  │ Local FS     │
   │  REST API  │  │  2.5 Flash  │  │ static/cards │
   └────────────┘  └─────────────┘  └──────────────┘

        ╭──────────────── optional agentic path ────────────────╮
        │  agent.py (Google ADK LlmAgent)                       │
        │     └─► MCP stdio ─► mcp_server.py (FastMCP tools)    │
        ╰────────────────────────────────────────────────────────╯
```

**Design highlights**

- **Two execution paths.** The primary `/generate` endpoint calls a deterministic pipeline directly (fast, reliable). The legacy ADK + MCP path is preserved for clients that want true agentic orchestration.
- **Stateless backend.** Cards are written to disk and served as static files; no database required.
- **Permissive CORS.** Frontend and backend are decoupled and can be deployed independently.

---

## 🔁 How It Works — Step by Step

1. **User submits a username** in the frontend's input box.
2. **Frontend POSTs** `{ "username": "<name>" }` to `/generate` on the FastAPI backend.
3. **`scrape_github(username)`** — backend calls the GitHub REST API:
   - `GET /users/{username}` → profile fields (`name`, `avatar_url`, `bio`, `followers`, `public_repos` …)
   - `GET /users/{username}/repos?sort=updated&per_page=100` → all public repos
   - Aggregates **top 6 repos by stars** and **top 5 most-used languages**.
4. **`analyze_profile(github_data)`** — sends a structured JSON-only prompt to **Gemini 2.5 Flash** and parses the response into:
   ```json
   {
     "developer_vibe": "…",
     "top_skills": ["…", "…", "…"],
     "fun_fact": "…",
     "card_theme": "hacker | builder | researcher | designer | open-source-hero"
   }
   ```
   On `429` errors, retries with exponential backoff (10s → 20s → 40s). On terminal failure, returns a safe fallback.
5. **`generate_card_html(...)`** — picks the theme palette, injects avatar, skills, repo list, and the fun fact into a styled `<div class="card">…</div>` string.
6. **`save_card(username, html)`** — writes the HTML to `backend/static/cards/<username>.html`.
7. **Backend responds** with:
   ```json
   {
     "username": "...",
     "card_url": "/static/cards/<username>.html",
     "html": "<div class=\"card\">…</div>",
     "analysis": { ... }
   }
   ```
8. **Frontend renders** the returned HTML inline and shows a "View / Download" link to the persisted card.

---

## 📁 Project Structure

```
github-card-generator/
├── .env.example              # Template for required env vars
├── .gitignore
├── README.md
├── docker-compose.yml        # Orchestrates backend + frontend
│
├── backend/
│   ├── Dockerfile            # Python 3.12-slim + uv
│   ├── requirements.txt      # FastAPI, ADK, MCP, google-genai, httpx, …
│   ├── main.py               # FastAPI app (/generate, /card/{u}, /health)
│   ├── pipeline.py           # Deterministic 4-step pipeline (the hot path)
│   ├── mcp_server.py         # FastMCP server exposing the same 4 tools
│   ├── agent.py              # Optional Google ADK LlmAgent over MCP
│   └── static/cards/         # Generated card HTML files (gitignored)
│
└── frontend/
    ├── Dockerfile            # Nginx alpine
    └── index.html            # Single-page UI
```

---

## ⚙️ Configuration

Create `backend/.env` from the template:

```bash
cp .env.example backend/.env
```

Required and optional variables:

| Variable | Required | Description |
|---|---|---|
| `GOOGLE_API_KEY` | ✅ | Gemini API key from [Google AI Studio](https://aistudio.google.com/). |
| `GITHUB_TOKEN` | ⚪ Optional | Personal access token. Raises GitHub rate limit from **60/hr** (unauthenticated) to **5,000/hr**. |

> 🔒 `.env` is gitignored. Never commit real keys.

---

## 🚀 Getting Started

### Option A — Docker Compose (recommended)

```bash
git clone https://github.com/Premkumar1845/Github-Card-Generator.git
cd Github-Card-Generator
cp .env.example backend/.env       # then edit backend/.env with your key

docker-compose up --build
```

| Service | URL |
|---|---|
| Frontend | http://localhost |
| Backend API | http://localhost:8080 |
| Health check | http://localhost:8080/health |

### Option B — Run locally (no Docker)

**1. Backend**

```bash
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1      # Windows PowerShell
# source .venv/bin/activate       # macOS/Linux
pip install -r requirements.txt
pip install google-adk            # only needed for the agentic path
uvicorn main:app --host 0.0.0.0 --port 8080 --reload
```

**2. Frontend**

Open `frontend/index.html` directly in a browser, or serve it:

```bash
cd frontend
python -m http.server 5500
```

Make sure the frontend points at `http://localhost:8080`.

---

## 📡 API Reference

### `POST /generate`

Generate (or regenerate) a dev card.

**Request**

```json
{ "username": "octocat" }
```

**Response — 200 OK**

```json
{
  "username": "octocat",
  "card_url": "/static/cards/octocat.html",
  "share_url": "/static/cards/octocat-a1b2c3d4e5.html",
  "share_id": "a1b2c3d4e5",
  "html": "<div class=\"card\">…</div>",
  "analysis": {
    "developer_vibe": "A curious tinkerer who loves shipping micro-projects.",
    "top_skills": ["Python", "DevOps", "Open Source"],
    "fun_fact": "Maintains more dotfiles than repos.",
    "card_theme": "builder"
  }
}
```

> `share_url` is regenerated on every call (random 10-char id) so each share link is unique.
> `card_url` is kept for backward compatibility and always points to the latest fragment.

**Error responses**

| Status | When |
|---|---|
| `400` | Empty `username`. |
| `404` | GitHub user not found / private. |
| `500` | Unhandled exception (details in logs). |

### `GET /card/{username}`

Returns the URL of a previously generated card.

```json
{ "username": "octocat", "card_url": "/static/cards/octocat.html" }
```

### `GET /health`

```json
{ "status": "ok" }
```

### `GET /static/cards/{username}.html`

Direct access to the saved card (suitable for embedding via `<iframe>` or linking from a portfolio).

---

## 🎨 Card Themes

The agent picks one of these based on the analyzed profile:

| Theme | Background | Text | Accent | Suited For |
|---|---|---|---|---|
| `hacker` | `#0d1117` | `#58a6ff` | `#238636` | Low-level / security / CLI devs |
| `builder` | `#f6f8fa` | `#24292f` | `#0969da` | Pragmatic shippers, full-stack |
| `researcher` | `#ffffff` | `#1b1f23` | `#6f42c1` | ML, academia, papers-with-code |
| `designer` | `#fff5f5` | `#d73a49` | `#f9826c` | UI / UX / front-end craft |
| `open-source-hero` | `#f0f9ff` | `#0366d6` | `#28a745` | Prolific OSS maintainers |

---

## 🧪 Quick Test

After starting the backend:

```bash
# PowerShell
$body = @{ username = "torvalds" } | ConvertTo-Json
Invoke-RestMethod -Uri http://localhost:8080/generate -Method Post -Body $body -ContentType "application/json"
```

```bash
# bash / curl
curl -X POST http://localhost:8080/generate \
     -H "Content-Type: application/json" \
     -d '{"username":"torvalds"}'
```

---

## 🛠 Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `429 / RESOURCE_EXHAUSTED` | Gemini free-tier quota hit. | Wait a minute (automatic backoff); upgrade quota; or rely on fallback analysis. |
| `404 User not found` | Profile is private or misspelled. | Verify the username on github.com. |
| Card returns fallback vibe | Gemini call failed silently. | Check `GOOGLE_API_KEY` is set and valid. |
| GitHub rate-limit errors | Unauthenticated calls capped at 60/hr. | Add `GITHUB_TOKEN` to `backend/.env`. |
| Backend can't see `.env` | Wrong working directory. | Run `uvicorn` **from inside `backend/`**, or set `--env-file`. |
| Generated card looks broken | Missing avatar / blocked CSP. | Open `static/cards/<user>.html` directly in a browser. |

---

## 🗺 Roadmap

- [x] Downloadable card as **JPG / PDF** (client-side via `html2canvas` + `jsPDF`)
- [x] **Unique share link** per generation
- [x] **Social share buttons** (WhatsApp, X, Facebook, LinkedIn, Telegram, Reddit, Instagram, Email)
- [ ] Server-rendered **OG-image** endpoint for richer link previews
- [ ] Theme **voting / overrides** in the UI
- [ ] **Caching layer** (Redis) keyed by username + ETag
- [ ] **Auth-gated** private repo stats
- [x] One-click **deploy to Cloud Run** (see below)

---

## ☁️ Deploy to Google Cloud Run

Two services: `gcr-backend` (FastAPI) and `gcr-frontend` (Nginx). Replace `PROJECT_ID` and `REGION` with your own.

```bash
# 0. Auth & project
gcloud auth login
gcloud config set project PROJECT_ID
gcloud services enable run.googleapis.com artifactregistry.googleapis.com cloudbuild.googleapis.com

# 1. Backend — build + deploy
cd backend
gcloud run deploy gcr-backend \
  --source . \
  --region REGION \
  --allow-unauthenticated \
  --port 8080 \
  --memory 512Mi \
  --set-env-vars GOOGLE_API_KEY=YOUR_GEMINI_KEY,GITHUB_TOKEN=YOUR_GH_TOKEN

# Capture the backend URL (e.g. https://gcr-backend-xxx-uc.a.run.app)
BACKEND_URL=$(gcloud run services describe gcr-backend --region REGION --format='value(status.url)')

# 2. Frontend — point it at the backend URL via env var
cd ../frontend
gcloud run deploy gcr-frontend \
  --source . \
  --region REGION \
  --allow-unauthenticated \
  --port 8080 \
  --set-env-vars BACKEND_URL=$BACKEND_URL
```

The frontend container's entrypoint runs `envsubst` to inject `${BACKEND_URL}` into `index.html` and `${PORT}` into `nginx.conf` at start-up, so the same image works in any environment.

> **Heads-up about share links on Cloud Run.** Cloud Run's filesystem is in-memory and ephemeral — files written to `static/cards/` do not persist across instances or restarts. For reliable share links in production, either:
> 1. Run the backend with `--max-instances=1` (simplest, single-instance only), or
> 2. Mount a Cloud Storage bucket (`--add-volume` / GCS FUSE) at `/app/static/cards`, or
> 3. Swap `save_card()` to upload to GCS and serve via a public bucket URL.

---

## 🤝 Contributing

Contributions are welcome! To get started:

1. Fork the repo and create a feature branch: `git checkout -b feat/your-feature`.
2. Follow the existing code style (PEP 8, type-hints where helpful).
3. Use **Conventional Commits** (`feat:`, `fix:`, `docs:`, `build:`, `chore:` …).
4. Open a pull request with a clear description and screenshots if the UI changed.

---

## 📜 License

Distributed under the **MIT License**. See `LICENSE` for details.

---

## 🙏 Acknowledgements

- [Google AI Studio](https://aistudio.google.com/) for Gemini API access
- [Model Context Protocol](https://modelcontextprotocol.io/) and the FastMCP project
- [FastAPI](https://fastapi.tiangolo.com/) for the delightful Python web framework
- [GitHub REST API](https://docs.github.com/en/rest) for profile data

<div align="center">

⭐ *If you find this project useful, give it a star — it really helps!*

</div>
