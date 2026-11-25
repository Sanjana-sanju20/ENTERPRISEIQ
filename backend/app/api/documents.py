from pathlib import Path
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, record_audit, require_roles
from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import ROLE_ADMIN, ROLE_ANALYST, ROLE_CEO, ROLE_MANAGER
from app.models.entities import BusinessMetric, Document, DocumentChunk, User
from app.processing.pipeline import process_uploaded_file

router = APIRouter(prefix="/api/documents", tags=["Knowledge Hub & Processing"])

ALLOWED_EXTENSIONS = {"pdf", "docx", "doc", "xlsx", "xls", "csv", "txt", "md"}
MAX_FILE_BYTES = 15 * 1024 * 1024  # 15 MB


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    category: str = Form("financial_report"),
    user: User = Depends(require_roles(ROLE_ANALYST, ROLE_ADMIN, ROLE_CEO, ROLE_MANAGER)),
    db: AsyncSession = Depends(get_db),
):
    filename = file.filename or "uploaded_document.txt"
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported file format '.{ext}'. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}")

    raw = await file.read()
    if len(raw) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    if len(raw) > MAX_FILE_BYTES:
        raise HTTPException(status_code=413, detail="File exceeds 15 MB limit.")

    settings = get_settings()
    upload_dir = Path(settings.UPLOAD_DIR) / user.organization_id
    upload_dir.mkdir(parents=True, exist_ok=True)
    safe_name = Path(filename).name
    dest = upload_dir / safe_name
    dest.write_bytes(raw)

    doc = Document(
        organization_id=user.organization_id,
        uploaded_by=user.id,
        filename=safe_name,
        file_type=ext,
        category=category,
        storage_path=str(dest),
        status="Processing",
        is_demo=False,
    )
    db.add(doc)
    await db.flush()

    result = process_uploaded_file(safe_name, raw)
    doc.preview_text = result["preview_text"]
    doc.processing_stats = result["stats"]
    doc.validation_issues = result["validation_issues"]
    doc.status = "Ready" if result["chunks"] else "Failed"

    for idx, (sec, text) in enumerate(result["chunks"]):
        db.add(
            DocumentChunk(
                organization_id=user.organization_id,
                document_id=doc.id,
                chunk_index=idx,
                page_or_section=sec,
                content=text,
                metadata_json={"category": category, "filename": safe_name},
            )
        )

    for m in result["extracted_metrics"]:
        db.add(
            BusinessMetric(
                organization_id=user.organization_id,
                period=m["period"],
                metric_name=m["metric_name"],
                actual_value=m["actual_value"],
                target_value=m["target_value"],
                is_demo=False,
            )
        )

    await record_audit(db, user.organization_id, user.email, "DOCUMENT_UPLOAD", "document", f"Uploaded and indexed '{safe_name}' ({len(result['chunks'])} chunks)")
    await db.commit()

    return {
        "id": doc.id,
        "filename": doc.filename,
        "file_type": doc.file_type,
        "category": doc.category,
        "status": doc.status,
        "processing_stats": doc.processing_stats,
        "validation_issues": doc.validation_issues,
        "preview_text": doc.preview_text,
    }


@router.get("")
async def list_documents(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    docs = (
        await db.execute(
            select(Document)
            .where(Document.organization_id == user.organization_id)
            .order_by(Document.created_at.desc())
        )
    ).scalars().all()
    return [
        {
            "id": d.id,
            "filename": d.filename,
            "file_type": d.file_type,
            "category": d.category,
            "status": d.status,
            "is_demo": d.is_demo,
            "processing_stats": d.processing_stats,
            "validation_issues": d.validation_issues,
            "created_at": d.created_at.isoformat(),
        }
        for d in docs
    ]


@router.get("/{doc_id}")
async def get_document(doc_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    doc = (
        await db.execute(select(Document).where(Document.id == doc_id, Document.organization_id == user.organization_id))
    ).scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    chunks = (
        await db.execute(
            select(DocumentChunk).where(DocumentChunk.document_id == doc.id).order_by(DocumentChunk.chunk_index.asc())
        )
    ).scalars().all()
    return {
        "id": doc.id,
        "filename": doc.filename,
        "file_type": doc.file_type,
        "category": doc.category,
        "status": doc.status,
        "is_demo": doc.is_demo,
        "processing_stats": doc.processing_stats,
        "validation_issues": doc.validation_issues,
        "preview_text": doc.preview_text,
        "chunks": [{"id": c.id, "page_or_section": c.page_or_section, "content": c.content} for c in chunks],
    }


@router.get("/{doc_id}/status")
async def get_document_status(doc_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    doc = (
        await db.execute(select(Document).where(Document.id == doc_id, Document.organization_id == user.organization_id))
    ).scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    stages = ["Uploaded", "Validating", "Extracting", "Processing", "Indexed", "Ready"]
    return {
        "id": doc.id,
        "filename": doc.filename,
        "status": doc.status,
        "pipeline_stages": stages,
        "processing_stats": doc.processing_stats,
        "validation_issues": doc.validation_issues,
    }
