import os
import re
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import Document, Permission, User
from app.permissions import can
from app.permissions import VALID_GRANT_LEVELS, can
from app.schemas import DocumentOut, ShareOut, ShareRequest

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


def get_document_or_404(db: Session, doc_id: int) -> Document:
    document = db.get(Document, doc_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    return document


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


@router.get("", response_model=list[DocumentOut])
def list_documents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    all_docs = db.scalars(select(Document).order_by(Document.id)).all()
    return [doc for doc in all_docs if can(db, current_user, doc, "read")]


@router.get("/{doc_id}", response_model=DocumentOut)
def get_document(
    doc_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    document = get_document_or_404(db, doc_id)
    if not can(db, current_user, document, "read"):
        raise HTTPException(status_code=403, detail="Not allowed")
    return document


@router.get("/{doc_id}/download")
def download_document(
    doc_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    document = get_document_or_404(db, doc_id)
    if not can(db, current_user, document, "read"):
        raise HTTPException(status_code=403, detail="Not allowed")

    file_path = (UPLOAD_DIR / document.stored_path).resolve()
    upload_root = UPLOAD_DIR.resolve()
    if not str(file_path).startswith(str(upload_root)) or not file_path.is_file():
        raise HTTPException(status_code=404, detail="Stored file is missing")

    return FileResponse(
        path=file_path,
        media_type="application/octet-stream",
        filename=document.filename,
        content_disposition_type="attachment",
    )


@router.delete("/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    doc_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    document = get_document_or_404(db, doc_id)
    if not can(db, current_user, document, "delete"):
        raise HTTPException(status_code=403, detail="Not allowed")

    file_path = (UPLOAD_DIR / document.stored_path).resolve()
    upload_root = UPLOAD_DIR.resolve()
    if not str(file_path).startswith(str(upload_root)):
        raise HTTPException(status_code=400, detail="Invalid stored path")

    db.execute(delete(Permission).where(Permission.document_id == document.id))
    db.delete(document)
    db.commit()

    if file_path.is_file():
        file_path.unlink()

    return Response(status_code=status.HTTP_204_NO_CONTENT)

@router.post("/{doc_id}/share", response_model=ShareOut, status_code=status.HTTP_200_OK)
def share_document(
    doc_id: int,
    payload: ShareRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    document = get_document_or_404(db, doc_id)
    if not can(db, current_user, document, "share"):
        raise HTTPException(status_code=403, detail="Not allowed to share this document")

    if payload.level not in VALID_GRANT_LEVELS:
        raise HTTPException(status_code=400, detail="Invalid permission level. Use 'read' or 'edit'")

    target_user = db.scalar(select(User).where(User.email == payload.user_email))
    if not target_user:
        raise HTTPException(status_code=404, detail="Target user not found")

    if target_user.id == document.owner_id:
        raise HTTPException(status_code=400, detail="Cannot share a document with its owner")

    # Check if a permission row already exists (upsert behavior)
    grant = db.scalar(
        select(Permission).where(
            Permission.document_id == document.id,
            Permission.user_id == target_user.id,
        )
    )

    if grant:
        grant.level = payload.level
    else:
        grant = Permission(
            document_id=document.id,
            user_id=target_user.id,
            level=payload.level,
        )
        db.add(grant)

    db.commit()
    db.refresh(grant)

    return ShareOut(
        id=grant.id,
        document_id=grant.document_id,
        user_id=grant.user_id,
        user_email=target_user.email,
        level=grant.level,
    )


@router.get("/{doc_id}/shares", response_model=list[ShareOut])
def list_document_shares(
    doc_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    document = get_document_or_404(db, doc_id)
    # Only owner can view the list of people with access
    if not can(db, current_user, document, "share"):
        raise HTTPException(status_code=403, detail="Not allowed")

    shares = db.scalars(
        select(Permission).where(Permission.document_id == document.id)
    ).all()

    result = []
    for s in shares:
        target_user = db.get(User, s.user_id)
        email = target_user.email if target_user else "unknown"
        result.append(
            ShareOut(
                id=s.id,
                document_id=s.document_id,
                user_id=s.user_id,
                user_email=email,
                level=s.level,
            )
        )
    return result


@router.delete("/{doc_id}/share/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_document_share(
    doc_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    document = get_document_or_404(db, doc_id)
    if not can(db, current_user, document, "share"):
        raise HTTPException(status_code=403, detail="Not allowed to revoke shares")

    grant = db.scalar(
        select(Permission).where(
            Permission.document_id == document.id,
            Permission.user_id == user_id,
        )
    )
    if not grant:
        raise HTTPException(status_code=404, detail="Share grant not found")

    db.delete(grant)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)