"""FastAPI application for creating and resolving short links."""

import secrets
import string
import hashlib
import json
from datetime import datetime, timezone

import redis
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.models import Click, Link
from app.redis_client import redis_client
from app.request_ip import get_client_ip
from app.schemas import LinkCreate, LinkListItem, LinkResponse, StatsResponse
from app.stats import breakdown, clicks_per_day, find_link, total_clicks
from app.validation import validate_long_url


app = FastAPI(title="URL Shortener API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

CODE_ALPHABET = string.ascii_letters + string.digits
CODE_LENGTH = 7
MAX_CODE_RETRIES = 10


def generate_code() -> str:
    """Generate a short, URL-safe identifier."""

    return "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_LENGTH))


def enforce_rate_limit(request: Request) -> None:
    """Apply a fixed-window limit, failing open if Redis is unavailable."""

    key = f"rate_limit:{get_client_ip(request)}"
    try:
        count = redis_client.incr(key)
        if count == 1:
            redis_client.expire(key, settings.rate_limit_window_seconds)
        if count > settings.rate_limit_per_minute:
            retry_after = redis_client.ttl(key)
            if retry_after < 0:
                retry_after = settings.rate_limit_window_seconds
            raise HTTPException(
                status_code=429,
                detail="Link creation rate limit exceeded",
                headers={"Retry-After": str(retry_after)},
            )
    except HTTPException:
        raise
    except redis.RedisError:
        # Availability of link creation is preferable to strict throttling
        # during a Redis outage; database uniqueness still protects storage.
        return


def hash_ip(ip_address: str) -> str:
    """Create a non-reversible, salt-protected identifier for analytics."""

    value = f"{settings.ip_hash_salt}:{ip_address}".encode("utf-8")
    return hashlib.sha256(value).hexdigest()


def enqueue_click_event(code: str, clicked_at: str, user_agent: str, ip_address: str) -> None:
    """Push analytics work after the response; failure must not affect redirects."""

    event = {
        "code": code,
        "timestamp": clicked_at,
        "user_agent": user_agent,
        "ip_hash": hash_ip(ip_address),
    }
    try:
        redis_client.lpush(settings.click_queue_name, json.dumps(event))
    except redis.RedisError:
        # Analytics is best effort at the edge; the worker queue can be
        # temporarily unavailable without turning a redirect into an error.
        return


@app.post("/api/links", response_model=LinkResponse, status_code=status.HTTP_201_CREATED)
def create_link(
    payload: LinkCreate,
    request: Request,
    db: Session = Depends(get_db),
) -> LinkResponse:
    """Validate a destination and persist a collision-safe short code."""

    enforce_rate_limit(request)
    try:
        long_url = validate_long_url(payload.long_url, settings.base_url)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    for _ in range(MAX_CODE_RETRIES):
        link = Link(code=generate_code(), long_url=long_url)
        db.add(link)
        try:
            # The unique database constraint is the authority in a race; a
            # pre-check alone would still allow two requests to pick a code.
            db.commit()
            db.refresh(link)
            return LinkResponse(
                code=link.code,
                long_url=link.long_url,
                short_url=f"{settings.base_url.rstrip('/')}/{link.code}",
            )
        except IntegrityError:
            db.rollback()

    raise HTTPException(status_code=503, detail="Could not allocate a unique short code")


@app.get("/api/links", response_model=list[LinkListItem])
def list_links(db: Session = Depends(get_db)) -> list[LinkListItem]:
    """List links and let PostgreSQL count clicks in the same query."""

    rows = db.execute(
        select(Link, func.count(Click.id).label("click_count"))
        .outerjoin(Click, Click.link_id == Link.id)
        .group_by(Link.id)
        .order_by(Link.created_at.desc())
    ).all()
    return [
        LinkListItem(
            code=link.code,
            long_url=link.long_url,
            short_url=f"{settings.base_url.rstrip('/')}/{link.code}",
            created_at=link.created_at.isoformat(),
            click_count=int(click_count),
        )
        for link, click_count in rows
    ]


def _stats_link_or_404(code: str, db: Session) -> Link:
    link = find_link(db, code)
    if link is None:
        raise HTTPException(status_code=404, detail="Short link not found")
    return link


@app.get("/api/links/{code}/stats", response_model=StatsResponse)
def link_stats(code: str, db: Session = Depends(get_db)) -> StatsResponse:
    link = _stats_link_or_404(code, db)
    return StatsResponse(
        code=link.code,
        total_clicks=total_clicks(db, link.id),
        clicks_per_day=clicks_per_day(db, link.id),
        device_breakdown=breakdown(db, link.id, Click.device),
        browser_breakdown=breakdown(db, link.id, Click.browser),
    )


@app.get("/api/links/{code}/stats/total")
def link_total_clicks(code: str, db: Session = Depends(get_db)) -> dict[str, int | str]:
    link = _stats_link_or_404(code, db)
    return {"code": code, "total_clicks": total_clicks(db, link.id)}


@app.get("/api/links/{code}/stats/daily")
def link_clicks_per_day(code: str, db: Session = Depends(get_db)) -> list[dict[str, int | str]]:
    link = _stats_link_or_404(code, db)
    return clicks_per_day(db, link.id)


@app.get("/api/links/{code}/stats/devices")
def link_device_breakdown(code: str, db: Session = Depends(get_db)) -> list[dict[str, int | str]]:
    link = _stats_link_or_404(code, db)
    return breakdown(db, link.id, Click.device)


@app.get("/api/links/{code}/stats/browsers")
def link_browser_breakdown(code: str, db: Session = Depends(get_db)) -> list[dict[str, int | str]]:
    link = _stats_link_or_404(code, db)
    return breakdown(db, link.id, Click.browser)


@app.get("/{code}")
def redirect_to_long_url(
    code: str,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> RedirectResponse:
    """Resolve a short code and issue a temporary redirect."""

    cached_url = None
    if settings.cache_enabled:
        try:
            cached_url = redis_client.get(f"link:{code}")
        except redis.RedisError:
            cached_url = None
        if cached_url:
            response = RedirectResponse(url=cached_url, status_code=status.HTTP_302_FOUND)
            background_tasks.add_task(
                enqueue_click_event,
                code,
                datetime.now(timezone.utc).isoformat(),
                request.headers.get("user-agent", ""),
                get_client_ip(request),
            )
            return response

    link = db.scalar(select(Link).where(Link.code == code))
    if link is None:
        raise HTTPException(status_code=404, detail="Short link not found")

    if settings.cache_enabled:
        try:
            redis_client.setex(f"link:{code}", settings.cache_ttl_seconds, link.long_url)
        except redis.RedisError:
            # A cache write is an optimization; the redirect must still work.
            pass

    response = RedirectResponse(url=link.long_url, status_code=status.HTTP_302_FOUND)
    background_tasks.add_task(
        enqueue_click_event,
        code,
        datetime.now(timezone.utc).isoformat(),
        request.headers.get("user-agent", ""),
        get_client_ip(request),
    )
    return response
