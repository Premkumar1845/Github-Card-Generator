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
    <div class="card" style="background: {t['bg']}; color: {t['text']}; border: 1px solid {t['border']}; font-family: -apple-system, system-ui, sans-serif; padding: 20px; border-radius: 12px; max-width: 400px; box-shadow: 0 4px 12px rgba(0,0,0,0.15);">
        <div style="display: flex; align-items: center; margin-bottom: 15px;">
            <img src="{github_data.get('avatar_url')}" style="width: 60px; height: 60px; border-radius: 50%; border: 2px solid {t['accent']}; margin-right: 15px;">
            <div>
                <h2 style="margin: 0; font-size: 1.4rem;">{github_data.get('name') or username}</h2>
                <p style="margin: 0; font-size: 0.9rem; opacity: 0.8;">@{username}</p>
            </div>
        </div>
        <p style="font-style: italic; margin: 12px 0; border-left: 3px solid {t['accent']}; padding-left: 10px; font-size: 0.95rem;">"{analysis.get('developer_vibe')}"</p>
        <div style="margin: 15px 0; display: flex; flex-wrap: wrap; gap: 4px;">{skills_html}</div>
        <div style="display: flex; gap: 20px; margin-bottom: 15px; font-size: 0.85rem; border-top: 1px solid {t['border']}; border-bottom: 1px solid {t['border']}; padding: 8px 0;">
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


def save_card(username: str, html: str) -> str:
    """Persist the card HTML and return its public URL path."""
    file_path = CARDS_DIR / f"{username}.html"
    file_path.write_text(html, encoding="utf-8")
    return f"/static/cards/{username}.html"


async def build_card(username: str) -> dict:
    """Run the full pipeline. Returns dict with html + card_url, or raises."""
    github_data = await scrape_github(username)
    if "error" in github_data:
        raise ValueError(github_data["error"])

    analysis = await analyze_profile(github_data)
    html = generate_card_html(username, github_data, analysis)
    card_url = save_card(username, html)
    return {
        "username": username,
        "card_url": card_url,
        "html": html,
        "analysis": analysis,
    }
