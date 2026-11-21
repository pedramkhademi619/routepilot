"""Routing policy database (``ip rule``) entry model."""

from pydantic import BaseModel, Field


class RpdbRule(BaseModel):
    """An ``ip rule`` that sends every lookup through a RoutePilot-owned table."""

    priority: int = Field(..., ge=1, le=32765, description="Rule priority (lower runs first)")
    table_id: int = Field(..., description="Routing table consulted by this rule")
    family: int = Field(default=4, description="Address family (4 or 6)")
