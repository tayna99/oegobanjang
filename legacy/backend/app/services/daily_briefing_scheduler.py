from __future__ import annotations

import threading
from datetime import datetime
from typing import Callable, Iterable
from zoneinfo import ZoneInfo

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.services.daily_briefing_service import build_sqlalchemy_daily_briefing_service


class ScheduledDailyBriefingError(BaseModel):
    company_id: str
    error_code: str
    message: str


class ScheduledDailyBriefingRun(BaseModel):
    status: str
    run_date: str
    total_companies: int
    succeeded_count: int
    failed_count: int
    briefing_run_ids: list[str] = Field(default_factory=list)
    errors: list[ScheduledDailyBriefingError] = Field(default_factory=list)


class DailyBriefingBackgroundScheduler:
    def __init__(
        self,
        session_factory: Callable[[], Session],
        *,
        interval_seconds: int = 86400,
        company_ids: Iterable[str] | None = None,
        timezone_name: str = "Asia/Seoul",
    ) -> None:
        self.session_factory = session_factory
        self.interval_seconds = max(interval_seconds, 60)
        self.company_ids = list(company_ids) if company_ids is not None else None
        self.timezone_name = timezone_name
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self.last_run: ScheduledDailyBriefingRun | None = None

    def start(self, *, run_immediately: bool = False) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._loop,
            args=(run_immediately,),
            name="daily-briefing-scheduler",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)

    def run_once(self, *, run_date: str | None = None) -> ScheduledDailyBriefingRun:
        db = self.session_factory()
        try:
            self.last_run = run_scheduled_daily_briefings(
                db,
                company_ids=self.company_ids,
                run_date=run_date,
                timezone_name=self.timezone_name,
            )
            return self.last_run
        finally:
            db.close()

    def _loop(self, run_immediately: bool) -> None:
        if run_immediately:
            self.run_once()
        while not self._stop_event.wait(self.interval_seconds):
            self.run_once()


def run_scheduled_daily_briefings(
    db: Session,
    *,
    company_ids: Iterable[str] | None = None,
    run_date: str | None = None,
    timezone_name: str = "Asia/Seoul",
) -> ScheduledDailyBriefingRun:
    """Run the same Daily Briefing service from a scheduler-safe entrypoint.

    The scheduler never sends messages or external handoffs. It only creates
    briefing results, pending actions, evidence events, and previews through
    the existing Daily Briefing service.
    """

    service = build_sqlalchemy_daily_briefing_service(db)
    target_date = run_date or datetime.now(ZoneInfo(timezone_name)).date().isoformat()
    selected_company_ids = list(company_ids or sorted(service.repository.companies.keys()))

    briefing_run_ids: list[str] = []
    errors: list[ScheduledDailyBriefingError] = []

    for company_id in selected_company_ids:
        try:
            result = service.run_daily_briefing(
                company_id=company_id,
                date=target_date,
                user_role="system",
                allowed_company_ids=None,
            )
            db.commit()
            briefing_run_ids.append(result.briefing_run_id)
        except LookupError as exc:
            db.rollback()
            errors.append(
                ScheduledDailyBriefingError(
                    company_id=company_id,
                    error_code="COMPANY_NOT_FOUND",
                    message=str(exc.args[0]) if exc.args else "Company context was not found.",
                )
            )
        except Exception as exc:
            db.rollback()
            errors.append(
                ScheduledDailyBriefingError(
                    company_id=company_id,
                    error_code=str(exc.args[0]) if exc.args else "SCHEDULED_BRIEFING_FAILED",
                    message="Scheduled Daily Briefing failed safely.",
                )
            )

    failed_count = len(errors)
    succeeded_count = len(briefing_run_ids)
    if failed_count == 0:
        status = "completed"
    elif succeeded_count == 0:
        status = "failed"
    else:
        status = "partial_failure"

    return ScheduledDailyBriefingRun(
        status=status,
        run_date=target_date,
        total_companies=len(selected_company_ids),
        succeeded_count=succeeded_count,
        failed_count=failed_count,
        briefing_run_ids=briefing_run_ids,
        errors=errors,
    )
