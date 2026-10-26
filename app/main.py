"""FastAPI application for creating and resolving short links."""

import secrets
import string

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.models import Link
from app.schemas import LinkCreate, LinkResponse
from app.validation import validate_long_url


app = FastAPI(title="URL Shortener API")

CODE_ALPHABET = string.ascii_letters + string.digits
CODE_LENGTH = 7
MAX_CODE_RETRIES = 10


def generate_code() -> str:
    """Generate a short, URL-safe identifier."""

    return "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_LENGTH))


@app.post("/api/links", response_model=LinkResponse, status_code=status.HTTP_201_CREATED)
def create_link(payload: LinkCreate, db: Session = Depends(get_db)) -> LinkResponse:
    """Validate a destination and persist a collision-safe short code."""

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


@app.get("/{code}")
def redirect_to_long_url(code: str, db: Session = Depends(get_db)) -> RedirectResponse:
    """Resolve a short code and issue a temporary redirect."""

    link = db.scalar(select(Link).where(Link.code == code))
    if link is None:
        raise HTTPException(status_code=404, detail="Short link not found")

    return RedirectResponse(url=link.long_url, status_code=status.HTTP_302_FOUND)
