"""
Admin Analytics Routes
Real-time platform analytics with database-driven KPIs.
"""
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, select, text, desc
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from api.constants import DATABASE_URL
from api.db.models import (
    UserModel, 
    OrganizationModel, 
    WorkflowModel,
    CallModel,
    organization_users_association
)
from api.services.auth.depends import get_superuser

router = APIRouter(prefix="/admin/analytics", tags=["admin-analytics"])

engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
async_session = async_sessionmaker(bind=engine)


class DashboardKPI(BaseModel):
    title: str
    value: str | int | float
    change: Optional[str] = None
    trend: Optional[str] = None  # "up", "down", "neutral"
    icon: Optional[str] = None


class TimeSeriesDataPoint(BaseModel):
    date: str
    value: int | float


class TopItem(BaseModel):
    name: str
    value: int | float
    percentage: Optional[float] = None


class AnalyticsDashboard(BaseModel):
    kpis: List[DashboardKPI]
    calls_timeline: List[TimeSeriesDataPoint]
    users_timeline: List[TimeSeriesDataPoint]
    top_organizations: List[TopItem]
    recent_activity: List[Dict[str, Any]]


@router.get("/dashboard", response_model=AnalyticsDashboard)
async def get_analytics_dashboard(
    days: int = Query(30, ge=7, le=365),
    user: UserModel = Depends(get_superuser)
):
    """Get comprehensive platform analytics dashboard."""
    
    async with async_session() as session:
        now = datetime.utcnow()
        period_start = now - timedelta(days=days)
        prev_period_start = period_start - timedelta(days=days)
        
        # === KPI CALCULATIONS ===
        
        # Total Users (current vs previous period)
        total_users = (await session.execute(
            select(func.count(UserModel.id))
        )).scalar_one()
        
        users_prev_period = (await session.execute(
            select(func.count(UserModel.id)).where(
                UserModel.created_at < period_start
            )
        )).scalar_one()
        
        user_growth = total_users - users_prev_period
        user_growth_pct = (user_growth / max(users_prev_period, 1)) * 100
        
        # Total Organizations
        total_orgs = (await session.execute(
            select(func.count(OrganizationModel.id))
        )).scalar_one()
        
        orgs_prev_period = (await session.execute(
            select(func.count(OrganizationModel.id)).where(
                OrganizationModel.created_at < period_start
            )
        )).scalar_one()
        
        org_growth = total_orgs - orgs_prev_period
        org_growth_pct = (org_growth / max(orgs_prev_period, 1)) * 100
        
        # Total Calls (current period)
        calls_query = text("""
            SELECT 
                COUNT(*) as total_calls,
                COALESCE(SUM(EXTRACT(EPOCH FROM (ended_at - started_at)) / 60.0), 0) as total_minutes
            FROM calls 
            WHERE started_at >= :period_start AND ended_at IS NOT NULL
        """)
        
        calls_result = await session.execute(calls_query, {"period_start": period_start})
        calls_row = calls_result.fetchone()
        total_calls = calls_row[0] if calls_row else 0
        total_minutes = float(calls_row[1]) if calls_row else 0.0
        
        # Previous period calls for comparison
        prev_calls_result = await session.execute(
            calls_query, 
            {"period_start": prev_period_start, "period_end": period_start}
        )
        prev_calls_row = prev_calls_result.fetchone()
        prev_calls = prev_calls_row[0] if prev_calls_row else 0
        
        calls_growth_pct = ((total_calls - prev_calls) / max(prev_calls, 1)) * 100 if prev_calls > 0 else 0
        
        # Active Organizations (made calls in period)
        active_orgs = (await session.execute(text("""
            SELECT COUNT(DISTINCT organization_id)
            FROM calls 
            WHERE started_at >= :period_start
        """), {"period_start": period_start})).scalar_one()
        
        # Average Call Duration
        avg_duration = total_minutes / total_calls if total_calls > 0 else 0
        
        # === TIME SERIES DATA ===
        
        # Daily calls for the period
        calls_timeline_query = text("""
            SELECT 
                DATE(started_at) as call_date,
                COUNT(*) as daily_calls
            FROM calls 
            WHERE started_at >= :period_start AND ended_at IS NOT NULL
            GROUP BY DATE(started_at)
            ORDER BY call_date
        """)
        
        calls_timeline_result = await session.execute(
            calls_timeline_query, {"period_start": period_start}
        )
        
        calls_timeline = []
        for row in calls_timeline_result:
            calls_timeline.append(TimeSeriesDataPoint(
                date=row[0].strftime("%Y-%m-%d"),
                value=row[1]
            ))
        
        # Daily user registrations
        users_timeline_query = text("""
            SELECT 
                DATE(created_at) as reg_date,
                COUNT(*) as daily_users
            FROM users 
            WHERE created_at >= :period_start
            GROUP BY DATE(created_at)
            ORDER BY reg_date
        """)
        
        users_timeline_result = await session.execute(
            users_timeline_query, {"period_start": period_start}
        )
        
        users_timeline = []
        for row in users_timeline_result:
            users_timeline.append(TimeSeriesDataPoint(
                date=row[0].strftime("%Y-%m-%d"),
                value=row[1]
            ))
        
        # === TOP ORGANIZATIONS ===
        
        top_orgs_query = text("""
            SELECT 
                o.name,
                COUNT(c.id) as call_count,
                COALESCE(SUM(EXTRACT(EPOCH FROM (c.ended_at - c.started_at)) / 60.0), 0) as total_minutes
            FROM organizations o
            LEFT JOIN calls c ON c.organization_id = o.id 
                AND c.started_at >= :period_start 
                AND c.ended_at IS NOT NULL
            GROUP BY o.id, o.name
            ORDER BY call_count DESC
            LIMIT 10
        """)
        
        top_orgs_result = await session.execute(
            top_orgs_query, {"period_start": period_start}
        )
        
        top_organizations = []
        for row in top_orgs_result:
            if row[1] > 0:  # Only include orgs with calls
                percentage = (row[1] / total_calls * 100) if total_calls > 0 else 0
                top_organizations.append(TopItem(
                    name=row[0],
                    value=row[1],
                    percentage=percentage
                ))
        
        # === RECENT ACTIVITY ===
        
        recent_activity_query = text("""
            SELECT 
                'call' as activity_type,
                c.started_at as timestamp,
                o.name as organization_name,
                EXTRACT(EPOCH FROM (c.ended_at - c.started_at)) / 60.0 as duration_minutes
            FROM calls c
            JOIN organizations o ON o.id = c.organization_id
            WHERE c.started_at >= :recent_time AND c.ended_at IS NOT NULL
            
            UNION ALL
            
            SELECT 
                'user_registered' as activity_type,
                u.created_at as timestamp,
                '' as organization_name,
                0 as duration_minutes
            FROM users u
            WHERE u.created_at >= :recent_time
            
            UNION ALL
            
            SELECT 
                'organization_created' as activity_type,
                o.created_at as timestamp,
                o.name as organization_name,
                0 as duration_minutes
            FROM organizations o
            WHERE o.created_at >= :recent_time
            
            ORDER BY timestamp DESC
            LIMIT 20
        """)
        
        recent_time = now - timedelta(hours=24)
        recent_activity_result = await session.execute(
            recent_activity_query, {"recent_time": recent_time}
        )
        
        recent_activity = []
        for row in recent_activity_result:
            activity = {
                "type": row[0],
                "timestamp": row[1].isoformat(),
                "organization": row[2] if row[2] else None,
            }
            if row[0] == "call" and row[3]:
                activity["duration"] = f"{row[3]:.1f} min"
            recent_activity.append(activity)
        
        # === BUILD RESPONSE ===
        
        kpis = [
            DashboardKPI(
                title="Total Users",
                value=total_users,
                change=f"+{user_growth}" if user_growth > 0 else str(user_growth),
                trend="up" if user_growth > 0 else "neutral",
                icon="users"
            ),
            DashboardKPI(
                title="Total Organizations", 
                value=total_orgs,
                change=f"+{org_growth}" if org_growth > 0 else str(org_growth),
                trend="up" if org_growth > 0 else "neutral",
                icon="building"
            ),
            DashboardKPI(
                title="Calls This Period",
                value=total_calls,
                change=f"+{calls_growth_pct:.1f}%" if calls_growth_pct > 0 else f"{calls_growth_pct:.1f}%",
                trend="up" if calls_growth_pct > 0 else "down" if calls_growth_pct < 0 else "neutral",
                icon="phone"
            ),
            DashboardKPI(
                title="Total Minutes",
                value=f"{total_minutes:,.0f}",
                change=None,
                trend="neutral",
                icon="clock"
            ),
            DashboardKPI(
                title="Active Organizations",
                value=active_orgs,
                change=f"{(active_orgs / max(total_orgs, 1) * 100):.1f}% of total",
                trend="neutral",
                icon="activity"
            ),
            DashboardKPI(
                title="Avg Call Duration",
                value=f"{avg_duration:.1f} min",
                change=None,
                trend="neutral",
                icon="timer"
            ),
        ]
        
        return AnalyticsDashboard(
            kpis=kpis,
            calls_timeline=calls_timeline,
            users_timeline=users_timeline,
            top_organizations=top_organizations,
            recent_activity=recent_activity
        )


