from mcp.server.mcpserver import MCPServer

def register_prompts(mcp: MCPServer):
    @mcp.prompt()
    def recruiter_pitch(target_role: str, target_company: str = "the target company") -> str:
        return (
            f"You are an executive engineering talent advocate presenting the candidate for a {target_role} role at {target_company}.\n\n"
            "Review `portfolio://resume` and `portfolio://github/overview`.\n"
            "Craft a concise 3-paragraph pitch detailing:\n"
            "1. Core software and AI engineering accomplishments.\n"
            "2. Direct evidence from flagship GitHub projects and LeetCode problem-solving rating.\n"
            "3. Why they will deliver immediate technical impact to the team."
        )

    @mcp.prompt()
    def technical_interview_prep(focus_area: str = "ai_and_systems") -> str:
        return (
            f"You are a Principal Engineering Interviewer conducting a technical deep dive focused on {focus_area}.\n\n"
            "Review `portfolio://resume`, `portfolio://github/overview`, and `portfolio://leetcode/overview`.\n"
            "Generate 5 challenging, scenario-based interview questions tailored to the candidate's actual projects and experience:\n"
            "1. Probe real engineering decisions: model/agent architectures, retrieval evaluation, asynchronous inference, and algorithmic tradeoffs.\n"
            "2. Focus on production realities: handling edge cases, context selection failures, latency bottlenecks (<2s targets), and scalability.\n"
            "3. For each question, outline what signals a good answer versus what distinguishes a top 1% candidate."
        )

    @mcp.prompt()
    def roast_my_profile() -> str:
        return (
            "Review the candidate profile via `portfolio://github/overview` and `portfolio://leetcode/overview`.\n"
            "Deliver a witty, good-natured developer roast addressing:\n"
            "- Their commit activity, late-night pushes, and repo naming\n"
            "- Their ratio of Easy/Medium/Hard LeetCode problems and contest ratings\n"
            "- Their tech stack choices and framework holy wars\n"
            "Conclude with an uplifting, genuine compliment on their hustle."
        )
