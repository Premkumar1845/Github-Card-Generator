    # GitHub Dev Card Generator

    Generate a personalized, themed HTML "dev card" for any GitHub user. Enter a username and an AI agent fetches their profile, analyzes their vibe, picks a theme, and renders a shareable card.

    Powered by **Google ADK** (Agent Development Kit) + **Gemini 2.5 Flash**, with tools exposed via an **MCP server**, a **FastAPI** backend, and a static **HTML/CSS/JS** frontend served by Nginx.

    ---

    ## Features

    - Enter any public GitHub username and get a styled dev card
    - AI-driven personality analysis (developer vibe, top skills, fun fact)
    - Auto-selected card theme: `hacker`, `builder`, `researcher`, `designer`, or `open-source-hero`
    - Top repos and most-used languages aggregated from the GitHub API
    - Cards saved as self-contained HTML and served via `/static/cards/<username>.html`
    - Built-in rate-limit retries with exponential backoff for Gemini API

    ---

    ## Architecture

    ```
    ┌────────────┐    POST /generate    ┌─────────────────┐    MCP/stdio   ┌──────────────────┐
    │  Frontend  │ ───────────────────▶ │  FastAPI + ADK  │ ─────────────▶ │   MCP Server     │
    │  (Nginx)   │ ◀─────────────────── │   LlmAgent      │ ◀───────────── │  (FastMCP tools) │
    └────────────┘     HTML card        └─────────────────┘                └──────────────────┘
                                                │                                   │
                                                ▼                                   ▼
                                        Gemini 2.5 Flash                 GitHub REST API
    ```

    The agent (`github_card_agent`) is instructed to call four MCP tools in order:

    1. `scrape_github(username)` — fetch profile, repos, language stats
    2. `analyze_profile(github_data)` — Gemini-powered vibe/theme classification
    3. `generate_card_html(username, github_data, analysis)` — build the styled card
    4. `save_card(username, html)` — persist to `static/cards/<username>.html`

    ---

    ## Project Structure

    ```
    github-card-generator/
    ├── docker-compose.yml
    ├── backend/
    │   ├── agent.py            # ADK LlmAgent + MCP toolset wiring
    │   ├── main.py             # FastAPI app, /generate endpoint
    │   ├── mcp_server.py       # MCP tools (scrape, analyze, render, save)
    │   ├── requirements.txt
    │   ├── Dockerfile
    │   └── static/cards/       # Generated card HTML files
    └── frontend/
        ├── index.html          # Single-page UI
        └── Dockerfile
    ```

    ---

    ## Prerequisites

    - Docker + Docker Compose **OR** Python 3.12+
    - A **Google API key** with Gemini access ([aistudio.google.com](https://aistudio.google.com/))
    - *(Optional)* A **GitHub personal access token** to raise API rate limits

    ---

    ## Setup

    ### 1. Configure environment variables

    Create `backend/.env`:

    ```env
    GOOGLE_API_KEY=your_gemini_api_key_here
    GITHUB_TOKEN=your_github_pat_here   # optional but recommended
    ```

    ### 2. Run with Docker Compose (recommended)

    ```bash
    docker-compose up --build
    ```

    - Frontend: http://localhost
    - Backend API: http://localhost:8080

    ### 3. Run locally (without Docker)

    **Backend:**

    ```bash
    cd backend
    pip install -r requirements.txt
    pip install google-adk
    uvicorn main:app --host 0.0.0.0 --port 8080
    ```

    **Frontend:** open `frontend/index.html` in your browser, or serve it with any static server. Make sure it points at `http://localhost:8080`.

    ---

    ## API

    ### `POST /generate`

    Generate a card for a GitHub user.

    **Request:**
    ```json
    { "username": "octocat" }
    ```

    **Response:**
    ```json
    {
    "username": "octocat",
    "card_url": "/static/cards/octocat.html",
    "html": "<div class=\"card\">...</div>",
    "agent_response": "..."
    }
    ```

    ### `GET /card/{username}`

    Returns the URL of a previously generated card.

    ### `GET /health`

    Health check. Returns `{"status": "ok", "agent": "github_card_agent"}`.

    ---

    ## Card Themes

    The agent picks one based on profile analysis:

    | Theme | Background | Accent |
    |---|---|---|
    | `hacker` | Dark `#0d1117` | Green `#238636` |
    | `builder` | Light `#f6f8fa` | Blue `#0969da` |
    | `researcher` | White | Purple `#6f42c1` |
    | `designer` | Pink `#fff5f5` | Coral `#f9826c` |
    | `open-source-hero` | Sky `#f0f9ff` | Green `#28a745` |

    ---

    ## Troubleshooting

    - **429 / RESOURCE_EXHAUSTED** — Gemini free-tier rate limit. The backend retries with exponential backoff; if it persists, wait a minute or upgrade your quota.
    - **`User not found`** — Profile is private or username is misspelled.
    - **Card not saved** — Check backend logs; the agent may have skipped a tool call. Ensure `mcp_server.py` is reachable from `agent.py`.
    - **GitHub rate limits** — Add `GITHUB_TOKEN` to `.env` to bump unauthenticated 60/hr to 5,000/hr.

    ---

    ## Tech Stack

    - **Backend:** FastAPI, Uvicorn, Google ADK, MCP (FastMCP), httpx
    - **AI:** Gemini 2.5 Flash via `google-genai`
    - **Frontend:** Vanilla HTML/CSS/JS, served by Nginx
    - **Infra:** Docker, Docker Compose
