import os
import json
import httpx
import asyncio
import sys
import warnings
from pathlib import Path
from collections import Counter
from mcp.server.fastmcp import FastMCP
from google import genai
from google.genai import types
from dotenv import load_dotenv

# Suppress warnings that might corrupt stdout
warnings.filterwarnings("ignore")
os.environ["PYTHONWARNINGS"] = "ignore"

# Load environment variables
load_dotenv()

# Configure Gemini
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    print("Error: GOOGLE_API_KEY not found", file=sys.stderr)

client = genai.Client(api_key=api_key)

mcp = FastMCP("GitHub Card Tools")

GITHUB_API_URL = "https://api.github.com"

@mcp.tool()
async def scrape_github(username: str) -> dict:
    """Fetch GitHub statistics and repositories for a user."""
    print(f"Scraping GitHub for: {username}", file=sys.stderr)
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "GitHub-Card-Generator"
    }
    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"token {token}"
    
    async with httpx.AsyncClient(headers=headers, timeout=15.0) as http_client:
        try:
            # User profile
            user_res = await http_client.get(f"{GITHUB_API_URL}/users/{username}")
            if user_res.status_code != 200:
                return {"error": f"User {username} not found (Status: {user_res.status_code})"}
            user_data = user_res.json()
            
            # Repositories
            repos_res = await http_client.get(f"{GITHUB_API_URL}/users/{username}/repos?sort=updated&per_page=100")
            repos_data = repos_res.json() if repos_res.status_code == 200 else []
            
            # Process repos
            top_repos = sorted(repos_data, key=lambda x: x.get("stargazers_count", 0), reverse=True)[:6]
            processed_top_repos = [
                {
                    "name": r["name"],
                    "stars": r["stargazers_count"],
                    "language": r["language"],
                    "description": r["description"]
                }
                for r in top_repos
            ]
            
            # Languages aggregation
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
                "most_used_languages": dict(lang_counts)
            }
        except Exception as e:
            print(f"Error in scrape_github: {str(e)}", file=sys.stderr)
            return {"error": str(e)}

@mcp.tool()
async def analyze_profile(github_data: dict) -> dict:
    """Analyze GitHub profile data using Gemini to determine vibe and theme."""
    print(f"Analyzing profile for: {github_data.get('username')}", file=sys.stderr)
    prompt = f"""
    Analyze this GitHub profile data and return a JSON object.
    Data: {json.dumps(github_data)}
    
    Required JSON structure:
    {{
        "developer_vibe": "one sentence personality description",
        "top_skills": ["skill1", "skill2", "skill3"],
        "fun_fact": "something clever inferred from their repos",
        "card_theme": "one of: 'hacker', 'builder', 'researcher', 'designer', 'open-source-hero'"
    }}
    """
    
    max_retries = 3
    base_delay = 15  # seconds
    
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                )
            )
            return json.loads(response.text)
        except Exception as e:
            error_str = str(e)
            is_rate_limit = "429" in error_str or "RESOURCE_EXHAUSTED" in error_str
            
            if is_rate_limit and attempt < max_retries - 1:
                wait = base_delay * (2 ** attempt)
                print(f"Rate limit hit in analyze_profile (attempt {attempt + 1}/{max_retries}). Retrying in {wait}s...", file=sys.stderr)
                await asyncio.sleep(wait)
            else:
                print(f"Error in analyze_profile: {error_str}", file=sys.stderr)
                return {
                    "developer_vibe": "A dedicated developer exploring the digital realm.",
                    "top_skills": ["Coding", "Problem Solving", "Open Source"],
                    "fun_fact": "They have a passion for building cool things!",
                    "card_theme": "builder"
                }

@mcp.tool()
async def generate_card_html(username: str, github_data: dict, analysis: dict) -> str:
    """Generate a self-contained HTML string for the dev card."""
    print(f"Generating HTML for: {username}", file=sys.stderr)
    theme = analysis.get("card_theme", "builder")
    
    themes = {
        "hacker": {"bg": "#0d1117", "text": "#58a6ff", "accent": "#238636", "border": "#30363d"},
        "builder": {"bg": "#f6f8fa", "text": "#24292f", "accent": "#0969da", "border": "#d0d7de"},
        "researcher": {"bg": "#ffffff", "text": "#1b1f23", "accent": "#6f42c1", "border": "#e1e4e8"},
        "designer": {"bg": "#fff5f5", "text": "#d73a49", "accent": "#f9826c", "border": "#ffeef0"},
        "open-source-hero": {"bg": "#f0f9ff", "text": "#0366d6", "accent": "#28a745", "border": "#c8e1ff"}
    }
    
    t = themes.get(theme, themes["builder"])
    
    skills_html = "".join([f'<span class="badge" style="background: {t["accent"]}; color: white; padding: 2px 8px; border-radius: 10px; font-size: 0.7rem; margin-right: 5px;">{s}</span>' for s in analysis.get("top_skills", [])])
    
    repos_list = github_data.get("top_repos", [])[:3]
    repos_html = "".join([
        f'<div class="repo" style="font-size: 0.8rem; margin-bottom: 5px;"><strong>{r["name"]}</strong> ({r["stars"]} ⭐) - {r["language"]}</div>'
        for r in repos_list
    ])

    html = f"""
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
    return html

@mcp.tool()
async def save_card(username: str, html: str) -> str:
    """Save the generated card HTML to a file."""
    print(f"Saving card for: {username}", file=sys.stderr)
    base_path = Path(__file__).parent.absolute()
    static_dir = base_path / "static" / "cards"
    static_dir.mkdir(parents=True, exist_ok=True)
    
    file_path = static_dir / f"{username}.html"
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(html)
    
    return f"/static/cards/{username}.html"

if __name__ == "__main__":
    mcp.run()
