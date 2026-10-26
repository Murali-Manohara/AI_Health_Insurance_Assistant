import hashlib
import os
import re
import uuid
from pathlib import Path
from fastapi import HTTPException, UploadFile
from backend.app.core.config import settings
from backend.app.core.logging_config import logger

def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent directory traversal and invalid characters."""
    base = os.path.basename(filename)
    clean = re.sub(r'[^a-zA-Z0-9_\.-]', '_', base)
    if not clean.lower().endswith('.pdf'):
        clean += '.pdf'
    return clean

def compute_sha256(file_bytes: bytes) -> str:
    """Compute SHA-256 hash of byte content."""
    hasher = hashlib.sha256()
    hasher.update(file_bytes)
    return hasher.hexdigest()

def validate_pdf_bytes(file_bytes: bytes, original_filename: str) -> None:
    """Validate PDF magic bytes, extension, and file size."""
    # 1. Size check
    if len(file_bytes) == 0:
        logger.error(f"Empty file uploaded: {original_filename}")
        raise HTTPException(status_code=400, detail="Uploaded file is empty (0 bytes).")
    
    if len(file_bytes) > settings.MAX_UPLOAD_SIZE_BYTES:
        logger.error(f"File exceeds max size {settings.MAX_UPLOAD_SIZE_BYTES}: {len(file_bytes)} bytes")
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds maximum allowed size of {settings.MAX_UPLOAD_SIZE_BYTES // (1024*1024)} MB."
        )
    
    # 2. Magic bytes check (%PDF-)
    if not file_bytes.startswith(b"%PDF-"):
        logger.error(f"File {original_filename} failed PDF magic byte validation.")
        raise HTTPException(
            status_code=400,
            detail="Invalid file format. The file does not have a valid PDF header signature."
        )

    # 3. Active content and embedded script scanning (malware & malicious macro mitigation)
    dangerous_pdf_tokens = [
        b"/JavaScript", b"/JS", b"/Launch", b"/EmbeddedFiles", b"/SubmitForm", b"/ImportData"
    ]
    for token in dangerous_pdf_tokens:
        if token in file_bytes:
            logger.warning(f"File {original_filename} contains dangerous PDF active token: {token.decode('ascii', errors='ignore')}")
            raise HTTPException(
                status_code=400,
                detail=f"Security rejection: Uploaded PDF contains active scripting or executable actions ({token.decode('ascii', errors='ignore')})."
            )

def scan_text_for_document_poisoning(text: str) -> None:
    """
    Scans extracted document text for prompt-poisoning or adversarial instructions
    intended to hijack system instructions upon retrieval.
    """
    if not text:
        return
    
    poison_patterns = [
        re.compile(r"ignore\s+(all\s+)?(previous|prior|above)\s+(instructions|directives)", re.IGNORECASE),
        re.compile(r"system\s+prompt\s*:\s*you\s+must", re.IGNORECASE),
        re.compile(r"disregard\s+(the\s+)?(guardrails|instructions)", re.IGNORECASE),
        re.compile(r"<\s*/?\s*(system|instruction|developer)\s*>", re.IGNORECASE),
        re.compile(r"secret\s+override\s+code", re.IGNORECASE),
    ]
    
    for pat in poison_patterns:
        if pat.search(text):
            logger.error(f"Document poisoning detected matching pattern: {pat.pattern}")
            raise ValueError(f"Document contains suspicious instructions attempting prompt poisoning ({pat.pattern}). Ingestion halted.")

def save_to_staging(file_bytes: bytes, original_filename: str) -> Path:
    """Safely write uploaded PDF to isolated staging directory with randomized name."""
    clean_name = sanitize_filename(original_filename)
    safe_name = f"{uuid.uuid4().hex[:8]}_{clean_name}"
    target_path = settings.STAGING_DIR / safe_name
    
    with open(target_path, "wb") as f:
        f.write(file_bytes)
        
    logger.info(f"Saved upload to staging: {target_path}")
    return target_path
