from datetime import datetime
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from src.data.events import EventsRepository
from src.routes.auth import get_current_user
from src.services.errors import BlockedUserError, ConflictError, NotFoundError, ServiceError
from src.services.events import EventsService

router = APIRouter(prefix="/api/events", tags=["events"])

ERROR_STATUS = {
    BlockedUserError: status.HTTP_403_FORBIDDEN,
    NotFoundError: status.HTTP_404_NOT_FOUND,
    ConflictError: status.HTTP_409_CONFLICT,
}


class UpcomingEventResponse(BaseModel):
    id: int
    title: str
    description: str | None = None
    room_name: str
    start_time: datetime | str
    duration_minutes: int
    seats: int
    free_seats: int


def get_events_service() -> EventsService:
    return EventsService(EventsRepository())


@router.get("/upcoming", response_model=list[UpcomingEventResponse])
def get_upcoming_events(
    current_user: dict[str, Any] = Depends(get_current_user),
    events_service: EventsService = Depends(get_events_service),
):
    events = events_service.get_upcoming_events(current_user)
    return [
        UpcomingEventResponse(
            id=e["id"],
            title=e["title"],
            description=e.get("description"),
            room_name=e["room_name"],
            start_time=e["start_time"],
            duration_minutes=e["duration_minutes"],
            seats=e["seats"],
            free_seats=e["free_seats"],
        )
        for e in events
    ]


@router.post("/{event_id}/register")
def register_for_event(
    event_id: int,
    current_user: dict[str, Any] = Depends(get_current_user),
    events_service: EventsService = Depends(get_events_service),
):
    try:
        registration = events_service.sign_up(current_user, event_id)
        return {"message": "You are signed up", "registration": registration}
    except ServiceError as e:
        raise HTTPException(status_code=ERROR_STATUS[type(e)], detail=str(e))


@router.post("/{event_id}/save")
def save_event(
    event_id: int,
    current_user: dict[str, Any] = Depends(get_current_user),
    events_service: EventsService = Depends(get_events_service),
):
    try:
        saved = events_service.save_event(current_user, event_id)
        return {"message": "Event saved", "saved_event": saved}
    except ServiceError as e:
        raise HTTPException(status_code=ERROR_STATUS[type(e)], detail=str(e))
