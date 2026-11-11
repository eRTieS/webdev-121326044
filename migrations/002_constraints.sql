-- Migration 002: Constrain roles and statuses, and stop deletes from cascading into events

ALTER TABLE users
    ADD CONSTRAINT users_role_check CHECK (role IN ('user', 'organizer', 'admin'));

ALTER TABLE events
    ADD CONSTRAINT events_status_check CHECK (status IN ('draft', 'published', 'cancelled'));

-- Deleting an organizer cancels their events (in the service) and keeps the rows,
-- so notifications can still name the event. The event just loses its organizer.
ALTER TABLE events ALTER COLUMN organizer_id DROP NOT NULL;
ALTER TABLE events
    DROP CONSTRAINT events_organizer_id_fkey,
    ADD CONSTRAINT events_organizer_id_fkey
        FOREIGN KEY (organizer_id) REFERENCES users(id) ON DELETE SET NULL;

-- A room that still has events cannot be deleted by accident.
ALTER TABLE events
    DROP CONSTRAINT events_room_id_fkey,
    ADD CONSTRAINT events_room_id_fkey
        FOREIGN KEY (room_id) REFERENCES rooms(id) ON DELETE RESTRICT;
