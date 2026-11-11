from datetime import datetime, timezone
from typing import Any, Callable

from src.services.errors import BlockedUserError, ConflictError, NotFoundError


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class EventsService:
    def __init__(self, events_repo: Any, now: Callable[[], datetime] = utc_now):
        self.events_repo = events_repo
        self.now = now

    def get_upcoming_events(self, user: dict[str, Any]) -> list[dict[str, Any]]:
        # All signed-in accounts (including blocked accounts) may view upcoming published events
        return self.events_repo.get_upcoming_published_events()

    def sign_up(self, user: dict[str, Any], event_id: int) -> dict[str, Any]:
        self._refuse_blocked(user)
        event = self._published_event(event_id)
        if not self._reservation_is_open(event):
            raise ConflictError("Reservation is not open")

        result, registration = self.events_repo.create_registration_if_seat_free(user["id"], event_id)
        if result == "missing":
            raise NotFoundError("Event not found")
        if result == "duplicate":
            raise ConflictError("You are already signed up")
        if result == "full":
            raise ConflictError("This event is full")
        return registration

    def save_event(self, user: dict[str, Any], event_id: int) -> dict[str, Any]:
        self._refuse_blocked(user)
        self._published_event(event_id)
        return self.events_repo.create_saved_event(user["id"], event_id)

    def _refuse_blocked(self, user: dict[str, Any]) -> None:
        if user.get("is_blocked"):
            raise BlockedUserError("Your account is blocked")

    def _published_event(self, event_id: int) -> dict[str, Any]:
        # Users never see unpublished events, so a draft is "not found" to them
        event = self.events_repo.get_event(event_id)
        if event is None or event["status"] != "published":
            raise NotFoundError("Event not found")
        return event

    def _reservation_is_open(self, event: dict[str, Any]) -> bool:
        now = self.now()
        if event["start_time"] <= now:
            return False
        opens, closes = event["reservation_open"], event["reservation_close"]
        if opens is not None and now < opens:
            return False
        if closes is not None and now > closes:
            return False
        return True
