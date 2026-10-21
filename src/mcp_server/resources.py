import json
from src.config import get_settings
from src.mongo import get_async_db
from mcp.server.mcpserver import MCPServer


def register_resources(mcp: MCPServer):
    @mcp.resource("portfolio://resume")
    async def get_resume_resource() -> str:
        db = get_async_db()
        doc = await db["resume_profile"].find_one({"doc_id": "canonical_resume"})
        if not doc or not doc.get("markdown"):
            return "# Resume Not Synced\nRun the sync runner to populate your resume."
        return doc["markdown"]

    @mcp.resource("portfolio://skills-matrix")
    async def get_skills_matrix() -> str:
        db = get_async_db()
        settings = get_settings()

        resume_doc = await db["resume_profile"].find_one({"doc_id": "canonical_resume"})
        github_doc = await db["github_cache"].find_one({"username": settings.github_username})
        leetcode_doc = await db["leetcode_cache"].find_one({"username": settings.leetcode_username})

        resume_skills = ""
        if resume_doc and "sections" in resume_doc:
            resume_skills = resume_doc["sections"].get("skills", "")

        gh_languages = github_doc.get("top_languages", {}) if github_doc else {}
        top_dsa_topics = dict(list((leetcode_doc.get("topic_skills", {}) if leetcode_doc else {}).items())[:12])

        matrix = {
            "declared_skills": resume_skills,
            "github_languages": gh_languages,
            "leetcode_topics": top_dsa_topics
        }
        return json.dumps(matrix, indent=2)

    @mcp.resource("portfolio://github/overview")
    async def get_github_overview() -> str:
        db = get_async_db()
        settings = get_settings()
        github_doc = await db["github_cache"].find_one({"username": settings.github_username})

        if not github_doc:
            return json.dumps({"status": "not_synced", "message": "GitHub data not synced yet."})

        github_doc.pop("_id", None)
        if "updated_at" in github_doc:
            github_doc["updated_at"] = str(github_doc["updated_at"])
        return json.dumps(github_doc, indent=2)

    @mcp.resource("portfolio://leetcode/overview")
    async def get_leetcode_overview() -> str:
        db = get_async_db()
        settings = get_settings()
        leetcode_doc = await db["leetcode_cache"].find_one({"username": settings.leetcode_username})

        if not leetcode_doc:
            return json.dumps({"status": "not_synced", "message": "LeetCode data not synced yet."})

        leetcode_doc.pop("_id", None)
        if "updated_at" in leetcode_doc:
            leetcode_doc["updated_at"] = str(leetcode_doc["updated_at"])
        return json.dumps(leetcode_doc, indent=2)
