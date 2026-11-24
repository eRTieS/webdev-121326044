from datetime import datetime, timezone
from typing import Any, Callable
from zoneinfo import ZoneInfo

from src.services.errors import BlockedUserError, ConflictError, NotFoundError

SOFIA_TZ = ZoneInfo("Europe/Sofia")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


MONTH_NAMES = (
    "", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
)


def format_sofia_time(start_time: datetime) -> str:
    sofia_dt = start_time.astimezone(SOFIA_TZ)
    month = MONTH_NAMES[sofia_dt.month]
    return f"{sofia_dt.day} {month} {sofia_dt.year} at {sofia_dt:%H:%M}"


class EventsService:
    def __init__(self, events_repo: Any, now: Callable[[], datetime] = utc_now):
        self.events_repo = events_repo
        self.now = now

    def get_upcoming_events(self, user: dict[str, Any]) -> list[dict[str, Any]]:
        # All signed-in accounts (including blocked accounts) may view upcoming published events
        return self.events_repo.get_upcoming_published_events()

    def sign_up(
        self, user: dict[str, Any], event_id: int, book_equipment: bool = False
    ) -> dict[str, Any]:
        self._refuse_blocked(user)
        event = self._published_event(event_id)
        if not self._reservation_is_open(event):
            raise ConflictError("Reservation is not open")

        result, registration = self.events_repo.create_registration_if_seat_free(
            user["id"], event_id, book_equipment
        )
        if result == "missing":
            raise NotFoundError("Event not found")
        if result == "duplicate":
            raise ConflictError("You are already signed up")
        if result == "full":
            raise ConflictError("This event is full")

        self.events_repo.delete_saved_event(user["id"], event_id)

        if result == "created_with_equipment":
            message = "You are signed up with a laptop"
        elif result == "created_without_equipment":
            message = "No equipment left: please bring your own"
        else:
            message = "You are signed up"

        return {**registration, "message": message}

    def cancel_reservation(self, user: dict[str, Any], event_id: int) -> dict[str, str]:
        # Cancel has no blocked check and no published check
        result, was_full = self.events_repo.cancel_registration(user["id"], event_id)
        if result == "missing":
            raise NotFoundError("You have no reservation for this event")

        if was_full:
            savers = self.events_repo.get_saver_ids(event_id)
            if savers:
                event = self.events_repo.get_event(event_id)
                time_str = format_sofia_time(event["start_time"])
                message = f"{event['title']} on {time_str}: a seat has opened up"
                self.events_repo.create_notifications(savers, event_id, message)

        return {"message": "Your reservation is cancelled"}

    def save_event(self, user: dict[str, Any], event_id: int) -> dict[str, Any]:
        self._refuse_blocked(user)
        self._published_event(event_id)
        # Saving is for being told about free seats, which a registered user doesn't need
        if self.events_repo.get_registration(user["id"], event_id):
            raise ConflictError("You are already signed up for this event")
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
