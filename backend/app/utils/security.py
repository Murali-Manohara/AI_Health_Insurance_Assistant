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

def save_to_staging(file_bytes: bytes, original_filename: str) -> Path:
    """Safely write uploaded PDF to isolated staging directory with randomized name."""
    clean_name = sanitize_filename(original_filename)
    safe_name = f"{uuid.uuid4().hex[:8]}_{clean_name}"
    target_path = settings.STAGING_DIR / safe_name
    
    with open(target_path, "wb") as f:
        f.write(file_bytes)
        
    logger.info(f"Saved upload to staging: {target_path}")
    return target_path
