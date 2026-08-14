"""
Admin Call Moderation Routes
Complete call moderation system for platform administrators.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, Query, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select, desc, func, and_, or_, String
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.database import get_db
from api.db.models import (
    WorkflowRunModel, UserModel, OrganizationModel, WorkflowModel,
    ViolationModel, AdminAuditLogModel, BannedWordModel
)
from api.services.auth.depends import get_superuser

router = APIRouter(prefix="/admin/calls", tags=["admin-calls"])

# Request/Response Schemas
class CallListItem(BaseModel):
    id: int
    started_at: datetime
    caller: str
    callee: str
    user: Dict[str, Any]
    organization: Dict[str, Any] 
    status: str
    duration_seconds: Optional[int]
    workflow: Dict[str, Any]
    disposition: Optional[str]
    recording_url: Optional[str]

class CallListResponse(BaseModel):
    items: List[CallListItem]
    total: int
    page: int
    pages: int

class CallDetailResponse(BaseModel):
    id: int
    started_at: datetime
    completed_at: Optional[datetime]
    caller: str
    callee: str
    direction: str
    status: str
    duration_seconds: Optional[int]
    workflow: Dict[str, Any]
    user: Dict[str, Any]
    organization: Dict[str, Any]
    recording_url: Optional[str]
    transcript: Optional[List[Dict[str, Any]]]
    ai_summary: Optional[str]
    sentiment: Optional[str]
    classification: Optional[str]
    events: List[Dict[str, Any]]
    admin_notes: List[Dict[str, Any]]
    moderation_actions: List[Dict[str, Any]]

class BanUserRequest(BaseModel):
    reason: str = Field(..., min_length=10, description="Reason for banning the user")

class FlagCallRequest(BaseModel):
    severity: str = Field(..., pattern="^(low|medium|high|critical)$")
    reason: str = Field(..., min_length=5)

class AddNoteRequest(BaseModel):
    note: str = Field(..., min_length=1)

class ViolationItem(BaseModel):
    id: int
    call_id: int
    call_timestamp: datetime
    user: Dict[str, Any]
    org: Dict[str, Any]
    detected_phrase: str
    severity: str
    status: str
    reviewed_by: Optional[Dict[str, Any]]
    reviewed_at: Optional[datetime]

class ViolationsResponse(BaseModel):
    items: List[ViolationItem]
    total: int
    page: int
    pages: int

# Routes

@router.get("/", response_model=CallListResponse)
async def get_calls(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    status: Optional[str] = Query(None),
    direction: Optional[str] = Query(None),
    user_id: Optional[int] = Query(None),
    org_id: Optional[int] = Query(None),
    phone_number: Optional[str] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    admin_user: UserModel = Depends(get_superuser)
):
    """
    List all platform calls with filtering and pagination.
    Only accessible to superuser admin accounts.
    """
    # Base query with joins
    query = select(WorkflowRunModel).options(
        selectinload(WorkflowRunModel.user),
        selectinload(WorkflowRunModel.organization), 
        selectinload(WorkflowRunModel.workflow)
    )
    
    # Apply filters
    conditions = []
    
    if status:
        conditions.append(WorkflowRunModel.status == status)
    
    if direction:
        conditions.append(WorkflowRunModel.direction == direction)
        
    if user_id:
        conditions.append(WorkflowRunModel.user_id == user_id)
        
    if org_id:
        conditions.append(WorkflowRunModel.organization_id == org_id)
        
    if phone_number:
        conditions.append(
            or_(
                WorkflowRunModel.caller.ilike(f"%{phone_number}%"),
                WorkflowRunModel.callee.ilike(f"%{phone_number}%")
            )
        )
        
    if date_from:
        conditions.append(WorkflowRunModel.started_at >= date_from)
        
    if date_to:
        conditions.append(WorkflowRunModel.started_at <= date_to)
        
    if search:
        # Search in run ID, user email, org name
        conditions.append(
            or_(
                func.cast(WorkflowRunModel.id, String).ilike(f"%{search}%"),
                WorkflowRunModel.user.has(UserModel.email.ilike(f"%{search}%")),
                WorkflowRunModel.organization.has(OrganizationModel.name.ilike(f"%{search}%"))
            )
        )
    
    if conditions:
        query = query.where(and_(*conditions))
    
    # Get total count
    count_query = select(func.count(WorkflowRunModel.id))
    if conditions:
        count_query = count_query.where(and_(*conditions))
    
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Apply pagination and ordering
    offset = (page - 1) * limit
    query = query.order_by(desc(WorkflowRunModel.started_at)).offset(offset).limit(limit)
    
    result = await db.execute(query)
    calls = result.scalars().all()
    
    # Format response
    items = []
    for call in calls:
        items.append(CallListItem(
            id=call.id,
            started_at=call.started_at,
            caller=call.caller or "",
            callee=call.callee or "",
            user={
                "id": call.user.id,
                "email": call.user.email,
                "name": f"{call.user.first_name or ''} {call.user.last_name or ''}".strip()
            },
            organization={
                "id": call.organization.id,
                "name": call.organization.name
            },
            status=call.status,
            duration_seconds=call.duration_seconds,
            workflow={
                "id": call.workflow.id,
                "name": call.workflow.name
            },
            disposition=call.disposition,
            recording_url=call.recording_url
        ))
    
    pages = (total + limit - 1) // limit
    
    return CallListResponse(
        items=items,
        total=total,
        page=page,
        pages=pages
    )


@router.get("/{run_id}", response_model=CallDetailResponse)
async def get_call_detail(
    run_id: int,
    db: AsyncSession = Depends(get_db),
    admin_user: UserModel = Depends(get_superuser)
):
    """
    Get detailed call information including transcript, events, and moderation history.
    """
    # Get call with all relations
    query = select(WorkflowRunModel).options(
        selectinload(WorkflowRunModel.user),
        selectinload(WorkflowRunModel.organization),
        selectinload(WorkflowRunModel.workflow)
    ).where(WorkflowRunModel.id == run_id)
    
    result = await db.execute(query)
    call = result.scalar_one_or_none()
    
    if not call:
        raise HTTPException(404, "Call not found")
    
    # Get admin notes from metadata (assuming stored in JSON field)
    admin_notes = call.metadata.get("admin_notes", []) if call.metadata else []
    
    # Get moderation actions from audit log
    audit_query = select(AdminAuditLogModel).where(
        and_(
            AdminAuditLogModel.target_type == "call",
            AdminAuditLogModel.target_id == run_id
        )
    ).order_by(desc(AdminAuditLogModel.created_at))
    
    audit_result = await db.execute(audit_query)
    audit_logs = audit_result.scalars().all()
    
    moderation_actions = []
    for log in audit_logs:
        moderation_actions.append({
            "action": log.action_type,
            "reason": log.summary_json.get("reason", "") if log.summary_json else "",
            "created_by": {
                "id": log.admin_user_id,
                "email": "admin@admin.com"  # Known admin email
            },
            "created_at": log.created_at
        })
    
    # Get call events from metadata
    events = call.metadata.get("events", []) if call.metadata else []
    
    # Get transcript from metadata
    transcript = call.metadata.get("transcript", []) if call.metadata else []
    
    return CallDetailResponse(
        id=call.id,
        started_at=call.started_at,
        completed_at=call.completed_at,
        caller=call.caller or "",
        callee=call.callee or "",
        direction=call.direction or "outbound",
        status=call.status,
        duration_seconds=call.duration_seconds,
        workflow={
            "id": call.workflow.id,
            "name": call.workflow.name,
            "config": call.workflow.config
        },
        user={
            "id": call.user.id,
            "email": call.user.email,
            "name": f"{call.user.first_name or ''} {call.user.last_name or ''}".strip(),
            "status": getattr(call.user, "status", "active")
        },
        organization={
            "id": call.organization.id,
            "name": call.organization.name,
            "status": getattr(call.organization, "status", "active")
        },
        recording_url=call.recording_url,
        transcript=transcript,
        ai_summary=call.metadata.get("ai_summary") if call.metadata else None,
        sentiment=call.metadata.get("sentiment") if call.metadata else None,
        classification=call.metadata.get("classification") if call.metadata else None,
        events=events,
        admin_notes=admin_notes,
        moderation_actions=moderation_actions
    )


@router.post("/{run_id}/ban-user")
async def ban_user(
    run_id: int,
    request: BanUserRequest,
    db: AsyncSession = Depends(get_db),
    admin_user: UserModel = Depends(get_superuser)
):
    """
    Ban the user who made this call.
    Creates audit log entry and updates user status.
    """
    # Get the call and user
    call_query = select(WorkflowRunModel).options(
        selectinload(WorkflowRunModel.user)
    ).where(WorkflowRunModel.id == run_id)
    
    call_result = await db.execute(call_query)
    call = call_result.scalar_one_or_none()
    
    if not call:
        raise HTTPException(404, "Call not found")
    
    user = call.user
    
    # Update user status to banned
    user.status = "banned"
    
    # Create audit log entry
    audit_log = AdminAuditLogModel(
        admin_user_id=admin_user.id,
        action_type="ban_user",
        target_type="user", 
        target_id=user.id,
        ip_address="127.0.0.1",  # Would be extracted from request in real implementation
        summary_json={
            "action": f"User {user.id} banned by admin {admin_user.id}",
            "reason": request.reason,
            "call_id": run_id
        }
    )
    
    db.add(audit_log)
    await db.commit()
    
    return {
        "success": True,
        "message": "User banned successfully",
        "user": {
            "id": user.id,
            "email": user.email,
            "status": "banned"
        }
    }


@router.post("/{run_id}/flag")
async def flag_call(
    run_id: int,
    request: FlagCallRequest,
    db: AsyncSession = Depends(get_db),
    admin_user: UserModel = Depends(get_superuser)
):
    """
    Flag a call for review by creating a violation record.
    """
    # Verify call exists
    call_query = select(WorkflowRunModel).where(WorkflowRunModel.id == run_id)
    call_result = await db.execute(call_query)
    call = call_result.scalar_one_or_none()
    
    if not call:
        raise HTTPException(404, "Call not found")
    
    # Create violation record
    violation = ViolationModel(
        call_id=run_id,
        user_id=call.user_id,
        detected_phrase=f"Admin flagged: {request.reason}",
        severity=request.severity,
        status="pending",
        notes_json={"flagged_by_admin": True, "reason": request.reason}
    )
    
    db.add(violation)
    
    # Create audit log entry
    audit_log = AdminAuditLogModel(
        admin_user_id=admin_user.id,
        action_type="flag_call",
        target_type="call",
        target_id=run_id,
        ip_address="127.0.0.1",
        summary_json={
            "action": f"Call {run_id} flagged by admin {admin_user.id}",
            "severity": request.severity,
            "reason": request.reason
        }
    )
    
    db.add(audit_log)
    await db.commit()
    
    return {
        "success": True,
        "violation_id": violation.id
    }


@router.patch("/{run_id}/notes")
async def add_note(
    run_id: int,
    request: AddNoteRequest,
    db: AsyncSession = Depends(get_db),
    admin_user: UserModel = Depends(get_superuser)
):
    """
    Add admin notes to a call.
    """
    # Get the call
    call_query = select(WorkflowRunModel).where(WorkflowRunModel.id == run_id)
    call_result = await db.execute(call_query)
    call = call_result.scalar_one_or_none()
    
    if not call:
        raise HTTPException(404, "Call not found")
    
    # Add note to metadata
    if not call.metadata:
        call.metadata = {}
    
    if "admin_notes" not in call.metadata:
        call.metadata["admin_notes"] = []
    
    note_entry = {
        "id": len(call.metadata["admin_notes"]) + 1,
        "note": request.note,
        "created_by": {
            "id": admin_user.id,
            "email": admin_user.email
        },
        "created_at": datetime.utcnow().isoformat()
    }
    
    call.metadata["admin_notes"].append(note_entry)
    
    # Mark as modified for SQLAlchemy
    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(call, "metadata")
    
    await db.commit()
    
    return {
        "success": True,
        "note": note_entry
    }


@router.delete("/{run_id}")
async def delete_call(
    run_id: int,
    db: AsyncSession = Depends(get_db),
    admin_user: UserModel = Depends(get_superuser)
):
    """
    Delete a call record (soft delete).
    """
    # Get the call
    call_query = select(WorkflowRunModel).where(WorkflowRunModel.id == run_id)
    call_result = await db.execute(call_query)
    call = call_result.scalar_one_or_none()
    
    if not call:
        raise HTTPException(404, "Call not found")
    
    # Soft delete by updating status
    call.status = "deleted"
    
    # Create audit log entry
    audit_log = AdminAuditLogModel(
        admin_user_id=admin_user.id,
        action_type="delete_call",
        target_type="call",
        target_id=run_id,
        ip_address="127.0.0.1",
        summary_json={
            "action": f"Call {run_id} deleted by admin {admin_user.id}"
        }
    )
    
    db.add(audit_log)
    await db.commit()
    
    return {
        "success": True,
        "message": "Call deleted successfully"
    }


@router.get("/violations", response_model=ViolationsResponse)
async def get_violations(
    severity: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    admin_user: UserModel = Depends(get_superuser)
):
    """
    Get moderation queue (violations list).
    """
    # Base query with joins
    query = select(ViolationModel).options(
        selectinload(ViolationModel.user),
        selectinload(ViolationModel.call),
        selectinload(ViolationModel.call.organization)
    )
    
    # Apply filters
    conditions = []
    
    if severity:
        conditions.append(ViolationModel.severity == severity)
        
    if status:
        conditions.append(ViolationModel.status == status)
    
    if conditions:
        query = query.where(and_(*conditions))
    
    # Get total count
    count_query = select(func.count(ViolationModel.id))
    if conditions:
        count_query = count_query.where(and_(*conditions))
        
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Apply pagination
    offset = (page - 1) * limit
    query = query.order_by(desc(ViolationModel.created_at)).offset(offset).limit(limit)
    
    result = await db.execute(query)
    violations = result.scalars().all()
    
    # Format response
    items = []
    for violation in violations:
        items.append(ViolationItem(
            id=violation.id,
            call_id=violation.call_id,
            call_timestamp=violation.call.started_at,
            user={
                "id": violation.user.id,
                "email": violation.user.email
            },
            org={
                "id": violation.call.organization.id,
                "name": violation.call.organization.name
            },
            detected_phrase=violation.detected_phrase,
            severity=violation.severity,
            status=violation.status,
            reviewed_by={
                "id": violation.reviewed_by,
                "email": "admin@admin.com"
            } if violation.reviewed_by else None,
            reviewed_at=violation.reviewed_at
        ))
    
    pages = (total + limit - 1) // limit
    
    return ViolationsResponse(
        items=items,
        total=total,
        page=page,
        pages=pages
    )
