"""
Admin Content Moderation Routes
Manage banned words and content moderation rules.
"""
from datetime import datetime
from typing import Optional, List
import csv
import io

from fastapi import APIRouter, Depends, Query, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select, desc, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.database import get_db
from api.db.models import BannedWordModel, AdminAuditLogModel, UserModel
from api.services.auth.depends import get_superuser

router = APIRouter(prefix="/admin/content", tags=["admin-content"])

# Request/Response Schemas
class BannedWordCreate(BaseModel):
    phrase: str = Field(..., min_length=2, max_length=200)
    severity: str = Field(..., pattern="^(low|medium|high|critical)$")
    enabled: bool = True

class BannedWordUpdate(BaseModel):
    phrase: Optional[str] = Field(None, min_length=2, max_length=200)
    severity: Optional[str] = Field(None, pattern="^(low|medium|high|critical)$")
    enabled: Optional[bool] = None

class BannedWordResponse(BaseModel):
    id: int
    phrase: str
    severity: str
    enabled: bool
    created_at: datetime

class BannedWordsListResponse(BaseModel):
    items: List[BannedWordResponse]
    total: int
    page: int
    pages: int

class ImportResult(BaseModel):
    success: bool
    imported: int
    errors: List[dict]

# Routes

@router.get("/banned-words", response_model=BannedWordsListResponse)
async def get_banned_words(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    severity: Optional[str] = Query(None),
    enabled: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    admin_user: UserModel = Depends(get_superuser)
):
    """
    List all banned words with filtering and pagination.
    """
    # Build query
    query = select(BannedWordModel)
    conditions = []
    
    if severity:
        conditions.append(BannedWordModel.severity == severity)
    
    if enabled is not None:
        conditions.append(BannedWordModel.enabled == enabled)
        
    if search:
        conditions.append(BannedWordModel.phrase.ilike(f"%{search}%"))
    
    if conditions:
        query = query.where(and_(*conditions))
    
    # Get total count
    count_query = select(func.count(BannedWordModel.id))
    if conditions:
        count_query = count_query.where(and_(*conditions))
    
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Apply pagination and ordering
    offset = (page - 1) * limit
    query = query.order_by(desc(BannedWordModel.created_at)).offset(offset).limit(limit)
    
    result = await db.execute(query)
    words = result.scalars().all()
    
    # Format response
    items = [
        BannedWordResponse(
            id=word.id,
            phrase=word.phrase,
            severity=word.severity,
            enabled=word.enabled,
            created_at=word.created_at
        )
        for word in words
    ]
    
    pages = (total + limit - 1) // limit
    
    return BannedWordsListResponse(
        items=items,
        total=total,
        page=page,
        pages=pages
    )


@router.post("/banned-words", response_model=BannedWordResponse)
async def create_banned_word(
    request: BannedWordCreate,
    db: AsyncSession = Depends(get_db),
    admin_user: UserModel = Depends(get_superuser)
):
    """
    Create a new banned word.
    """
    # Check if phrase already exists
    existing_query = select(BannedWordModel).where(
        func.lower(BannedWordModel.phrase) == func.lower(request.phrase)
    )
    existing_result = await db.execute(existing_query)
    existing_word = existing_result.scalar_one_or_none()
    
    if existing_word:
        raise HTTPException(400, "This phrase is already in the banned words list")
    
    # Create new banned word
    banned_word = BannedWordModel(
        phrase=request.phrase.strip(),
        severity=request.severity,
        enabled=request.enabled
    )
    
    db.add(banned_word)
    await db.flush()
    
    # Create audit log entry
    audit_log = AdminAuditLogModel(
        admin_user_id=admin_user.id,
        action_type="create",
        target_type="banned_word",
        target_id=banned_word.id,
        ip_address="127.0.0.1",
        summary_json={
            "action": f"Created banned word '{request.phrase}' with severity '{request.severity}'",
            "phrase": request.phrase,
            "severity": request.severity
        }
    )
    
    db.add(audit_log)
    await db.commit()
    
    return BannedWordResponse(
        id=banned_word.id,
        phrase=banned_word.phrase,
        severity=banned_word.severity,
        enabled=banned_word.enabled,
        created_at=banned_word.created_at
    )


@router.patch("/banned-words/{word_id}", response_model=BannedWordResponse)
async def update_banned_word(
    word_id: int,
    request: BannedWordUpdate,
    db: AsyncSession = Depends(get_db),
    admin_user: UserModel = Depends(get_superuser)
):
    """
    Update a banned word.
    """
    # Get existing word
    query = select(BannedWordModel).where(BannedWordModel.id == word_id)
    result = await db.execute(query)
    banned_word = result.scalar_one_or_none()
    
    if not banned_word:
        raise HTTPException(404, "Banned word not found")
    
    # Update fields
    if request.phrase is not None:
        # Check for duplicates (excluding current word)
        existing_query = select(BannedWordModel).where(
            and_(
                func.lower(BannedWordModel.phrase) == func.lower(request.phrase),
                BannedWordModel.id != word_id
            )
        )
        existing_result = await db.execute(existing_query)
        existing_word = existing_result.scalar_one_or_none()
        
        if existing_word:
            raise HTTPException(400, "This phrase is already in the banned words list")
        
        banned_word.phrase = request.phrase.strip()
    
    if request.severity is not None:
        banned_word.severity = request.severity
    
    if request.enabled is not None:
        banned_word.enabled = request.enabled
    
    # Create audit log entry
    changes = {}
    if request.phrase is not None:
        changes['phrase'] = request.phrase
    if request.severity is not None:
        changes['severity'] = request.severity
    if request.enabled is not None:
        changes['enabled'] = request.enabled
    
    audit_log = AdminAuditLogModel(
        admin_user_id=admin_user.id,
        action_type="update",
        target_type="banned_word",
        target_id=banned_word.id,
        ip_address="127.0.0.1",
        summary_json={
            "action": f"Updated banned word '{banned_word.phrase}'",
            "changes": changes
        }
    )
    
    db.add(audit_log)
    await db.commit()
    
    return BannedWordResponse(
        id=banned_word.id,
        phrase=banned_word.phrase,
        severity=banned_word.severity,
        enabled=banned_word.enabled,
        created_at=banned_word.created_at
    )


