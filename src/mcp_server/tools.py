import re
from typing import Any
from mcp.server.mcpserver import MCPServer
from src.config import get_settings
from src.mongo import get_async_db


def register_tools(mcp: MCPServer):
    @mcp.tool()
    async def search_experience(query: str, category: str = "all") -> str:
        db = get_async_db()
        filter_query: dict[str, Any] = {}
        if category != "all":
            filter_query["category"] = category

        text_filter = {**filter_query, "$text": {"$search": query}}
        cursor = db["resume_chunks"].find(text_filter).limit(5)
        results = await cursor.to_list(length=5)

        if not results:
            regex_pattern = re.compile(re.escape(query), re.IGNORECASE)
            regex_filter = {
                **filter_query,
                "$or": [
                    {"content": regex_pattern},
                    {"title": regex_pattern},
                    {"tags": regex_pattern}
                ]
            }
            cursor = db["resume_chunks"].find(regex_filter).limit(5)
            results = await cursor.to_list(length=5)

        if not results:
            return f"No resume entries found matching '{query}'. Check the full resume via portfolio://resume."

        formatted = []
        for r in results:
            formatted.append(f"### [{r.get('category', '').upper()}] {r.get('title')}\n{r.get('content')}")
        return "\n\n---\n\n".join(formatted)

    @mcp.tool()
    async def get_project_deep_dive(repo_name: str) -> str:
        db = get_async_db()
        settings = get_settings()
        doc = await db["github_cache"].find_one({"username": settings.github_username})
        if not doc:
            return "GitHub data not synced yet."

        repos = doc.get("top_repositories", [])
        matched = next((r for r in repos if r["name"].lower() == repo_name.lower()), None)

        if not matched:
            available = [r["name"] for r in repos]
            return f"Project '{repo_name}' not found. Available projects: {', '.join(available)}"

        readme = matched.get("readme_excerpt") or "No README cached."
        return (
            f"# {matched['name']}\n"
            f"**URL**: {matched['html_url']}\n"
            f"**Language**: {matched.get('language') or 'N/A'} | **Stars**: {matched.get('stars', 0)} | **Forks**: {matched.get('forks', 0)}\n"
            f"**Topics**: {', '.join(matched.get('topics', [])) or 'None'}\n"
            f"**Description**: {matched['description']}\n\n"
            f"## README\n{readme}"
        )

    @mcp.tool()
    async def get_dsa_proficiency(topic: str = "") -> str:
        db = get_async_db()
        settings = get_settings()
        doc = await db["leetcode_cache"].find_one({"username": settings.leetcode_username})

        if not doc:
            return "LeetCode stats not synced yet."

        summary = (
            f"### LeetCode Profile ({doc.get('username')})\n"
            f"- Total Solved: {doc.get('total_solved', 0)} (Easy: {doc.get('easy_solved', 0)}, Medium: {doc.get('medium_solved', 0)}, Hard: {doc.get('hard_solved', 0)})\n"
            f"- Contest Rating: {doc.get('contest_rating', 'Unrated')} (Rank: {doc.get('contest_rank', 'N/A')})\n"
            f"- Badges: {', '.join(doc.get('badges', [])) or 'None'}\n"
        )

        topic_skills = doc.get("topic_skills", {})
        if topic:
            matched = {k: v for k, v in topic_skills.items() if topic.lower() in k.lower()}
            if matched:
                details = "\n".join([f"- {k}: {v} problems solved" for k, v in matched.items()])
                return f"{summary}\n#### Topic Mastery: '{topic}'\n{details}"
            return f"{summary}\nNo problems tracked under topic '{topic}'."

        top_topics = sorted(topic_skills.items(), key=lambda x: x[1], reverse=True)[:10]
        details = "\n".join([f"- {k}: {v} solved" for k, v in top_topics])
        return f"{summary}\n#### Top Mastered Topics:\n{details}"

    @mcp.tool()
    async def evaluate_job_fit(job_description: str) -> str:
        db = get_async_db()
        settings = get_settings()

        resume_doc = await db["resume_profile"].find_one({"doc_id": "canonical_resume"})
        github_doc = await db["github_cache"].find_one({"username": settings.github_username})
        leetcode_doc = await db["leetcode_cache"].find_one({"username": settings.leetcode_username})

        resume_md = resume_doc.get("markdown", "") if resume_doc else "Resume not synced."
        top_repos = github_doc.get("top_repositories", []) if github_doc else []
        repos_summary = "\n".join([
            f"- {r['name']} ({r.get('language')}): {r['description']}"
            for r in top_repos[:6]
        ])
        leetcode_solved = leetcode_doc.get("total_solved", 0) if leetcode_doc else 0
        leetcode_rating = leetcode_doc.get("contest_rating") if leetcode_doc else None

        return (
            "### Candidate Evaluation Dossier\n\n"
            f"**Problem Solving**: {leetcode_solved} LeetCode problems solved (Rating: {leetcode_rating or 'Unrated'})\n\n"
            f"**Key Projects**:\n{repos_summary}\n\n"
            f"**Resume Overview**:\n{resume_md}\n\n"
            "---\n"
            "Evaluate candidate fit against the following Job Description by providing:\n"
            "1. Match Score (0-100%)\n"
            "2. Direct Proof Points from projects and internships\n"
            "3. Algorithmic / DSA Readiness\n"
            "4. Growth areas or adjacent technologies\n\n"
            f"**Target Job Description**:\n{job_description}"
        )
