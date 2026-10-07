"""Health response schema: app status plus broker link state."""

from pydantic import BaseModel


class BrokerState(BaseModel):
    connected: bool


class HealthOut(BaseModel):
    status: str
    broker: BrokerState