@router.get("/calls/stats")
async def get_call_statistics(
    days: int = Query(30, ge=1, le=365),
    organization_id: Optional[int] = Query(None),
    user: UserModel = Depends(get_superuser)
):
    """Get detailed call statistics with optional organization filtering."""
    
    async with async_session() as session:
        period_start = datetime.utcnow() - timedelta(days=days)
        
        # Build base query with optional org filter
        base_conditions = "started_at >= :period_start AND ended_at IS NOT NULL"
        params = {"period_start": period_start}
        
        if organization_id:
            base_conditions += " AND organization_id = :org_id"
            params["org_id"] = organization_id
        
        # Overall statistics
        stats_query = text(f"""
            SELECT 
                COUNT(*) as total_calls,
                COUNT(DISTINCT organization_id) as unique_orgs,
                COALESCE(SUM(EXTRACT(EPOCH FROM (ended_at - started_at)) / 60.0), 0) as total_minutes,
                COALESCE(AVG(EXTRACT(EPOCH FROM (ended_at - started_at)) / 60.0), 0) as avg_duration,
                MIN(EXTRACT(EPOCH FROM (ended_at - started_at)) / 60.0) as min_duration,
                MAX(EXTRACT(EPOCH FROM (ended_at - started_at)) / 60.0) as max_duration
            FROM calls 
            WHERE {base_conditions}
        """)
        
        stats_result = await session.execute(stats_query, params)
        stats_row = stats_result.fetchone()
        
        # Call distribution by hour of day
        hourly_query = text(f"""
            SELECT 
                EXTRACT(HOUR FROM started_at) as hour,
                COUNT(*) as call_count
            FROM calls 
            WHERE {base_conditions}
            GROUP BY EXTRACT(HOUR FROM started_at)
            ORDER BY hour
        """)
        
        hourly_result = await session.execute(hourly_query, params)
        hourly_distribution = [{"hour": int(row[0]), "calls": row[1]} for row in hourly_result]
        
        # Call distribution by day of week
        daily_query = text(f"""
            SELECT 
                EXTRACT(DOW FROM started_at) as dow,
                COUNT(*) as call_count
            FROM calls 
            WHERE {base_conditions}
            GROUP BY EXTRACT(DOW FROM started_at)
            ORDER BY dow
        """)
        
        daily_result = await session.execute(daily_query, params)
        daily_distribution = []
        day_names = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
        for row in daily_result:
            daily_distribution.append({
                "day": day_names[int(row[0])],
                "calls": row[1]
            })
        
        return {
            "period_days": days,
            "organization_id": organization_id,
            "summary": {
                "total_calls": stats_row[0] if stats_row else 0,
                "unique_organizations": stats_row[1] if stats_row else 0,
                "total_minutes": float(stats_row[2]) if stats_row else 0.0,
                "average_duration_minutes": float(stats_row[3]) if stats_row else 0.0,
                "min_duration_minutes": float(stats_row[4]) if stats_row else 0.0,
                "max_duration_minutes": float(stats_row[5]) if stats_row else 0.0,
            },
            "distribution": {
                "by_hour": hourly_distribution,
                "by_day_of_week": daily_distribution,
            }
        }


