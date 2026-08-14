"""
Admin Organizations Routes
Complete CRUD for managing all platform organizations with statistics.
"""
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select, text, update, delete, desc, asc
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import selectinload

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

router = APIRouter(prefix="/admin/organizations", tags=["admin-organizations"])

engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
async_session = async_sessionmaker(bind=engine)


class OrganizationStatsModel(BaseModel):
    user_count: int = 0
    total_calls: int = 0
    total_minutes: float = 0.0
    total_workflows: int = 0
    active_workflows: int = 0
    last_activity: Optional[datetime] = None
    calls_last_30_days: int = 0
    minutes_last_30_days: float = 0.0
    avg_call_duration: float = 0.0


class UserSummary(BaseModel):
    id: int
    email: str
    is_active: bool


class AdminOrganizationResponse(BaseModel):
    id: int
    name: str
    is_active: bool = True
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    phone_number: Optional[str] = None
    users: List[UserSummary] = []
    stats: Optional[OrganizationStatsModel] = None


class AdminOrganizationsListResponse(BaseModel):
    organizations: List[AdminOrganizationResponse]
    total_count: int
    page: int
    limit: int
    total_pages: int


class UpdateOrganizationRequest(BaseModel):
    name: Optional[str] = None
    is_active: Optional[bool] = None
    phone_number: Optional[str] = None


class CreateOrganizationRequest(BaseModel):
    name: str
    phone_number: Optional[str] = None
    owner_email: Optional[str] = None  # If provided, add this user as owner


@router.get("", response_model=AdminOrganizationsListResponse)
async def list_organizations(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    search: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    sort_by: str = Query("created_at", regex="^(name|created_at|last_activity|total_calls|user_count)$"),
    sort_order: str = Query("desc", regex="^(asc|desc)$"),
    user: UserModel = Depends(get_superuser),
):
    """List all platform organizations with advanced filtering and statistics."""
    offset = (page - 1) * limit

    async with async_session() as session:
        # Build base query
        base_q = select(OrganizationModel).options(selectinload(OrganizationModel.users))
        count_q = select(func.count(OrganizationModel.id))

        # Apply filters
        filters = []
        if search:
            like = f"%{search.lower()}%"
            filters.append(func.lower(OrganizationModel.name).like(like))
        
        if is_active is not None:
            filters.append(OrganizationModel.is_active == is_active)

        if filters:
            base_q = base_q.where(*filters)
            count_q = count_q.where(*filters)

        # Get total count
        total_count = (await session.execute(count_q)).scalar_one()

        # Apply sorting - handle computed fields
        if sort_by in ["name", "created_at"]:
            order_col = getattr(OrganizationModel, sort_by)
            if sort_order == "desc":
                order_col = desc(order_col)
            else:
                order_col = asc(order_col)
            base_q = base_q.order_by(order_col)
        else:
            # For computed fields, we'll sort in Python after getting stats
            base_q = base_q.order_by(desc(OrganizationModel.created_at))

        # Get organizations with pagination
        orgs_result = await session.execute(base_q.offset(offset).limit(limit))
        organizations = orgs_result.scalars().unique().all()

        # Get comprehensive statistics for each org
        org_stats = {}
        if organizations:
            org_ids = [o.id for o in organizations]
            
            # Get call and user statistics
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)
            
            stats_query = text("""
                SELECT 
                    o.id,
                    COUNT(DISTINCT u.id) as user_count,
                    COUNT(c.id) as total_calls,
                    COALESCE(SUM(EXTRACT(EPOCH FROM (c.ended_at - c.started_at)) / 60.0), 0) as total_minutes,
                    MAX(c.started_at) as last_activity,
                    COUNT(CASE WHEN c.started_at >= :thirty_days_ago THEN 1 END) as calls_last_30_days,
                    COALESCE(SUM(CASE WHEN c.started_at >= :thirty_days_ago 
                        THEN EXTRACT(EPOCH FROM (c.ended_at - c.started_at)) / 60.0 END), 0) as minutes_last_30_days,
                    COUNT(w.id) as total_workflows,
                    COUNT(CASE WHEN w.is_active THEN 1 END) as active_workflows
                FROM organizations o
                LEFT JOIN organization_users ou ON ou.organization_id = o.id
                LEFT JOIN users u ON u.id = ou.user_id
                LEFT JOIN calls c ON c.organization_id = o.id AND c.ended_at IS NOT NULL
                LEFT JOIN workflows w ON w.organization_id = o.id
                WHERE o.id = ANY(:org_ids)
                GROUP BY o.id
            """)
            
            stats_result = await session.execute(
                stats_query, 
                {"org_ids": org_ids, "thirty_days_ago": thirty_days_ago}
            )
            
            for row in stats_result:
                total_calls = row[2] or 0
                total_minutes = float(row[3]) if row[3] else 0.0
                avg_duration = (total_minutes / total_calls) if total_calls > 0 else 0.0
                
                org_stats[row[0]] = OrganizationStatsModel(
                    user_count=row[1] or 0,
                    total_calls=total_calls,
                    total_minutes=total_minutes,
                    last_activity=row[4],
                    calls_last_30_days=row[5] or 0,
                    minutes_last_30_days=float(row[6]) if row[6] else 0.0,
                    total_workflows=row[7] or 0,
                    active_workflows=row[8] or 0,
                    avg_call_duration=avg_duration,
                )

    total_pages = (total_count + limit - 1) // limit
    
    # Build response
    response_orgs = []
    for o in organizations:
        stats = org_stats.get(o.id, OrganizationStatsModel())
        
        response_orgs.append(AdminOrganizationResponse(
            id=o.id,
            name=o.name,
            is_active=o.is_active,
            created_at=o.created_at,
            updated_at=o.updated_at,
            phone_number=o.phone_number,
            users=[
                UserSummary(
                    id=u.id,
                    email=u.email or "unknown",
                    is_active=u.is_active
                ) for u in o.users
            ],
            stats=stats,
        ))

    # Sort by computed fields if requested
    if sort_by == "total_calls":
        response_orgs.sort(
            key=lambda x: x.stats.total_calls if x.stats else 0, 
            reverse=(sort_order == "desc")
        )
    elif sort_by == "user_count":
        response_orgs.sort(
            key=lambda x: x.stats.user_count if x.stats else 0,
            reverse=(sort_order == "desc")
        )
    elif sort_by == "last_activity":
        response_orgs.sort(
            key=lambda x: x.stats.last_activity or datetime.min,
            reverse=(sort_order == "desc")
        )

    return AdminOrganizationsListResponse(
        organizations=response_orgs,
        total_count=total_count,
        page=page,
        limit=limit,
        total_pages=total_pages,
    )


