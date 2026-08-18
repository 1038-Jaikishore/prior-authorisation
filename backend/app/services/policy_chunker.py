import re
import html
import hashlib
from bs4 import BeautifulSoup
from typing import List, Dict, Any

# Field selection map configuration for RAG
RAG_FIELD_SELECTION = {
    "NCD": {
        "title": {"embed": True, "reason": "Defines the specific scope and subject matter of the National Coverage Determination."},
        "indications_limitations": {"embed": True, "reason": "Contains core clinical criteria, coverages, indications, and limitations rules for national coverage."},
        "item_service_description": {"embed": True, "reason": "Narrative describing the medical device, diagnostic, or clinical service addressed."},
        "benefit_category": {"embed": True, "reason": "Specifies under which Medicare benefit class the service is covered."},
        "transmittal_number": {"embed": False, "reason": "Administrative revision tracking number; has no clinical or medical policy value."},
        "publication_number": {"embed": False, "reason": "CMS manual publication number; administrative/citation metadata only."}
    },
    "LCD": {
        "title": {"embed": True, "reason": "Primary identifier containing the service name and scope of local coverage."},
        "indication": {"embed": True, "reason": "Contains vital narrative outlining active coverage indications, limitations, and medical necessity definitions."},
        "cms_cov_policy": {"embed": True, "reason": "Detailed references and narrative on federal coverage requirements."},
        "coding_guidelines": {"embed": True, "reason": "Clinical coding instructions and modifiers guidance for billing alignment."},
        "doc_reqs": {"embed": True, "reason": "Narrative details on the medical record documentation required to support claims."},
        "diagnoses_support": {"embed": True, "reason": "Descriptions of diagnosis/clinical findings support rules (if formatted as narrative)."},
        "diagnoses_dont_support": {"embed": True, "reason": "Descriptions of findings or diagnoses that do not support medical necessity."},
        "url": {"embed": False, "reason": "Web reference; static link containing no narrative policy criteria."},
        "contractor_name_type": {"embed": False, "reason": "Name of the MAC contractor; processed deterministically during geography routing."}
    },
    "Article": {
        "title": {"embed": True, "reason": "Identifies the core billing or coding topic covered by the article."},
        "description": {"embed": True, "reason": "Summary describing the clinical scope, coding changes, or billing clarifications."},
        "cms_cov_policy": {"embed": True, "reason": "Narrative detailing related LCDs or statutory references for policy compliance."},
        "status": {"embed": False, "reason": "Document state indicator (e.g. Active); resolved deterministically."}
    }
}

def clean_html(html_content: str) -> str:
    """Decodes HTML entities and strips tags while preserving structure, headings, and list items."""
    if not html_content:
        return ""
        
    # Unescape HTML entities first
    text = html.unescape(html_content)
    
    # Use BeautifulSoup with lxml parser
    soup = BeautifulSoup(text, "lxml")
    
    # Remove script, style, and navigation tags
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
        
    # Process headings to preserve section boundaries
    for heading in soup(["h1", "h2", "h3", "h4", "h5", "h6"]):
        heading.insert_before("\n\n")
        heading.insert_after("\n\n")
        
    # Process paragraph and structural blocks to ensure line breaks
    for p in soup(["p", "div", "tr"]):
        p.insert_before("\n")
        p.insert_after("\n")
        
    # Format list items as bullets
    for li in soup(["li"]):
        li.insert_before("\n - ")
        
    # Get plain text
    raw_text = soup.get_text()
    
    # Clean whitespace and preserve reasonable spacing
    lines = [line.strip() for line in raw_text.splitlines()]
    cleaned_lines = []
    prev_blank = False
    
    for line in lines:
        if line:
            cleaned_lines.append(line)
            prev_blank = False
        elif not prev_blank:
            cleaned_lines.append("")
            prev_blank = True
            
    return "\n".join(cleaned_lines).strip()

def split_text_by_paragraphs(text: str, chunk_size: int = 1000, chunk_overlap: int = 200) -> List[str]:
    """Splits a body of text into paragraph-bounded chunks to preserve context."""
    if not text:
        return []
        
    paragraphs = text.split("\n\n")
    chunks = []
    current_chunk = []
    current_len = 0
    
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        
        para_len = len(para)
        
        # If paragraph fits, add it
        if current_len + para_len <= chunk_size:
            current_chunk.append(para)
            current_len += para_len + 2
        else:
            if current_chunk:
                chunks.append("\n\n".join(current_chunk))
            
            # Handle exceptionally large paragraphs
            if para_len > chunk_size:
                start = 0
                while start < para_len:
                    end = start + chunk_size
                    chunks.append(para[start:end])
                    start += chunk_size - chunk_overlap
                current_chunk = []
                current_len = 0
            else:
                current_chunk = [para]
                current_len = para_len
                
    if current_chunk:
        chunks.append("\n\n".join(current_chunk))
        
    return chunks

def make_stable_chunk_id(doc_type: str, doc_id: str, doc_ver: str, section: str, chunk_order: int) -> str:
    """Generates a stable, reproducible MD5 hash ID for a policy chunk."""
    key_str = f"{doc_type.upper()}:{doc_id}:{doc_ver or '1'}:{section}:{chunk_order}"
    return hashlib.md5(key_str.encode("utf-8")).hexdigest()

def generate_field_selection_report(output_path: str) -> None:
    """Auto-generates the backend/reports/rag_field_selection.md markdown documentation file."""
    md_lines = [
        "# Volume 4 RAG Field Selection Map",
        "",
        "This report outlines which fields from NCDs, LCDs, and Articles are selected for narrative vector embedding in RAG indexing.",
        ""
    ]
    
    for doc_type, fields in RAG_FIELD_SELECTION.items():
        md_lines.extend([
            f"## {doc_type} Fields",
            "",
            "| Field Name | Embed? | Reason |",
            "| --- | --- | --- |"
        ])
        for field, config in fields.items():
            embed_str = "**Yes**" if config["embed"] else "No"
            md_lines.append(f"| `{field}` | {embed_str} | {config['reason']} |")
        md_lines.append("")
        
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))
