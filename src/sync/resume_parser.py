import io
import re
from datetime import datetime, timezone
from typing import Any
import httpx
import pypdf
from src.config import get_settings
from src.mongo import get_async_db

SECTION_HEADERS = [
    ("education", re.compile(r"^education", re.IGNORECASE)),
    ("experience", re.compile(r"^(work\s+experience|professional\s+experience|experience)", re.IGNORECASE)),
    ("projects", re.compile(r"^(projects|key\s+projects|personal\s+projects)", re.IGNORECASE)),
    ("skills", re.compile(r"^(technical\s+skills|skills)", re.IGNORECASE)),
    ("achievements", re.compile(r"^(achievements|honors|awards)", re.IGNORECASE)),
]

DATE_PATTERN = re.compile(
    r"((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4}|(?:19|20)\d{2}\s*[–-]\s*(?:Present|(?:19|20)\d{2}|[A-Za-z]+))",
    re.IGNORECASE
)


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
        "education": [],
        "experience": [],
        "projects": [],
        "skills": [],
        "achievements": [],
        "other": []
    }
    
    current_section = "header"
    for line in lines:
        matched_section = None
        for sec_name, pattern in SECTION_HEADERS:
            if len(line.split()) <= 3 and pattern.match(line):
                matched_section = sec_name
                break
        
        if matched_section:
            current_section = matched_section
            continue
            
        sections[current_section].append(line)
        
    return {k: "\n".join(v).strip() for k, v in sections.items() if v}


def is_entry_header(line: str) -> bool:
    if line.startswith(("•", "-", "*")):
        return False
    if "|" in line:
        return True
    if DATE_PATTERN.search(line):
        return True
    return False


def parse_bulleted_entries(text: str) -> list[dict[str, str]]:
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    entries: list[dict[str, str]] = []
    current_headers: list[str] = []
    current_bullets: list[str] = []

    for line in lines:
        if line.startswith(("•", "-", "*")):
            current_bullets.append(line)
        elif is_entry_header(line):
            if current_headers or current_bullets:
                title = " | ".join(current_headers).strip()
                full_content = "\n".join(current_headers + current_bullets)
                entries.append({"title": title, "content": full_content})
            current_headers = [line]
            current_bullets = []
        else:
            if not current_bullets:
                current_headers.append(line)
            else:
                current_bullets[-1] += " " + line

    if current_headers or current_bullets:
        title = " | ".join(current_headers).strip()
        full_content = "\n".join(current_headers + current_bullets)
        entries.append({"title": title, "content": full_content})

    return entries


def extract_keywords_as_tags(text: str, category: str) -> list[str]:
    raw_tokens = re.findall(r"\b[A-Za-z0-9+#.-]{2,}\b", text)
    stopwords = {"and", "for", "the", "with", "from", "using", "built", "into", "over", "each", "live", "github"}
    meaningful = [t.lower() for t in raw_tokens if t.lower() not in stopwords]
    unique_tags: list[str] = [category]
    for tag in meaningful:
        if tag not in unique_tags:
            unique_tags.append(tag)
        if len(unique_tags) >= 12:
            break
    return unique_tags


def create_chunks_from_sections(sections: dict[str, str]) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []

    if "education" in sections and sections["education"]:
        chunks.append({
            "category": "education",
            "title": "Education",
            "content": sections["education"],
            "tags": extract_keywords_as_tags(sections["education"][:120], "education")
        })

    if "experience" in sections and sections["experience"]:
        entries = parse_bulleted_entries(sections["experience"])
        for entry in entries:
            chunks.append({
                "category": "experience",
                "title": entry["title"][:80],
                "content": entry["content"],
                "tags": extract_keywords_as_tags(entry["title"], "experience")
            })

    if "projects" in sections and sections["projects"]:
        entries = parse_bulleted_entries(sections["projects"])
        for entry in entries:
            chunks.append({
                "category": "projects",
                "title": entry["title"][:80],
                "content": entry["content"],
                "tags": extract_keywords_as_tags(entry["title"], "projects")
            })

    if "skills" in sections and sections["skills"]:
        chunks.append({
            "category": "skills",
            "title": "Technical Skills",
            "content": sections["skills"],
            "tags": extract_keywords_as_tags(sections["skills"][:150], "skills")
        })

    if "achievements" in sections and sections["achievements"]:
        chunks.append({
            "category": "achievements",
            "title": "Achievements",
            "content": sections["achievements"],
            "tags": extract_keywords_as_tags(sections["achievements"][:120], "achievements")
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
        header_lines = sections["header"].splitlines()
        candidate_name = header_lines[0] if header_lines else "Profile"
        md_parts.append(f"# {candidate_name}\n\n{sections['header']}")
    for sec in ["education", "experience", "projects", "skills", "achievements"]:
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