@router.get("/{org_id}", response_model=AdminOrganizationResponse)
async def get_organization_detail(
    org_id: int,
    user: UserModel = Depends(get_superuser),
):
    """Get detailed information for a specific organization."""
    async with async_session() as session:
        # Get organization with users
        org_result = await session.execute(
            select(OrganizationModel)
            .options(selectinload(OrganizationModel.users))
            .where(OrganizationModel.id == org_id)
        )
        organization = org_result.scalars().first()
        
        if not organization:
            raise HTTPException(status_code=404, detail="Organization not found")

        # Get comprehensive statistics
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        
        stats_query = text("""
            SELECT 
                COUNT(DISTINCT u.id) as user_count,
                COUNT(c.id) as total_calls,
                COALESCE(SUM(EXTRACT(EPOCH FROM (c.ended_at - c.started_at)) / 60.0), 0) as total_minutes,
                MAX(c.started_at) as last_activity,
                COUNT(CASE WHEN c.started_at >= :thirty_days_ago THEN 1 END) as calls_last_30_days,
                COALESCE(SUM(CASE WHEN c.started_at >= :thirty_days_ago 
                    THEN EXTRACT(EPOCH FROM (c.ended_at - c.started_at)) / 60.0 END), 0) as minutes_last_30_days,
                COUNT(w.id) as total_workflows,
                COUNT(CASE WHEN w.is_active THEN 1 END) as active_workflows
            FROM organizations o
            LEFT JOIN organization_users ou ON ou.organization_id = o.id
            LEFT JOIN users u ON u.id = ou.user_id
            LEFT JOIN calls c ON c.organization_id = o.id AND c.ended_at IS NOT NULL
            LEFT JOIN workflows w ON w.organization_id = o.id
            WHERE o.id = :org_id
            GROUP BY o.id
        """)
        
        stats_result = await session.execute(
            stats_query, 
            {"org_id": org_id, "thirty_days_ago": thirty_days_ago}
        )
        stats_row = stats_result.fetchone()
        
        if stats_row:
            total_calls = stats_row[1] or 0
            total_minutes = float(stats_row[2]) if stats_row[2] else 0.0
            avg_duration = (total_minutes / total_calls) if total_calls > 0 else 0.0
            
            stats = OrganizationStatsModel(
                user_count=stats_row[0] or 0,
                total_calls=total_calls,
                total_minutes=total_minutes,
                last_activity=stats_row[3],
                calls_last_30_days=stats_row[4] or 0,
                minutes_last_30_days=float(stats_row[5]) if stats_row[5] else 0.0,
                total_workflows=stats_row[6] or 0,
                active_workflows=stats_row[7] or 0,
                avg_call_duration=avg_duration,
            )
        else:
            stats = OrganizationStatsModel()

        return AdminOrganizationResponse(
            id=organization.id,
            name=organization.name,
            is_active=organization.is_active,
            created_at=organization.created_at,
            updated_at=organization.updated_at,
            phone_number=organization.phone_number,
            users=[
                UserSummary(
                    id=u.id,
                    email=u.email or "unknown",
                    is_active=u.is_active
                ) for u in organization.users
            ],
            stats=stats,
        )


