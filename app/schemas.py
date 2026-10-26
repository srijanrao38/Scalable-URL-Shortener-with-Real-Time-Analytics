"""Pydantic request and response schemas."""

from pydantic import BaseModel, ConfigDict


class LinkCreate(BaseModel):
    long_url: str


class LinkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    long_url: str
    short_url: str


class LinkListItem(LinkResponse):
    created_at: str
    click_count: int


class BreakdownItem(BaseModel):
    name: str
    count: int


class ClicksPerDayItem(BaseModel):
    date: str
    clicks: int


class StatsResponse(BaseModel):
    code: str
    total_clicks: int
    clicks_per_day: list[ClicksPerDayItem]
    device_breakdown: list[BreakdownItem]
    browser_breakdown: list[BreakdownItem]
