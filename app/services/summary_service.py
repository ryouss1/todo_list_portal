import logging
from collections import Counter, defaultdict
from datetime import date, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.crud import daily_report as crud_report
from app.crud import user as crud_user
from app.models.task_category import TaskCategory
from app.schemas.summary import (
    BusinessSummaryResponse,
    CategoryCount,
    CategoryInfo,
    CategoryTrend,
    RecentReportSummary,
    ReportTrend,
    UserReportStatus,
)

logger = logging.getLogger("app.services.summary")


def get_day_range(ref_date: date):
    return ref_date, ref_date


def get_week_range(ref_date: date):
    start = ref_date - timedelta(days=ref_date.weekday())
    end = start + timedelta(days=6)
    return start, end


def get_month_range(ref_date: date):
    start = ref_date.replace(day=1)
    if ref_date.month == 12:
        end = ref_date.replace(year=ref_date.year + 1, month=1, day=1) - timedelta(days=1)
    else:
        end = ref_date.replace(month=ref_date.month + 1, day=1) - timedelta(days=1)
    return start, end


def get_summary(db: Session, period: str, ref_date: date, group_id: Optional[int] = None) -> BusinessSummaryResponse:
    logger.info("Generating %s summary for ref_date=%s, group_id=%s", period, ref_date, group_id)

    if period == "daily":
        period_start, period_end = get_day_range(ref_date)
    elif period == "weekly":
        period_start, period_end = get_week_range(ref_date)
    else:
        period_start, period_end = get_month_range(ref_date)

    all_reports = crud_report.get_reports_by_date_range(db, period_start, period_end)
    users = crud_user.get_users(db)

    # Filter by group if specified
    if group_id is not None:
        users = [u for u in users if u.group_id == group_id]
        target_user_ids = {u.id for u in users}
        reports = [r for r in all_reports if r.user_id in target_user_ids]
    else:
        reports = all_reports

    # Build categories list (used by user_report_statuses, report_trends, and response)
    all_categories = db.query(TaskCategory).order_by(TaskCategory.id).all()
    categories = {c.id: c.name for c in all_categories}
    categories_list = [CategoryInfo(id=c.id, name=c.name) for c in all_categories]

    user_map = {u.id: u.display_name for u in users}
    today = date.today()

    # Per-user category counts and minutes
    user_report_counts = Counter(r.user_id for r in reports)
    user_has_today = set(r.user_id for r in reports if r.report_date == today)
    user_cat_counts: dict = defaultdict(Counter)
    user_cat_minutes: dict = defaultdict(lambda: defaultdict(int))
    for r in reports:
        user_cat_counts[r.user_id][r.category_id] += 1
        user_cat_minutes[r.user_id][r.category_id] += r.time_minutes or 0

    user_report_statuses = [
        UserReportStatus(
            user_id=u.id,
            display_name=u.display_name,
            report_count=user_report_counts.get(u.id, 0),
            has_report_today=u.id in user_has_today,
            category_breakdown=[
                CategoryCount(
                    category_id=c.id,
                    category_name=c.name,
                    count=user_cat_counts[u.id].get(c.id, 0),
                    total_minutes=user_cat_minutes[u.id].get(c.id, 0),
                )
                for c in all_categories
            ],
        )
        for u in users
    ]

    # Per-date category counts and minutes
    date_counts = Counter(r.report_date for r in reports)
    date_cat_counts: dict = defaultdict(Counter)
    date_cat_minutes: dict = defaultdict(lambda: defaultdict(int))
    for r in reports:
        date_cat_counts[r.report_date][r.category_id] += 1
        date_cat_minutes[r.report_date][r.category_id] += r.time_minutes or 0

    report_trends = sorted(
        [
            ReportTrend(
                date=d,
                count=c,
                category_breakdown=[
                    CategoryCount(
                        category_id=cid,
                        category_name=categories.get(cid, "Unknown"),
                        count=cnt,
                        total_minutes=date_cat_minutes[d].get(cid, 0),
                    )
                    for cid, cnt in date_cat_counts[d].items()
                    if cnt > 0
                ],
            )
            for d, c in date_counts.items()
        ],
        key=lambda x: x.date,
    )
    cat_stats = {}
    for r in reports:
        cid = r.category_id
        if cid not in cat_stats:
            cat_stats[cid] = {"count": 0, "minutes": 0}
        cat_stats[cid]["count"] += 1
        cat_stats[cid]["minutes"] += r.time_minutes or 0
    category_trends = sorted(
        [
            CategoryTrend(
                category_id=cid,
                category_name=categories.get(cid, "Unknown"),
                report_count=stats["count"],
                total_minutes=stats["minutes"],
            )
            for cid, stats in cat_stats.items()
        ],
        key=lambda x: x.total_minutes,
        reverse=True,
    )

    recent_reports = [
        RecentReportSummary(
            id=r.id,
            user_id=r.user_id,
            display_name=user_map.get(r.user_id, "Unknown"),
            report_date=r.report_date,
            work_content_preview=r.work_content[:100] if r.work_content else "",
        )
        for r in reports[:10]
    ]

    issues = []
    for r in reports:
        if r.issues and r.issues.strip():
            issues.append(f"[{r.report_date}] {user_map.get(r.user_id, 'Unknown')}: {r.issues.strip()}")

    return BusinessSummaryResponse(
        period_start=period_start,
        period_end=period_end,
        period=period,
        total_reports=len(reports),
        categories=categories_list,
        user_report_statuses=user_report_statuses,
        report_trends=report_trends,
        category_trends=category_trends,
        recent_reports=recent_reports,
        issues=issues,
    )
