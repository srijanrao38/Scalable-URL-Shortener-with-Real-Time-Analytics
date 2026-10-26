"""Pydantic request and response schemas."""

from pydantic import BaseModel, ConfigDict


class LinkCreate(BaseModel):
    long_url: str


class LinkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    long_url: str
    short_url: str