@router.get("/usage/trends")
async def get_usage_trends(
    days: int = Query(90, ge=30, le=365),
    user: UserModel = Depends(get_superuser)
):
    """Get platform usage trends over time."""
    
    async with async_session() as session:
        period_start = datetime.utcnow() - timedelta(days=days)
        
        # Weekly usage trends
        trends_query = text("""
            SELECT 
                DATE_TRUNC('week', started_at) as week_start,
                COUNT(*) as calls,
                COUNT(DISTINCT organization_id) as active_orgs,
                COALESCE(SUM(EXTRACT(EPOCH FROM (ended_at - started_at)) / 60.0), 0) as total_minutes
            FROM calls 
            WHERE started_at >= :period_start AND ended_at IS NOT NULL
            GROUP BY DATE_TRUNC('week', started_at)
            ORDER BY week_start
        """)
        
        trends_result = await session.execute(trends_query, {"period_start": period_start})
        
        weekly_trends = []
        for row in trends_result:
            weekly_trends.append({
                "week": row[0].strftime("%Y-%m-%d"),
                "calls": row[1],
                "active_organizations": row[2],
                "total_minutes": float(row[3])
            })
        
        # Growth metrics
        if len(weekly_trends) >= 2:
            latest_week = weekly_trends[-1]
            prev_week = weekly_trends[-2]
            
            call_growth = ((latest_week["calls"] - prev_week["calls"]) / max(prev_week["calls"], 1)) * 100
            org_growth = ((latest_week["active_organizations"] - prev_week["active_organizations"]) / max(prev_week["active_organizations"], 1)) * 100
            
            growth_metrics = {
                "weekly_call_growth_percent": call_growth,
                "weekly_org_growth_percent": org_growth,
            }
        else:
            growth_metrics = {
                "weekly_call_growth_percent": 0,
                "weekly_org_growth_percent": 0,
            }
        
        return {
            "period_days": days,
            "weekly_trends": weekly_trends,
            "growth_metrics": growth_metrics
        }