@router.post("", response_model=AdminOrganizationResponse)
async def create_organization(
    create_data: CreateOrganizationRequest,
    user: UserModel = Depends(get_superuser),
):
    """Create a new organization."""
    async with async_session() as session:
        # Check if name already exists
        existing = await session.execute(
            select(OrganizationModel).where(OrganizationModel.name == create_data.name)
        )
        if existing.scalars().first():
            raise HTTPException(status_code=400, detail="Organization name already exists")

        # Create organization
        new_org = OrganizationModel(
            name=create_data.name,
            phone_number=create_data.phone_number,
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        
        session.add(new_org)
        await session.flush()  # Get the ID
        
        # Add owner if specified
        if create_data.owner_email:
            owner = await session.execute(
                select(UserModel).where(UserModel.email == create_data.owner_email)
            )
            owner_user = owner.scalars().first()
            if not owner_user:
                raise HTTPException(status_code=404, detail="Owner user not found")
            
            # Add to organization_users
            await session.execute(
                organization_users_association.insert().values(
                    organization_id=new_org.id,
                    user_id=owner_user.id
                )
            )

        await session.commit()
        
        return await get_organization_detail(new_org.id, user)


@router.patch("/{org_id}", response_model=AdminOrganizationResponse)
async def update_organization(
    org_id: int,
    update_data: UpdateOrganizationRequest,
    user: UserModel = Depends(get_superuser),
):
    """Update organization settings."""
    async with async_session() as session:
        # Check if organization exists
        org_result = await session.execute(
            select(OrganizationModel).where(OrganizationModel.id == org_id)
        )
        organization = org_result.scalars().first()
        
        if not organization:
            raise HTTPException(status_code=404, detail="Organization not found")

        # Check if new name conflicts
        if update_data.name and update_data.name != organization.name:
            existing = await session.execute(
                select(OrganizationModel).where(
                    OrganizationModel.name == update_data.name,
                    OrganizationModel.id != org_id
                )
            )
            if existing.scalars().first():
                raise HTTPException(status_code=400, detail="Organization name already exists")

        # Update fields
        update_fields = {}
        if update_data.name is not None:
            update_fields["name"] = update_data.name
        if update_data.is_active is not None:
            update_fields["is_active"] = update_data.is_active
        if update_data.phone_number is not None:
            update_fields["phone_number"] = update_data.phone_number
        
        if update_fields:
            update_fields["updated_at"] = datetime.utcnow()
            await session.execute(
                update(OrganizationModel)
                .where(OrganizationModel.id == org_id)
                .values(**update_fields)
            )
            await session.commit()

        return await get_organization_detail(org_id, user)


@router.delete("/{org_id}")
async def delete_organization(
    org_id: int,
    user: UserModel = Depends(get_superuser),
):
    """
    Delete an organization permanently. This will:
    1. Remove all users from the organization
    2. Delete all workflows and calls
    3. Delete the organization
    WARNING: This action cannot be undone.
    """
    async with async_session() as session:
        # Check if organization exists
        org_result = await session.execute(
            select(OrganizationModel).where(OrganizationModel.id == org_id)
        )
        organization = org_result.scalars().first()
        
        if not organization:
            raise HTTPException(status_code=404, detail="Organization not found")

        # Remove all users from organization
        await session.execute(
            delete(organization_users_association).where(
                organization_users_association.c.organization_id == org_id
            )
        )
        
        # Delete calls (workflows will cascade delete)
        await session.execute(
            delete(CallModel).where(CallModel.organization_id == org_id)
        )
        
        # Delete workflows
        await session.execute(
            delete(WorkflowModel).where(WorkflowModel.organization_id == org_id)
        )
        
        # Delete organization
        await session.execute(
            delete(OrganizationModel).where(OrganizationModel.id == org_id)
        )
        
        await session.commit()

    return {"message": f"Organization {organization.name} deleted successfully"}


@router.post("/{org_id}/users/{user_id}")
async def add_user_to_organization(
    org_id: int,
    user_id: int,
    user: UserModel = Depends(get_superuser),
):
    """Add a user to an organization."""
    async with async_session() as session:
        # Verify both exist
        org_exists = (await session.execute(
            select(func.count(OrganizationModel.id)).where(OrganizationModel.id == org_id)
        )).scalar_one()
        
        user_exists = (await session.execute(
            select(func.count(UserModel.id)).where(UserModel.id == user_id)
        )).scalar_one()
        
        if not org_exists:
            raise HTTPException(status_code=404, detail="Organization not found")
        if not user_exists:
            raise HTTPException(status_code=404, detail="User not found")

        # Check if already a member
        existing = (await session.execute(
            select(func.count()).where(
                organization_users_association.c.organization_id == org_id,
                organization_users_association.c.user_id == user_id
            )
        )).scalar_one()
        
        if existing:
            raise HTTPException(status_code=400, detail="User already in organization")

        # Add relationship
        await session.execute(
            organization_users_association.insert().values(
                organization_id=org_id,
                user_id=user_id
            )
        )
        await session.commit()

    return {"message": "User added to organization successfully"}


@router.delete("/{org_id}/users/{user_id}")
async def remove_user_from_organization(
    org_id: int,
    user_id: int,
    user: UserModel = Depends(get_superuser),
):
    """Remove a user from an organization."""
    async with async_session() as session:
        result = await session.execute(
            delete(organization_users_association).where(
                organization_users_association.c.organization_id == org_id,
                organization_users_association.c.user_id == user_id
            )
        )
        
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="User not in organization")
        
        await session.commit()

    return {"message": "User removed from organization successfully"}


