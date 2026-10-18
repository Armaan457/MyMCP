import io
import re
from datetime import datetime, timezone
from typing import Any
import httpx
import pypdf
from src.config import get_settings
from src.mongo import get_async_db

SECTION_HEADERS = [
    ("experience", re.compile(r"^(work\s+experience|professional\s+experience|experience|employment)", re.IGNORECASE)),
    ("projects", re.compile(r"^(projects|key\s+projects|personal\s+projects|selected\s+projects)", re.IGNORECASE)),
    ("skills", re.compile(r"^(technical\s+skills|skills\s*(&|and)?\s*abilities|skills|competencies)", re.IGNORECASE)),
    ("education", re.compile(r"^(education|academic\s+background|academics)", re.IGNORECASE)),
    ("achievements", re.compile(r"^(achievements|honors|awards|certifications)", re.IGNORECASE)),
]

def extract_drive_file_id(url: str) -> str | None:
    patterns = [
        r"/file/d/([a-zA-Z0-9_-]+)",
        r"[?&]id=([a-zA-Z0-9_-]+)",
        r"/d/([a-zA-Z0-9_-]+)",
    ]
    for p in patterns:
        m = re.search(p, url)
        if m:
            return m.group(1)
    return None


async def download_drive_pdf(url: str) -> bytes:
    file_id = extract_drive_file_id(url)
    download_url = f"https://drive.google.com/uc?export=download&id={file_id}" if file_id else url
    async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
        response = await client.get(download_url)
        response.raise_for_status()
        return response.content


def extract_text_from_bytes(pdf_bytes: bytes) -> str:
    reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
    full_text: list[str] = []
    for page in reader.pages:
        text = page.extract_text() or ""
        cleaned = re.sub(r"[ \t]+", " ", text)
        full_text.append(cleaned.strip())
    return "\n\n".join(full_text)


def segment_resume_sections(raw_text: str) -> dict[str, str]:
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    sections: dict[str, list[str]] = {
        "header": [],
        "experience": [],
        "projects": [],
        "skills": [],
        "education": [],
        "achievements": [],
        "other": []
    }
    
    current_section = "header"
    for line in lines:
        matched_section = None
        for sec_name, pattern in SECTION_HEADERS:
            if len(line.split()) <= 4 and pattern.match(line):
                matched_section = sec_name
                break
        
        if matched_section:
            current_section = matched_section
            continue
            
        sections[current_section].append(line)
        
    return {k: "\n".join(v).strip() for k, v in sections.items() if v}


def create_chunks_from_sections(sections: dict[str, str]) -> list[dict[str, Any]]:
    chunks = []
    
    if "projects" in sections and sections["projects"]:
        blocks = [b.strip() for b in re.split(r"\n\s*\n|(?<=\.)\n(?=[A-Z0-9])", sections["projects"]) if b.strip()]
        for idx, block in enumerate(blocks):
            first_line = block.splitlines()[0] if block.splitlines() else f"Project {idx+1}"
            chunks.append({
                "category": "project",
                "title": first_line[:60],
                "content": block,
                "tags": ["project", "portfolio"]
            })
            
    if "experience" in sections and sections["experience"]:
        blocks = [b.strip() for b in re.split(r"\n\s*\n|(?<=\.)\n(?=[A-Z0-9])", sections["experience"]) if b.strip()]
        for idx, block in enumerate(blocks):
            first_line = block.splitlines()[0] if block.splitlines() else f"Experience {idx+1}"
            chunks.append({
                "category": "experience",
                "title": first_line[:60],
                "content": block,
                "tags": ["work", "experience"]
            })
            
    if "skills" in sections and sections["skills"]:
        chunks.append({
            "category": "skills",
            "title": "Technical Skills Matrix",
            "content": sections["skills"],
            "tags": ["skills", "technologies", "languages"]
        })
        
    return chunks


async def ingest_resume(url: str | None = None) -> dict[str, Any]:
    settings = get_settings()
    target_url = url or settings.resume_drive_url
    
    if not target_url:
        return {"status": "skipped", "reason": "No RESUME_DRIVE_URL configured"}
        
    try:
        pdf_bytes = await download_drive_pdf(target_url)
        raw_text = extract_text_from_bytes(pdf_bytes)
    except Exception as e:
        return {"status": "error", "reason": f"Failed to fetch resume from Google Drive: {e}"}
        
    sections = segment_resume_sections(raw_text)
    chunks = create_chunks_from_sections(sections)
    
    md_parts = []
    if "header" in sections:
        md_parts.append(f"# Profile\n\n{sections['header']}")
    for sec in ["skills", "experience", "projects", "education", "achievements"]:
        if sec in sections:
            md_parts.append(f"## {sec.replace('_', ' ').title()}\n\n{sections[sec]}")
    markdown_content = "\n\n---\n\n".join(md_parts) if md_parts else raw_text
    
    now = datetime.now(timezone.utc)
    db = get_async_db()
    
    await db["resume_profile"].update_one(
        {"doc_id": "canonical_resume"},
        {
            "$set": {
                "doc_id": "canonical_resume",
                "source_url": target_url,
                "raw_text": raw_text,
                "markdown": markdown_content,
                "sections": sections,
                "updated_at": now
            }
        },
        upsert=True
    )
    
    if chunks:
        await db["resume_chunks"].delete_many({})
        for c in chunks:
            c["updated_at"] = now
        await db["resume_chunks"].insert_many(chunks)
        
    return {
        "status": "success",
        "sections_count": len(sections),
        "chunks_count": len(chunks),
        "updated_at": now.isoformat()
    }


if __name__ == "__main__":
    import asyncio
    res = asyncio.run(ingest_resume())
    print(res)
