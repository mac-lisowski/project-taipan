"""Health: one endpoint for liveness plus readiness over cached link state."""

from typing import Annotated

from fastapi import APIRouter, Depends
from messaging import Messaging

from api.messaging import get_messaging
from api.schemas import HealthOut

router = APIRouter(tags=["health"])

MessagingDep = Annotated[Messaging, Depends(get_messaging)]


@router.get("/health", response_model=HealthOut)
def health(messaging: MessagingDep) -> HealthOut:
    # Cached link state only: never ping, never open a connection.
    return HealthOut(status="ok", broker={"connected": messaging.connected})