@router.get("/stats/overview")
async def get_organizations_overview(user: UserModel = Depends(get_superuser)):
    """Get platform-wide organization statistics."""
    async with async_session() as session:
        # Basic counts
        total_orgs = (await session.execute(
            select(func.count(OrganizationModel.id))
        )).scalar_one()
        
        active_orgs = (await session.execute(
            select(func.count(OrganizationModel.id)).where(OrganizationModel.is_active == True)
        )).scalar_one()

        # Recent activity
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        
        new_orgs_30d = (await session.execute(
            select(func.count(OrganizationModel.id)).where(
                OrganizationModel.created_at >= thirty_days_ago
            )
        )).scalar_one()
        
        new_orgs_7d = (await session.execute(
            select(func.count(OrganizationModel.id)).where(
                OrganizationModel.created_at >= seven_days_ago
            )
        )).scalar_one()

        # Organizations with activity
        active_orgs_30d_query = text("""
            SELECT COUNT(DISTINCT c.organization_id)
            FROM calls c
            WHERE c.started_at >= :thirty_days_ago
        """)
        
        active_orgs_30d = (await session.execute(
            active_orgs_30d_query, {"thirty_days_ago": thirty_days_ago}
        )).scalar_one()

        return {
            "total_organizations": total_orgs,
            "active_organizations": active_orgs,
            "inactive_organizations": total_orgs - active_orgs,
            "new_organizations_30_days": new_orgs_30d,
            "new_organizations_7_days": new_orgs_7d,
            "organizations_with_activity_30_days": active_orgs_30d or 0,
            "growth_rate_30d": (new_orgs_30d / max(total_orgs - new_orgs_30d, 1)) * 100,
        }
