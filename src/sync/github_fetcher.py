from datetime import datetime, timezone
from typing import Any
import httpx
from src.config import get_settings
from src.mongo import get_async_db

GITHUB_API_BASE = "https://api.github.com"

async def fetch_github_profile(username: str, token: str | None = None) -> dict[str, Any]:
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "Portfolio-MCP/1.0"
    }
    if token:
        headers["Authorization"] = f"token {token}"
        
    async with httpx.AsyncClient(headers=headers, timeout=20.0) as client:
        user_res = await client.get(f"{GITHUB_API_BASE}/users/{username}")
        if user_res.status_code == 404:
            raise ValueError(f"GitHub user '{username}' not found.")
        user_res.raise_for_status()
        user_data = user_res.json()
        
        repos_res = await client.get(
            f"{GITHUB_API_BASE}/users/{username}/repos",
            params={"per_page": 100, "sort": "pushed", "type": "owner"}
        )
        repos_res.raise_for_status()
        raw_repos = repos_res.json()
        
        owned_repos = [r for r in raw_repos if not r.get("fork", False)]
        owned_repos.sort(key=lambda x: (x.get("stargazers_count", 0), x.get("updated_at", "")), reverse=True)
        
        language_counts: dict[str, int] = {}
        for r in owned_repos:
            lang = r.get("language")
            if lang:
                language_counts[lang] = language_counts.get(lang, 0) + 1
                
        top_repos_detailed = []
        for repo in owned_repos[:6]:
            repo_name = repo["name"]
            readme_content = ""
            try:
                readme_res = await client.get(
                    f"{GITHUB_API_BASE}/repos/{username}/{repo_name}/readme",
                    headers={"Accept": "application/vnd.github.v3.raw"}
                )
                if readme_res.status_code == 200:
                    readme_content = readme_res.text[:2500]
            except Exception:
                readme_content = ""
                
            top_repos_detailed.append({
                "name": repo_name,
                "full_name": repo["full_name"],
                "description": repo.get("description") or "",
                "stars": repo.get("stargazers_count", 0),
                "forks": repo.get("forks_count", 0),
                "language": repo.get("language"),
                "topics": repo.get("topics", []),
                "html_url": repo["html_url"],
                "pushed_at": repo.get("pushed_at"),
                "readme_excerpt": readme_content
            })
            
        return {
            "username": username,
            "name": user_data.get("name"),
            "bio": user_data.get("bio"),
            "avatar_url": user_data.get("avatar_url"),
            "public_repos_count": user_data.get("public_repos", 0),
            "followers": user_data.get("followers", 0),
            "following": user_data.get("following", 0),
            "top_languages": language_counts,
            "top_repositories": top_repos_detailed,
            "all_repository_names": [r["name"] for r in owned_repos]
        }


async def sync_github_data() -> dict[str, Any]:
    settings = get_settings()
    username = settings.github_username
    
    if not username:
        return {"status": "skipped", "reason": "No GITHUB_USERNAME configured"}
        
    try:
        profile_data = await fetch_github_profile(username, settings.github_token)
        now = datetime.now(timezone.utc)
        profile_data["updated_at"] = now
        
        db = get_async_db()
        await db["github_cache"].update_one(
            {"username": username},
            {"$set": profile_data},
            upsert=True
        )
        return {
            "status": "success",
            "username": username,
            "repos_cached": len(profile_data["top_repositories"]),
            "updated_at": now.isoformat()
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


if __name__ == "__main__":
    import asyncio
    res = asyncio.run(sync_github_data())
    print(res)
