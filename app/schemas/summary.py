from datetime import date
from typing import List

from pydantic import BaseModel


class CategoryCount(BaseModel):
    category_id: int
    category_name: str
    count: int
    total_minutes: int = 0


class CategoryInfo(BaseModel):
    id: int
    name: str


class UserReportStatus(BaseModel):
    user_id: int
    display_name: str
    report_count: int
    has_report_today: bool
    category_breakdown: List[CategoryCount]


class ReportTrend(BaseModel):
    date: date
    count: int
    category_breakdown: List[CategoryCount]


class CategoryTrend(BaseModel):
    category_id: int
    category_name: str
    report_count: int
    total_minutes: int


class RecentReportSummary(BaseModel):
    id: int
    user_id: int
    display_name: str
    report_date: date
    work_content_preview: str


class BusinessSummaryResponse(BaseModel):
    period_start: date
    period_end: date
    period: str
    total_reports: int
    categories: List[CategoryInfo]
    user_report_statuses: List[UserReportStatus]
    report_trends: List[ReportTrend]
    category_trends: List[CategoryTrend]
    recent_reports: List[RecentReportSummary]
    issues: List[str]
