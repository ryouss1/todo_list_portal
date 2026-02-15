from datetime import date, timedelta

from app.models.daily_report import DailyReport
from app.models.group import Group
from app.models.task_category import TaskCategory
from app.models.user import User


def _ensure_category(db_session, category_id=7, name="その他"):
    cat = db_session.query(TaskCategory).filter(TaskCategory.id == category_id).first()
    if not cat:
        cat = TaskCategory(id=category_id, name=name)
        db_session.add(cat)
        db_session.flush()
    return cat


class TestSummaryAPI:
    def test_summary_empty(self, client):
        # Use a past date range with no data to avoid stale DB interference
        resp = client.get("/api/summary/?period=weekly&ref_date=2020-01-06")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_reports"] == 0
        assert data["period"] == "weekly"
        assert isinstance(data["user_report_statuses"], list)
        assert isinstance(data["report_trends"], list)
        assert isinstance(data["recent_reports"], list)
        assert isinstance(data["issues"], list)

    def test_summary_weekly(self, client, db_session):
        _ensure_category(db_session)
        today = date.today()
        report = DailyReport(
            user_id=1, report_date=today, category_id=7, task_name="Task", time_minutes=0, work_content="Today's work"
        )
        db_session.add(report)
        db_session.flush()

        resp = client.get(f"/api/summary/?period=weekly&ref_date={today.isoformat()}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_reports"] >= 1
        assert data["period"] == "weekly"

    def test_summary_monthly(self, client, db_session):
        _ensure_category(db_session)
        today = date.today()
        report = DailyReport(
            user_id=1, report_date=today, category_id=7, task_name="Task", time_minutes=0, work_content="Monthly work"
        )
        db_session.add(report)
        db_session.flush()

        resp = client.get(f"/api/summary/?period=monthly&ref_date={today.isoformat()}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_reports"] >= 1
        assert data["period"] == "monthly"

    def test_summary_has_user_statuses(self, client, db_session):
        _ensure_category(db_session)
        today = date.today()
        report = DailyReport(
            user_id=1, report_date=today, category_id=7, task_name="Task", time_minutes=0, work_content="Work"
        )
        db_session.add(report)
        db_session.flush()

        resp = client.get(f"/api/summary/?period=weekly&ref_date={today.isoformat()}")
        data = resp.json()
        assert len(data["user_report_statuses"]) >= 1
        user1 = [u for u in data["user_report_statuses"] if u["user_id"] == 1]
        assert len(user1) == 1
        assert user1[0]["report_count"] >= 1
        assert user1[0]["display_name"] == "Default User"

    def test_summary_has_issues(self, client, db_session):
        _ensure_category(db_session)
        today = date.today()
        report = DailyReport(
            user_id=1,
            report_date=today,
            category_id=7,
            task_name="Task",
            time_minutes=0,
            work_content="Work",
            issues="Bug found in login",
        )
        db_session.add(report)
        db_session.flush()

        resp = client.get(f"/api/summary/?period=weekly&ref_date={today.isoformat()}")
        data = resp.json()
        assert len(data["issues"]) >= 1
        assert "Bug found in login" in data["issues"][0]

    def test_summary_category_trends(self, client, db_session):
        _ensure_category(db_session, category_id=1, name="開発")
        _ensure_category(db_session, category_id=2, name="設計")
        today = date.today()
        db_session.add(
            DailyReport(
                user_id=1, report_date=today, category_id=1, task_name="Dev", time_minutes=120, work_content="W"
            )
        )
        db_session.add(
            DailyReport(
                user_id=1,
                report_date=today - timedelta(days=1),
                category_id=2,
                task_name="Design",
                time_minutes=60,
                work_content="W",
            )
        )
        db_session.flush()

        resp = client.get(f"/api/summary/?period=weekly&ref_date={today.isoformat()}")
        data = resp.json()
        assert "category_trends" in data
        assert len(data["category_trends"]) >= 2
        # Sorted by total_minutes desc — 開発(120) first
        names = [c["category_name"] for c in data["category_trends"]]
        assert "開発" in names
        assert "設計" in names
        dev = [c for c in data["category_trends"] if c["category_name"] == "開発"][0]
        assert dev["total_minutes"] == 120
        assert dev["report_count"] >= 1

    def test_user_report_status_category_breakdown(self, client, db_session):
        _ensure_category(db_session, category_id=1, name="開発")
        _ensure_category(db_session, category_id=2, name="設計")
        # Use a past date range to avoid stale data interference
        ref = date(2020, 1, 6)  # Monday
        db_session.add(
            DailyReport(user_id=1, report_date=ref, category_id=1, task_name="Dev1", time_minutes=60, work_content="W")
        )
        db_session.add(
            DailyReport(
                user_id=1,
                report_date=ref + timedelta(days=1),
                category_id=1,
                task_name="Dev2",
                time_minutes=60,
                work_content="W",
            )
        )
        db_session.add(
            DailyReport(
                user_id=1,
                report_date=ref + timedelta(days=2),
                category_id=2,
                task_name="Design1",
                time_minutes=30,
                work_content="W",
            )
        )
        db_session.flush()

        resp = client.get(f"/api/summary/?period=weekly&ref_date={ref.isoformat()}")
        data = resp.json()
        user1 = [u for u in data["user_report_statuses"] if u["user_id"] == 1][0]
        assert "category_breakdown" in user1
        dev_bd = [b for b in user1["category_breakdown"] if b["category_id"] == 1]
        assert len(dev_bd) == 1
        assert dev_bd[0]["count"] == 2
        assert dev_bd[0]["total_minutes"] == 120
        design_bd = [b for b in user1["category_breakdown"] if b["category_id"] == 2]
        assert len(design_bd) == 1
        assert design_bd[0]["count"] == 1
        assert design_bd[0]["total_minutes"] == 30

    def test_report_trends_category_breakdown(self, client, db_session):
        _ensure_category(db_session, category_id=1, name="開発")
        _ensure_category(db_session, category_id=2, name="設計")
        # Use a past date range to avoid stale data interference
        ref = date(2020, 2, 3)  # Monday
        db_session.add(
            DailyReport(user_id=1, report_date=ref, category_id=1, task_name="Dev", time_minutes=60, work_content="W")
        )
        db_session.add(
            DailyReport(
                user_id=1, report_date=ref, category_id=2, task_name="Design", time_minutes=30, work_content="W"
            )
        )
        db_session.flush()

        resp = client.get(f"/api/summary/?period=weekly&ref_date={ref.isoformat()}")
        data = resp.json()
        ref_trend = [t for t in data["report_trends"] if t["date"] == ref.isoformat()]
        assert len(ref_trend) == 1
        bd = ref_trend[0]["category_breakdown"]
        assert len(bd) == 2
        dev_bd = [b for b in bd if b["category_id"] == 1]
        assert len(dev_bd) == 1
        assert dev_bd[0]["count"] == 1
        design_bd = [b for b in bd if b["category_id"] == 2]
        assert len(design_bd) == 1
        assert design_bd[0]["count"] == 1

    def test_summary_includes_categories_list(self, client, db_session):
        _ensure_category(db_session, category_id=1, name="開発")
        _ensure_category(db_session, category_id=2, name="設計")

        resp = client.get("/api/summary/")
        data = resp.json()
        assert "categories" in data
        assert isinstance(data["categories"], list)
        cat_ids = [c["id"] for c in data["categories"]]
        assert 1 in cat_ids
        assert 2 in cat_ids
        cat1 = [c for c in data["categories"] if c["id"] == 1][0]
        assert cat1["name"] == "開発"

    def test_summary_daily(self, client, db_session):
        _ensure_category(db_session)
        today = date.today()
        db_session.add(
            DailyReport(
                user_id=1, report_date=today, category_id=7, task_name="Task", time_minutes=30, work_content="Daily"
            )
        )
        db_session.flush()

        resp = client.get(f"/api/summary/?period=daily&ref_date={today.isoformat()}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["period"] == "daily"
        assert data["period_start"] == today.isoformat()
        assert data["period_end"] == today.isoformat()
        assert data["total_reports"] >= 1

    def test_summary_daily_no_adjacent_dates(self, client, db_session):
        _ensure_category(db_session)
        ref = date(2020, 3, 10)
        db_session.add(
            DailyReport(user_id=1, report_date=ref, category_id=7, task_name="T", time_minutes=10, work_content="W")
        )
        db_session.add(
            DailyReport(
                user_id=1,
                report_date=ref + timedelta(days=1),
                category_id=7,
                task_name="T2",
                time_minutes=20,
                work_content="W2",
            )
        )
        db_session.flush()

        resp = client.get(f"/api/summary/?period=daily&ref_date={ref.isoformat()}")
        data = resp.json()
        assert data["total_reports"] == 1
        assert data["period_start"] == ref.isoformat()
        assert data["period_end"] == ref.isoformat()

    def test_summary_invalid_period(self, client):
        resp = client.get("/api/summary/?period=yearly")
        assert resp.status_code == 422

    def test_summary_group_filter(self, client, db_session, other_user):
        """group_id指定でそのグループのユーザーのみ集計される."""
        _ensure_category(db_session)
        # Create a group and assign user 1 to it
        group = Group(name="FilterGroup", sort_order=99)
        db_session.add(group)
        db_session.flush()
        user1 = db_session.query(User).filter(User.id == 1).first()
        user1.group_id = group.id
        other_user.group_id = None
        db_session.flush()

        ref = date(2020, 4, 6)  # Monday
        db_session.add(
            DailyReport(user_id=1, report_date=ref, category_id=7, task_name="T1", time_minutes=30, work_content="W1")
        )
        db_session.add(
            DailyReport(user_id=2, report_date=ref, category_id=7, task_name="T2", time_minutes=20, work_content="W2")
        )
        db_session.flush()

        # With group filter: only user1's report
        resp = client.get(f"/api/summary/?period=weekly&ref_date={ref.isoformat()}&group_id={group.id}")
        data = resp.json()
        assert data["total_reports"] == 1
        user_ids = [u["user_id"] for u in data["user_report_statuses"]]
        assert 1 in user_ids
        assert 2 not in user_ids

    def test_summary_group_filter_empty(self, client, db_session):
        """所属ユーザーがいないグループではtotal_reports=0."""
        group = Group(name="EmptyGroup", sort_order=99)
        db_session.add(group)
        db_session.flush()

        ref = date(2020, 5, 4)
        resp = client.get(f"/api/summary/?period=weekly&ref_date={ref.isoformat()}&group_id={group.id}")
        data = resp.json()
        assert data["total_reports"] == 0
        assert data["user_report_statuses"] == []

    def test_summary_no_group_filter(self, client, db_session, other_user):
        """group_id未指定で全ユーザー集計（後方互換）."""
        _ensure_category(db_session)
        ref = date(2020, 6, 1)
        db_session.add(
            DailyReport(user_id=1, report_date=ref, category_id=7, task_name="T1", time_minutes=10, work_content="W")
        )
        db_session.add(
            DailyReport(user_id=2, report_date=ref, category_id=7, task_name="T2", time_minutes=10, work_content="W")
        )
        db_session.flush()

        resp = client.get(f"/api/summary/?period=weekly&ref_date={ref.isoformat()}")
        data = resp.json()
        assert data["total_reports"] >= 2
        user_ids = [u["user_id"] for u in data["user_report_statuses"]]
        assert 1 in user_ids
        assert 2 in user_ids
