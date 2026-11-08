import os
import re
import uuid
import logging
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.audit import log_event
from app.database import get_db
from app.dependencies import get_current_user
from app.models import Document, Permission, User
from app.permissions import VALID_GRANT_LEVELS, authorize, can
from app.schemas import DocumentOut, ShareOut, ShareRequest

router = APIRouter(prefix="/documents", tags=["documents"])
logger = logging.getLogger(__name__)

UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "uploads"))
MAX_BYTES = 5 * 1024 * 1024  # 5 MB


def _remove_local_file(path: Path) -> None:
    try:
        path.unlink(missing_ok=True)
    except OSError:
        logger.exception("Could not remove document file %s", path)


def _restore_local_file(path: Path, data: bytes) -> None:
    """Restore a missing file atomically, without leaving a partial destination."""
    temp_path = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        temp_path.write_bytes(data)
        os.replace(temp_path, path)
    except OSError as exc:
        _remove_local_file(temp_path)
        raise HTTPException(status_code=500, detail="Could not restore document file") from exc

# Allowed extension -> the first bytes a real file of that type starts with
SIGNATURES = {
    ".pdf": b"%PDF-",
    ".png": b"\x89PNG\r\n\x1a\n",
    ".jpg": b"\xff\xd8\xff",
    ".jpeg": b"\xff\xd8\xff",
    ".txt": None,  # plain text has no signature, checked via utf-8 and null-bytes
}


def clean_filename(name: str) -> str:
    base = Path((name or "file").replace("\\", "/")).name
    return re.sub(r"[^A-Za-z0-9._-]", "_", base)[:100] or "file"


def validate_and_read_file(file: UploadFile) -> tuple[str, bytes]:
    filename = clean_filename(file.filename)
    extension = Path(filename).suffix.lower()
    if extension not in SIGNATURES:
        raise HTTPException(status_code=415, detail="File type not allowed")

    data = file.file.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise HTTPException(status_code=413, detail="File too large (max 5 MB)")
    if len(data) == 0:
        raise HTTPException(status_code=400, detail="Empty file")

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

    return filename, data


@router.post("", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
def upload(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    filename, data = validate_and_read_file(file)

    stored_name = uuid.uuid4().hex + ".bin"
    local_path = UPLOAD_DIR / stored_name
    try:
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        local_path.write_bytes(data)
    except OSError as exc:
        _remove_local_file(local_path)
        raise HTTPException(status_code=500, detail="Could not store uploaded file") from exc

    document = Document(
        owner_id=current_user.id,
        filename=filename,
        stored_path=stored_name,
        size=len(data),
        file_data=data,
        content=data,
    )
    db.add(document)
    try:
        # log_event commits the pending document and audit row together.
        db.flush()
        log_event(db, current_user.id, "upload", document.id, "allowed")
    except Exception as exc:
        db.rollback()
        _remove_local_file(local_path)
        logger.exception("Could not commit uploaded document")
        raise HTTPException(status_code=500, detail="Could not save uploaded document") from exc
    db.refresh(document)
    return document


@router.put("/{doc_id}", response_model=DocumentOut)
def update_document(
    doc_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Allows owner or user with 'edit' permission to replace document content."""
    document = authorize(
        db, current_user, db.get(Document, doc_id), "edit", log_allowed=False
    )
    filename, data = validate_and_read_file(file)

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    upload_root = UPLOAD_DIR.resolve()

    old_path = (UPLOAD_DIR / document.stored_path).resolve()
    new_stored_name = uuid.uuid4().hex + ".bin"
    new_path = UPLOAD_DIR / new_stored_name
    new_path.write_bytes(data)

    document.filename = filename
    document.stored_path = new_stored_name
    document.size = len(data)
    document.file_data = data
    document.content = data
    try:
        # Commit the document update and its success event in the same
        # transaction so neither can persist without the other.
        log_event(db, current_user.id, "edit", document.id, "allowed")
    except Exception:
        db.rollback()
        new_path.unlink(missing_ok=True)
        raise
    db.refresh(document)

    if old_path.is_relative_to(upload_root) and old_path.is_file():
        old_path.unlink()

    return document


@router.get("", response_model=list[DocumentOut])
def list_documents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    all_docs = db.scalars(select(Document).order_by(Document.id)).all()
    return [doc for doc in all_docs if can(db, current_user, doc, "read")]


@router.get("/shared-with-me", response_model=list[DocumentOut])
def list_shared_documents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List documents explicitly shared with the current user."""
    return db.scalars(
        select(Document)
        .join(Permission, Permission.document_id == Document.id)
        .where(
            Permission.user_id == current_user.id,
            Permission.level.in_(VALID_GRANT_LEVELS),
            Document.owner_id != current_user.id,
        )
        .order_by(Document.id)
    ).all()


@router.get("/{doc_id}", response_model=DocumentOut)
def get_document(
    doc_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    document = authorize(db, current_user, db.get(Document, doc_id), "read")
    return document


@router.get("/{doc_id}/download")
def download_document(
    doc_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    document = authorize(db, current_user, db.get(Document, doc_id), "read")

    file_path = (UPLOAD_DIR / document.stored_path).resolve()
    upload_root = UPLOAD_DIR.resolve()
    if not file_path.is_relative_to(upload_root):
        raise HTTPException(status_code=404, detail="Stored file is missing")

    if not file_path.is_file():
        stored_data = document.file_data if document.file_data is not None else document.content
        if stored_data is not None:
            _restore_local_file(file_path, stored_data)

    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="Stored file is missing")

    response = FileResponse(path=file_path, filename=document.filename, media_type="application/octet-stream")
    log_event(db, current_user.id, "download", document.id, "allowed")
    return response


@router.delete("/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    doc_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    document = authorize(db, current_user, db.get(Document, doc_id), "delete")

    file_path = (UPLOAD_DIR / document.stored_path).resolve()
    upload_root = UPLOAD_DIR.resolve()
    if not file_path.is_relative_to(upload_root):
        raise HTTPException(status_code=400, detail="Invalid stored path")

    db.execute(delete(Permission).where(Permission.document_id == document.id))
    db.delete(document)
    db.commit()

    _remove_local_file(file_path)

    log_event(db, current_user.id, "delete", document.id, "allowed")

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{doc_id}/share", response_model=ShareOut, status_code=status.HTTP_200_OK)
def share_document(
    doc_id: int,
    payload: ShareRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    document = authorize(db, current_user, db.get(Document, doc_id), "share")

    if payload.level not in VALID_GRANT_LEVELS:
        raise HTTPException(status_code=400, detail="Invalid permission level. Use 'read' or 'edit'")

    normalized_email = payload.user_email.strip().lower()
    target_user = db.scalar(select(User).where(User.email == normalized_email))
    if not target_user:
        raise HTTPException(status_code=404, detail="Target user not found")

    if target_user.id == document.owner_id:
        raise HTTPException(status_code=400, detail="Cannot share a document with its owner")

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
    log_event(db, current_user.id, "grant_access", document.id, "allowed")

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
    document = authorize(db, current_user, db.get(Document, doc_id), "share")

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
    document = authorize(db, current_user, db.get(Document, doc_id), "share")

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
    log_event(db, current_user.id, "revoke_access", document.id, "allowed")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
