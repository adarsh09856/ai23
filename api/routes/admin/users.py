"""
Admin Users Routes
Complete CRUD for managing all platform users with statistics and controls.
"""
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, EmailStr
from sqlalchemy import func, select, text, update, delete, desc, asc
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import selectinload, joinedload

from api.constants import DATABASE_URL
from api.db import db_client
from api.db.models import (
    UserModel, 
    OrganizationModel, 
    WorkflowModel,
    CallModel,
    organization_users_association
)
from api.services.auth.depends import get_superuser

router = APIRouter(prefix="/admin/users", tags=["admin-users"])

engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
async_session = async_sessionmaker(bind=engine)


class UserStatsModel(BaseModel):
    total_calls: int = 0
    total_minutes: float = 0.0
    total_workflows: int = 0
    active_workflows: int = 0
    last_activity: Optional[datetime] = None
    calls_last_30_days: int = 0
    minutes_last_30_days: float = 0.0


class OrganizationSummary(BaseModel):
    id: int
    name: str
    is_active: bool


class AdminUserResponse(BaseModel):
    id: int
    email: Optional[str]
    is_active: bool = True
    is_superuser: bool = False
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    phone_number: Optional[str] = None
    selected_organization_id: Optional[int]
    organizations: List[OrganizationSummary] = []
    stats: Optional[UserStatsModel] = None


class AdminUsersListResponse(BaseModel):
    users: List[AdminUserResponse]
    total_count: int
    page: int
    limit: int
    total_pages: int


class UpdateUserRequest(BaseModel):
    is_active: Optional[bool] = None
    is_superuser: Optional[bool] = None
    phone_number: Optional[str] = None


class UserActivityLog(BaseModel):
    timestamp: datetime
    action: str
    details: Dict[str, Any]


@router.get("", response_model=AdminUsersListResponse)
async def list_users(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    search: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    is_superuser: Optional[bool] = Query(None),
    sort_by: str = Query("created_at", regex="^(email|created_at|last_activity|total_calls)$"),
    sort_order: str = Query("desc", regex="^(asc|desc)$"),
    user: UserModel = Depends(get_superuser),
):
    """List all platform users with advanced filtering, pagination, and statistics."""
    offset = (page - 1) * limit

    async with async_session() as session:
        # Build base query
        base_q = select(UserModel).options(selectinload(UserModel.organizations))
        count_q = select(func.count(UserModel.id))

        # Apply filters
        filters = []
        if search:
            like = f"%{search.lower()}%"
            filters.append(func.lower(UserModel.email).like(like))
        
        if is_active is not None:
            filters.append(UserModel.is_active == is_active)
        
        if is_superuser is not None:
            filters.append(UserModel.is_superuser == is_superuser)

        if filters:
            base_q = base_q.where(*filters)
            count_q = count_q.where(*filters)

        # Get total count
        total_count = (await session.execute(count_q)).scalar_one()

        # Apply sorting
        order_col = getattr(UserModel, sort_by)
        if sort_order == "desc":
            order_col = desc(order_col)
        else:
            order_col = asc(order_col)

        # Get users with pagination
        users_result = await session.execute(
            base_q.order_by(order_col).offset(offset).limit(limit)
        )
        users = users_result.scalars().unique().all()

        # Get user statistics
        user_stats = {}
        if users:
            user_ids = [u.id for u in users]
            
            # Get call statistics
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)
            
            # Total calls and minutes
            stats_query = text("""
                SELECT 
                    u.id,
                    COUNT(c.id) as total_calls,
                    COALESCE(SUM(EXTRACT(EPOCH FROM (c.ended_at - c.started_at)) / 60.0), 0) as total_minutes,
                    MAX(c.started_at) as last_call_at,
                    COUNT(CASE WHEN c.started_at >= :thirty_days_ago THEN 1 END) as calls_last_30_days,
                    COALESCE(SUM(CASE WHEN c.started_at >= :thirty_days_ago 
                        THEN EXTRACT(EPOCH FROM (c.ended_at - c.started_at)) / 60.0 END), 0) as minutes_last_30_days
                FROM users u
                LEFT JOIN organizations o ON o.id = ANY(
                    SELECT organization_id FROM organization_users WHERE user_id = u.id
                )
                LEFT JOIN calls c ON c.organization_id = o.id AND c.ended_at IS NOT NULL
                WHERE u.id = ANY(:user_ids)
                GROUP BY u.id
            """)
            
            stats_result = await session.execute(
                stats_query, 
                {"user_ids": user_ids, "thirty_days_ago": thirty_days_ago}
            )
            
            for row in stats_result:
                user_stats[row[0]] = UserStatsModel(
                    total_calls=row[1] or 0,
                    total_minutes=float(row[2]) if row[2] else 0.0,
                    last_activity=row[3],
                    calls_last_30_days=row[4] or 0,
                    minutes_last_30_days=float(row[5]) if row[5] else 0.0,
                )
            
            # Get workflow counts
            workflow_stats = await session.execute(
                select(
                    WorkflowModel.organization_id,
                    func.count(WorkflowModel.id).label('total_workflows'),
                    func.sum(func.cast(WorkflowModel.is_active, func.Integer)).label('active_workflows')
                ).where(
                    WorkflowModel.organization_id.in_(
                        select(organization_users_association.c.organization_id)
                        .where(organization_users_association.c.user_id.in_(user_ids))
                    )
                ).group_by(WorkflowModel.organization_id)
            )
            
            workflow_counts = {r[0]: (r[1], r[2]) for r in workflow_stats}

    total_pages = (total_count + limit - 1) // limit
    
    # Build response
    response_users = []
    for u in users:
        stats = user_stats.get(u.id, UserStatsModel())
        
        # Add workflow stats from user's organizations
        for org in u.organizations:
            if org.id in workflow_counts:
                total_wf, active_wf = workflow_counts[org.id]
                stats.total_workflows += total_wf or 0
                stats.active_workflows += active_wf or 0
        
        response_users.append(AdminUserResponse(
            id=u.id,
            email=u.email,
            is_active=u.is_active,
            is_superuser=u.is_superuser,
            created_at=u.created_at,
            updated_at=u.updated_at,
            phone_number=u.phone_number,
            selected_organization_id=u.selected_organization_id,
            organizations=[
                OrganizationSummary(
                    id=org.id,
                    name=org.name,
                    is_active=org.is_active
                ) for org in u.organizations
            ],
            stats=stats,
        ))

    return AdminUsersListResponse(
        users=response_users,
        total_count=total_count,
        page=page,
        limit=limit,
        total_pages=total_pages,
    )


