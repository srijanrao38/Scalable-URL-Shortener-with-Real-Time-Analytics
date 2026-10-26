"""SQL aggregation helpers for link analytics."""

from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Click, Link


def find_link(db: Session, code: str) -> Link | None:
    return db.scalar(select(Link).where(Link.code == code))


def total_clicks(db: Session, link_id: int) -> int:
    return int(db.scalar(select(func.count(Click.id)).where(Click.link_id == link_id)) or 0)


def clicks_per_day(db: Session, link_id: int) -> list[dict[str, int | str]]:
    start_date = date.today() - timedelta(days=29)
    start_at = datetime.combine(start_date, time.min, tzinfo=timezone.utc)
    day_column = func.date(Click.clicked_at).label("day")
    rows = db.execute(
        select(day_column, func.count(Click.id).label("clicks"))
        .where(Click.link_id == link_id, Click.clicked_at >= start_at)
        .group_by(day_column)
        .order_by(day_column)
    ).all()
    return [
        {"date": value.isoformat() if hasattr(value, "isoformat") else str(value), "clicks": int(count)}
        for value, count in rows
    ]


def breakdown(db: Session, link_id: int, dimension) -> list[dict[str, int | str]]:
    rows = db.execute(
        select(dimension.label("name"), func.count(Click.id).label("count"))
        .where(Click.link_id == link_id)
        .group_by(dimension)
        .order_by(func.count(Click.id).desc(), dimension)
    ).all()
    return [{"name": str(name), "count": int(count)} for name, count in rows]
