"""
Deterministic card-generation pipeline.

The original agent-based flow (gemini-2.5-flash deciding to call 4 MCP tools in
order) was unreliable — the model occasionally narrates the steps as text
instead of issuing real function calls, leaving no card saved. Since the
sequence is fixed, we run it directly here: scrape -> analyze (LLM) ->
render -> save. Only `analyze_profile` needs Gemini.
"""
import os
import json
import uuid
import asyncio
import logging
from collections import Counter
from pathlib import Path

import httpx
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

GITHUB_API_URL = "https://api.github.com"
BASE_DIR = Path(__file__).parent.absolute()
CARDS_DIR = BASE_DIR / "static" / "cards"
CARDS_DIR.mkdir(parents=True, exist_ok=True)

_api_key = os.getenv("GOOGLE_API_KEY")
_client = genai.Client(api_key=_api_key) if _api_key else None


async def scrape_github(username: str) -> dict:
    """Fetch GitHub statistics and repositories for a user."""
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "GitHub-Card-Generator",
    }
    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"token {token}"

    async with httpx.AsyncClient(headers=headers, timeout=15.0) as http:
        user_res = await http.get(f"{GITHUB_API_URL}/users/{username}")
        if user_res.status_code != 200:
            return {"error": f"User {username} not found (Status: {user_res.status_code})"}
        user_data = user_res.json()

        repos_res = await http.get(
            f"{GITHUB_API_URL}/users/{username}/repos?sort=updated&per_page=100"
        )
        repos_data = repos_res.json() if repos_res.status_code == 200 else []

    top_repos = sorted(repos_data, key=lambda x: x.get("stargazers_count", 0), reverse=True)[:6]
    processed_top_repos = [
        {
            "name": r["name"],
            "stars": r["stargazers_count"],
            "language": r["language"],
            "description": r["description"],
        }
        for r in top_repos
    ]
    languages = [r["language"] for r in repos_data if r["language"]]
    lang_counts = Counter(languages).most_common(5)

    return {
        "username": username,
        "name": user_data.get("name"),
        "avatar_url": user_data.get("avatar_url"),
        "bio": user_data.get("bio"),
        "location": user_data.get("location"),
        "public_repos": user_data.get("public_repos"),
        "followers": user_data.get("followers"),
        "top_repos": processed_top_repos,
        "most_used_languages": dict(lang_counts),
    }


_FALLBACK_ANALYSIS = {
    "developer_vibe": "A dedicated developer exploring the digital realm.",
    "top_skills": ["Coding", "Problem Solving", "Open Source"],
    "fun_fact": "They have a passion for building cool things!",
    "card_theme": "builder",
}


async def analyze_profile(github_data: dict) -> dict:
    """Use Gemini to classify vibe / theme. Falls back gracefully."""
    if _client is None:
        logger.warning("GOOGLE_API_KEY not set; using fallback analysis")
        return _FALLBACK_ANALYSIS

    prompt = (
        "Analyze this GitHub profile data and return ONLY a JSON object.\n"
        f"Data: {json.dumps(github_data)}\n\n"
        "Required JSON structure:\n"
        "{\n"
        '  "developer_vibe": "one sentence personality description",\n'
        '  "top_skills": ["skill1", "skill2", "skill3"],\n'
        '  "fun_fact": "something clever inferred from their repos",\n'
        '  "card_theme": "one of: hacker, builder, researcher, designer, open-source-hero"\n'
        "}"
    )

    max_retries = 3
    base_delay = 10
    for attempt in range(max_retries):
        try:
            # genai SDK is sync; run off the event loop
            response = await asyncio.to_thread(
                _client.models.generate_content,
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.3,
                    thinking_config=types.ThinkingConfig(thinking_budget=0),
                ),
            )
            return json.loads(response.text)
        except Exception as e:
            msg = str(e)
            is_rate = "429" in msg or "RESOURCE_EXHAUSTED" in msg
            if is_rate and attempt < max_retries - 1:
                wait = base_delay * (2 ** attempt)
                logger.warning(f"analyze_profile rate-limited, retry in {wait}s")
                await asyncio.sleep(wait)
            else:
                logger.exception("analyze_profile failed; using fallback")
                return _FALLBACK_ANALYSIS
    return _FALLBACK_ANALYSIS