@router.get("/{user_id}", response_model=AdminUserResponse)
async def get_user_detail(
    user_id: int,
    user: UserModel = Depends(get_superuser),
):
    """Get detailed information for a specific user including full statistics."""
    async with async_session() as session:
        # Get user with organizations
        user_result = await session.execute(
            select(UserModel)
            .options(selectinload(UserModel.organizations))
            .where(UserModel.id == user_id)
        )
        target_user = user_result.scalars().first()
        
        if not target_user:
            raise HTTPException(status_code=404, detail="User not found")

        # Get comprehensive statistics
        stats_query = text("""
            SELECT 
                COUNT(c.id) as total_calls,
                COALESCE(SUM(EXTRACT(EPOCH FROM (c.ended_at - c.started_at)) / 60.0), 0) as total_minutes,
                MAX(c.started_at) as last_activity,
                COUNT(CASE WHEN c.started_at >= NOW() - INTERVAL '30 days' THEN 1 END) as calls_last_30_days,
                COALESCE(SUM(CASE WHEN c.started_at >= NOW() - INTERVAL '30 days' 
                    THEN EXTRACT(EPOCH FROM (c.ended_at - c.started_at)) / 60.0 END), 0) as minutes_last_30_days
            FROM organizations o
            JOIN organization_users ou ON ou.organization_id = o.id
            LEFT JOIN calls c ON c.organization_id = o.id AND c.ended_at IS NOT NULL
            WHERE ou.user_id = :user_id
        """)
        
        stats_result = await session.execute(stats_query, {"user_id": user_id})
        stats_row = stats_result.fetchone()
        
        # Get workflow counts
        workflow_result = await session.execute(
            select(
                func.count(WorkflowModel.id).label('total_workflows'),
                func.sum(func.cast(WorkflowModel.is_active, func.Integer)).label('active_workflows')
            ).where(
                WorkflowModel.organization_id.in_(
                    select(organization_users_association.c.organization_id)
                    .where(organization_users_association.c.user_id == user_id)
                )
            )
        )
        workflow_row = workflow_result.fetchone()
        
        stats = UserStatsModel(
            total_calls=stats_row[0] or 0,
            total_minutes=float(stats_row[1]) if stats_row[1] else 0.0,
            last_activity=stats_row[2],
            calls_last_30_days=stats_row[3] or 0,
            minutes_last_30_days=float(stats_row[4]) if stats_row[4] else 0.0,
            total_workflows=workflow_row[0] or 0,
            active_workflows=workflow_row[1] or 0,
        )

        return AdminUserResponse(
            id=target_user.id,
            email=target_user.email,
            is_active=target_user.is_active,
            is_superuser=target_user.is_superuser,
            created_at=target_user.created_at,
            updated_at=target_user.updated_at,
            phone_number=target_user.phone_number,
            selected_organization_id=target_user.selected_organization_id,
            organizations=[
                OrganizationSummary(
                    id=org.id,
                    name=org.name,
                    is_active=org.is_active
                ) for org in target_user.organizations
            ],
            stats=stats,
        )