@router.delete("/banned-words/{word_id}")
async def delete_banned_word(
    word_id: int,
    db: AsyncSession = Depends(get_db),
    admin_user: UserModel = Depends(get_superuser)
):
    """
    Delete a banned word.
    """
    # Get existing word
    query = select(BannedWordModel).where(BannedWordModel.id == word_id)
    result = await db.execute(query)
    banned_word = result.scalar_one_or_none()
    
    if not banned_word:
        raise HTTPException(404, "Banned word not found")
    
    phrase = banned_word.phrase  # Save for audit log
    
    # Delete the word
    await db.delete(banned_word)
    
    # Create audit log entry
    audit_log = AdminAuditLogModel(
        admin_user_id=admin_user.id,
        action_type="delete",
        target_type="banned_word",
        target_id=word_id,
        ip_address="127.0.0.1",
        summary_json={
            "action": f"Deleted banned word '{phrase}'",
            "phrase": phrase
        }
    )
    
    db.add(audit_log)
    await db.commit()
    
    return {"success": True, "message": "Banned word deleted successfully"}


@router.post("/banned-words/import", response_model=ImportResult)
async def import_banned_words(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    admin_user: UserModel = Depends(get_superuser)
):
    """
    Import banned words from CSV file.
    Expected format: phrase,severity
    """
    if not file.filename.endswith('.csv'):
        raise HTTPException(400, "File must be a CSV")
    
    # Read and parse CSV
    content = await file.read()
    csv_content = content.decode('utf-8')
    csv_reader = csv.DictReader(io.StringIO(csv_content))
    
    imported_count = 0
    errors = []
    imported_phrases = []
    
    # Get existing phrases for duplicate checking
    existing_query = select(BannedWordModel.phrase)
    existing_result = await db.execute(existing_query)
    existing_phrases = set(phrase.lower() for phrase in existing_result.scalars())
    
    for row_num, row in enumerate(csv_reader, start=2):  # Start at 2 because row 1 is header
        try:
            # Validate required fields
            if 'phrase' not in row or 'severity' not in row:
                errors.append({
                    "row": row_num,
                    "error": "Missing required columns 'phrase' and/or 'severity'"
                })
                continue
            
            phrase = row['phrase'].strip()
            severity = row['severity'].strip().lower()
            
            # Validate data
            if len(phrase) < 2:
                errors.append({
                    "row": row_num,
                    "error": "Phrase must be at least 2 characters long"
                })
                continue
            
            if severity not in ['low', 'medium', 'high', 'critical']:
                errors.append({
                    "row": row_num,
                    "error": "Severity must be one of: low, medium, high, critical"
                })
                continue
            
            # Check for duplicates
            if phrase.lower() in existing_phrases or phrase.lower() in imported_phrases:
                errors.append({
                    "row": row_num,
                    "error": f"Duplicate phrase: '{phrase}'"
                })
                continue
            
            # Create banned word
            banned_word = BannedWordModel(
                phrase=phrase,
                severity=severity,
                enabled=True
            )
            
            db.add(banned_word)
            imported_phrases.append(phrase.lower())
            imported_count += 1
            
        except Exception as e:
            errors.append({
                "row": row_num,
                "error": f"Unexpected error: {str(e)}"
            })
    
    # Create audit log entry
    audit_log = AdminAuditLogModel(
        admin_user_id=admin_user.id,
        action_type="bulk_import",
        target_type="banned_words",
        target_id=None,
        ip_address="127.0.0.1",
        summary_json={
            "action": f"Imported {imported_count} banned words from CSV",
            "imported_count": imported_count,
            "errors_count": len(errors),
            "filename": file.filename
        }
    )
    
    db.add(audit_log)
    await db.commit()
    
    return ImportResult(
        success=True,
        imported=imported_count,
        errors=errors
    )


@router.get("/banned-words/export")
async def export_banned_words(
    enabled_only: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    admin_user: UserModel = Depends(get_superuser)
):
    """
    Export banned words to CSV file.
    """
    # Build query
    query = select(BannedWordModel).order_by(BannedWordModel.phrase)
    
    if enabled_only:
        query = query.where(BannedWordModel.enabled == True)
    
    result = await db.execute(query)
    words = result.scalars().all()
    
    # Generate CSV content
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow(['phrase', 'severity', 'enabled', 'created_at'])
    
    # Write data
    for word in words:
        writer.writerow([
            word.phrase,
            word.severity,
            word.enabled,
            word.created_at.isoformat()
        ])
    
    # Prepare response
    csv_content = output.getvalue()
    output.close()
    
    filename = f"banned_words_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    return StreamingResponse(
        io.BytesIO(csv_content.encode('utf-8')),
        media_type='text/csv',
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
