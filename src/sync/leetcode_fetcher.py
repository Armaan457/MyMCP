from datetime import datetime, timezone
from typing import Any
import httpx
from src.config import get_settings
from src.mongo import get_async_db

LEETCODE_GRAPHQL_URL = "https://leetcode.com/graphql"

LEETCODE_QUERY = """
query getUserProfile($username: String!) {
  matchedUser(username: $username) {
    username
    profile {
      ranking
      userAvatar
      reputation
    }
    submitStats {
      acSubmissionNum {
        difficulty
        count
        submissions
      }
    }
    badges {
      id
      displayName
      icon
    }
    tagProblemCounts {
      advanced {
        tagName
        problemsSolved
      }
      intermediate {
        tagName
        problemsSolved
      }
      fundamental {
        tagName
        problemsSolved
      }
    }
  }
  userContestRanking(username: $username) {
    attendedContestsCount
    rating
    globalRanking
    totalParticipants
    topPercentage
    badge {
      name
    }
  }
}
"""


async def fetch_leetcode_profile(username: str) -> dict[str, Any]:
    headers = {
        "Content-Type": "application/json",
        "Referer": f"https://leetcode.com/{username}/",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    }
    payload = {
        "query": LEETCODE_QUERY,
        "variables": {"username": username}
    }
    
    async with httpx.AsyncClient(headers=headers, timeout=20.0) as client:
        response = await client.post(LEETCODE_GRAPHQL_URL, json=payload)
        response.raise_for_status()
        data = response.json()
        
        errors = data.get("errors")
        if errors:
            raise ValueError(f"LeetCode GraphQL returned error: {errors}")
            
        data_body = data.get("data", {})
        matched_user = data_body.get("matchedUser")
        if not matched_user:
            raise ValueError(f"LeetCode user '{username}' not found.")
            
        submit_stats = matched_user.get("submitStats", {}).get("acSubmissionNum", [])
        diff_map = {item["difficulty"].lower(): item["count"] for item in submit_stats}
        
        tags_data = matched_user.get("tagProblemCounts", {})
        topic_skills = {}
        for level in ["fundamental", "intermediate", "advanced"]:
            for item in tags_data.get(level, []):
                topic_skills[item["tagName"]] = item["problemsSolved"]
                
        contest = data_body.get("userContestRanking") or {}
        
        return {
            "username": username,
            "profile": matched_user.get("profile", {}),
            "total_solved": diff_map.get("all", 0),
            "easy_solved": diff_map.get("easy", 0),
            "medium_solved": diff_map.get("medium", 0),
            "hard_solved": diff_map.get("hard", 0),
            "contest_rating": round(contest.get("rating", 0), 1) if contest.get("rating") else None,
            "contest_rank": contest.get("globalRanking"),
            "contests_attended": contest.get("attendedContestsCount", 0),
            "top_percentage": contest.get("topPercentage"),
            "topic_skills": topic_skills,
            "badges": [b.get("displayName") for b in matched_user.get("badges", [])]
        }


async def sync_leetcode_data() -> dict[str, Any]:
    settings = get_settings()
    username = settings.leetcode_username
    
    if not username:
        return {"status": "skipped", "reason": "No LEETCODE_USERNAME configured"}
        
    try:
        profile_data = await fetch_leetcode_profile(username)
        now = datetime.now(timezone.utc)
        profile_data["updated_at"] = now
        
        db = get_async_db()
        await db["leetcode_cache"].update_one(
            {"username": username},
            {"$set": profile_data},
            upsert=True
        )
        return {
            "status": "success",
            "username": username,
            "total_solved": profile_data["total_solved"],
            "updated_at": now.isoformat()
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}