@router.patch("/{user_id}", response_model=AdminUserResponse)
async def update_user(
    user_id: int,
    update_data: UpdateUserRequest,
    user: UserModel = Depends(get_superuser),
):
    """Update user settings. Admin only."""
    async with async_session() as session:
        # Check if user exists
        user_result = await session.execute(
            select(UserModel).where(UserModel.id == user_id)
        )
        target_user = user_result.scalars().first()
        
        if not target_user:
            raise HTTPException(status_code=404, detail="User not found")

        # Prevent admin from deactivating themselves
        if user_id == user.id and update_data.is_active is False:
            raise HTTPException(status_code=400, detail="Cannot deactivate yourself")

        # Update fields
        update_fields = {}
        if update_data.is_active is not None:
            update_fields["is_active"] = update_data.is_active
        if update_data.is_superuser is not None:
            update_fields["is_superuser"] = update_data.is_superuser
        if update_data.phone_number is not None:
            update_fields["phone_number"] = update_data.phone_number
        
        if update_fields:
            update_fields["updated_at"] = datetime.utcnow()
            await session.execute(
                update(UserModel)
                .where(UserModel.id == user_id)
                .values(**update_fields)
            )
            await session.commit()

        # Return updated user details
        return await get_user_detail(user_id, user)


@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    user: UserModel = Depends(get_superuser),
):
    """
    Delete a user permanently. This will:
    1. Remove user from all organizations
    2. Delete the user account
    WARNING: This action cannot be undone.
    """
    if user_id == user.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")

    async with async_session() as session:
        # Check if user exists
        target_user = await session.execute(
            select(UserModel).where(UserModel.id == user_id)
        )
        if not target_user.scalars().first():
            raise HTTPException(status_code=404, detail="User not found")

        # Remove from organizations first (foreign key constraint)
        await session.execute(
            delete(organization_users_association).where(
                organization_users_association.c.user_id == user_id
            )
        )
        
        # Delete user
        await session.execute(
            delete(UserModel).where(UserModel.id == user_id)
        )
        
        await session.commit()

    return {"message": f"User {user_id} deleted successfully"}


@router.get("/stats/overview")
async def get_users_overview(user: UserModel = Depends(get_superuser)):
    """Get platform-wide user statistics overview."""
    async with async_session() as session:
        # Basic counts
        total_users = (await session.execute(
            select(func.count(UserModel.id))
        )).scalar_one()
        
        active_users = (await session.execute(
            select(func.count(UserModel.id)).where(UserModel.is_active == True)
        )).scalar_one()
        
        superusers = (await session.execute(
            select(func.count(UserModel.id)).where(UserModel.is_superuser == True)
        )).scalar_one()

        # Recent activity
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        
        new_users_30d = (await session.execute(
            select(func.count(UserModel.id)).where(
                UserModel.created_at >= thirty_days_ago
            )
        )).scalar_one()
        
        new_users_7d = (await session.execute(
            select(func.count(UserModel.id)).where(
                UserModel.created_at >= seven_days_ago
            )
        )).scalar_one()

        # Active users (made calls recently)
        active_users_30d_query = text("""
            SELECT COUNT(DISTINCT u.id)
            FROM users u
            JOIN organization_users ou ON ou.user_id = u.id
            JOIN calls c ON c.organization_id = ou.organization_id
            WHERE c.started_at >= :thirty_days_ago
        """)
        
        active_users_30d = (await session.execute(
            active_users_30d_query, {"thirty_days_ago": thirty_days_ago}
        )).scalar_one()

        return {
            "total_users": total_users,
            "active_users": active_users,
            "inactive_users": total_users - active_users,
            "superusers": superusers,
            "new_users_30_days": new_users_30d,
            "new_users_7_days": new_users_7d,
            "users_with_activity_30_days": active_users_30d or 0,
            "growth_rate_30d": (new_users_30d / max(total_users - new_users_30d, 1)) * 100,
        }
