import os
import re
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import Document, User
from app.schemas import DocumentOut

router = APIRouter(prefix="/documents", tags=["documents"])

UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "uploads"))
MAX_BYTES = 5 * 1024 * 1024  # 5 MB

# Allowed extension -> the first bytes a real file of that type starts with
SIGNATURES = {
    ".pdf": b"%PDF-",
    ".png": b"\x89PNG\r\n\x1a\n",
    ".jpg": b"\xff\xd8\xff",
    ".jpeg": b"\xff\xd8\xff",
    ".txt": None,  # plain text has no signature, so it is checked separately
}


def clean_filename(name: str) -> str:
    # Keep only the last part (drops any folder path), then replace odd characters
    base = Path((name or "file").replace("\\", "/")).name
    return re.sub(r"[^A-Za-z0-9._-]", "_", base)[:100] or "file"


@router.post("", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
def upload(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    filename = clean_filename(file.filename)
    extension = Path(filename).suffix.lower()

    if extension not in SIGNATURES:
        raise HTTPException(status_code=415, detail="File type not allowed")

    # Read one byte more than the limit, so we can tell if it is too big
    data = file.file.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise HTTPException(status_code=413, detail="File too large (max 5 MB)")
    if len(data) == 0:
        raise HTTPException(status_code=400, detail="Empty file")

    # Check the real content, not just the name
    signature = SIGNATURES[extension]
    if signature is not None:
        if not data.startswith(signature):
            raise HTTPException(status_code=400, detail="File content does not match its type")
    else:
        try:
            data.decode("utf-8")
        except UnicodeDecodeError:
            raise HTTPException(status_code=400, detail="File content does not match its type")
        if b"\x00" in data:
            raise HTTPException(status_code=400, detail="File content does not match its type")

    # The name on disk is random. The user's filename is never used as a path.
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    stored_name = uuid.uuid4().hex + ".bin"
    (UPLOAD_DIR / stored_name).write_bytes(data)

    document = Document(
        owner_id=current_user.id,
        filename=filename,
        stored_path=stored_name,
        size=len(data),
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    return document