def generate_card_html(username: str, github_data: dict, analysis: dict) -> str:
    """Build a self-contained HTML card."""
    themes = {
        "hacker":            {"bg": "#0d1117", "text": "#58a6ff", "accent": "#238636", "border": "#30363d"},
        "builder":           {"bg": "#f6f8fa", "text": "#24292f", "accent": "#0969da", "border": "#d0d7de"},
        "researcher":        {"bg": "#ffffff", "text": "#1b1f23", "accent": "#6f42c1", "border": "#e1e4e8"},
        "designer":          {"bg": "#fff5f5", "text": "#d73a49", "accent": "#f9826c", "border": "#ffeef0"},
        "open-source-hero":  {"bg": "#f0f9ff", "text": "#0366d6", "accent": "#28a745", "border": "#c8e1ff"},
    }
    t = themes.get(analysis.get("card_theme", "builder"), themes["builder"])

    skills_html = "".join(
        f'<span class="badge" style="background: {t["accent"]}; color: white; '
        f'padding: 2px 8px; border-radius: 10px; font-size: 0.7rem; margin-right: 5px;">{s}</span>'
        for s in analysis.get("top_skills", [])
    )
    repos_list = github_data.get("top_repos", [])[:3]
    repos_html = "".join(
        f'<div class="repo" style="font-size: 0.8rem; margin-bottom: 5px;">'
        f'<strong>{r["name"]}</strong> ({r["stars"]} ⭐) - {r["language"]}</div>'
        for r in repos_list
    )

    return f"""
    <div class="card" style="background: {t['bg']}; color: {t['text']}; border: 1px solid {t['border']}; font-family: -apple-system, system-ui, sans-serif; padding: 20px; border-radius: 12px; width: 100%; max-width: 400px; box-sizing: border-box; box-shadow: 0 4px 12px rgba(0,0,0,0.15); overflow-wrap: break-word; word-wrap: break-word;">
        <div style="display: flex; align-items: center; margin-bottom: 15px; gap: 12px;">
            <img src="{github_data.get('avatar_url')}" style="width: 60px; height: 60px; border-radius: 50%; border: 2px solid {t['accent']}; flex-shrink: 0;">
            <div style="min-width: 0; flex: 1;">
                <h2 style="margin: 0; font-size: 1.4rem; overflow-wrap: break-word;">{github_data.get('name') or username}</h2>
                <p style="margin: 0; font-size: 0.9rem; opacity: 0.8; overflow-wrap: break-word;">@{username}</p>
            </div>
        </div>
        <p style="font-style: italic; margin: 12px 0; border-left: 3px solid {t['accent']}; padding-left: 10px; font-size: 0.95rem;">"{analysis.get('developer_vibe')}"</p>
        <div style="margin: 15px 0; display: flex; flex-wrap: wrap; gap: 4px;">{skills_html}</div>
        <div style="display: flex; flex-wrap: wrap; gap: 12px 20px; margin-bottom: 15px; font-size: 0.85rem; border-top: 1px solid {t['border']}; border-bottom: 1px solid {t['border']}; padding: 8px 0;">
            <span><strong>{github_data.get('public_repos')}</strong> Repos</span>
            <span><strong>{github_data.get('followers')}</strong> Followers</span>
        </div>
        <div style="background: rgba(0,0,0,0.03); padding: 12px; border-radius: 8px;">
            <h4 style="margin-top: 0; margin-bottom: 8px; font-size: 0.9rem; text-transform: uppercase; letter-spacing: 0.05em; opacity: 0.7;">Top Projects</h4>
            {repos_html}
        </div>
        <p style="font-size: 0.75rem; margin-top: 15px; text-align: right; opacity: 0.6; font-weight: 600;">✨ {analysis.get('fun_fact')}</p>
    </div>
    """


def _wrap_full_page(username: str, card_html: str) -> str:
    """Wrap the card fragment in a complete, shareable HTML page with OG tags."""
    title = f"{username}'s GitHub Dev Card"
    description = f"AI-generated developer card for @{username}. Built with the GitHub Dev Card Generator."
    return f"""<!DOCTYPE html>
<html lang=\"en\">
<head>
    <meta charset=\"UTF-8\">
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">
    <title>{title}</title>
    <meta name=\"description\" content=\"{description}\">
    <meta property=\"og:title\" content=\"{title}\">
    <meta property=\"og:description\" content=\"{description}\">
    <meta property=\"og:type\" content=\"website\">
    <meta name=\"twitter:card\" content=\"summary_large_image\">
    <meta name=\"twitter:title\" content=\"{title}\">
    <meta name=\"twitter:description\" content=\"{description}\">
    <style>
        body {{
            margin: 0;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            background: linear-gradient(135deg, #0d1117 0%, #161b22 100%);
            padding: 24px;
            font-family: -apple-system, system-ui, sans-serif;
        }}
        .share-footer {{
            position: fixed;
            bottom: 12px;
            left: 50%;
            transform: translateX(-50%);
            font-size: 0.75rem;
            color: #8b949e;
        }}
        .share-footer a {{ color: #58a6ff; text-decoration: none; }}
    </style>
</head>
<body>
    {card_html}
    <div class=\"share-footer\">Generated by <a href=\"https://github.com/Premkumar1845/Github-Card-Generator\" target=\"_blank\" rel=\"noopener\">GitHub Dev Card Generator</a></div>
</body>
</html>
"""


def save_card(username: str, html: str, share_id: str) -> tuple[str, str]:
    """Persist the card HTML.

    Writes two files:
      - <username>.html              (latest copy / fragment, backward compat)
      - <username>-<share_id>.html   (full-page shareable snapshot)

    Returns (legacy_card_url, share_url_path).
    """
    # Legacy fragment (kept for backward compatibility with old links)
    fragment_path = CARDS_DIR / f"{username}.html"
    fragment_path.write_text(html, encoding="utf-8")

    # Full-page shareable snapshot, unique per generation
    full_page = _wrap_full_page(username, html)
    share_path = CARDS_DIR / f"{username}-{share_id}.html"
    share_path.write_text(full_page, encoding="utf-8")

    return (
        f"/static/cards/{username}.html",
        f"/static/cards/{username}-{share_id}.html",
    )


async def build_card(username: str) -> dict:
    """Run the full pipeline. Returns dict with html + card_url + share_url."""
    github_data = await scrape_github(username)
    if "error" in github_data:
        raise ValueError(github_data["error"])

    analysis = await analyze_profile(github_data)
    html = generate_card_html(username, github_data, analysis)

    # Unique short id per generation so every share link is fresh
    share_id = uuid.uuid4().hex[:10]
    card_url, share_url = save_card(username, html, share_id)

    return {
        "username": username,
        "card_url": card_url,
        "share_url": share_url,
        "share_id": share_id,
        "html": html,
        "analysis": analysis,
    }
