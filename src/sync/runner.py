import asyncio
from datetime import datetime, timezone
from typing import Any
from src.mongo import init_indexes
from src.sync.resume_parser import ingest_resume
from src.sync.github_fetcher import sync_github_data
from src.sync.leetcode_fetcher import sync_leetcode_data


async def run_sync() -> dict[str, Any]:
    await init_indexes()
    
    resume_task = ingest_resume()
    github_task = sync_github_data()
    leetcode_task = sync_leetcode_data()
    
    resume_res, github_res, leetcode_res = await asyncio.gather(
        resume_task, github_task, leetcode_task, return_exceptions=True
    )
    
    def format_res(res: Any) -> dict[str, Any]:
        if isinstance(res, Exception):
            return {"status": "error", "error": str(res)}
        return res if isinstance(res, dict) else {"status": "unknown"}

    return {
        "resume": format_res(resume_res),
        "github": format_res(github_res),
        "leetcode": format_res(leetcode_res),
        "synced_at": datetime.now(timezone.utc).isoformat()
    }


if __name__ == "__main__":
    result = asyncio.run(run_sync())
    print(result)
