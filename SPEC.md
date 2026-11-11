# Lab Booking System

<!-- Exercise 2. Write the non-goals first. Every acceptance criterion must be checkable in under a minute.
     Keep these headings exactly as they are: the self-checks look for them by name.
     The full target is on the course site under Resources → The course project. -->

## Project option
<!-- One line: lab booking, study groups, club events, or the own project the lecturer approved. -->
Lab booking.

## Goals

### Accounts and roles
- There are three roles: user, organizer and admin.
- The first admins are created by a seed script or an environment variable. After that, only an admin can make someone an admin, by promoting an existing account or by creating a new admin account.
- The last admin can't be deleted, blocked or demoted, so someone can always manage the system.
- An admin can change roles, block accounts, delete accounts and reset the password of a local account. There is no self-service reset; the sign-in page tells users to ask an admin.
- Deleting or blocking an account frees that person's seats and equipment. If the account belongs to an organizer, their events are cancelled too, and the admin sees a warning first if the organizer has active events.
- A blocked user can still sign in and browse events, and sees a message that the account is blocked. They can't sign up for events or save them.

### Rooms and equipment
- The admin page manages rooms, organizers and users.
- The admin sets each room's default number of seats and equipment. Only an admin can change these defaults.
- An organizer can use a room's defaults for an event, or set different numbers for that event only: more, for example extra seats just for this event, or fewer, to free up space. This includes more equipment than the room has, for example when the organizer brings extra laptops. Changing an event's numbers never changes the room's defaults.
- No overlaps: a room holds one event at a time, and each piece of equipment is booked by one person at a time. This is checked when an event is created and whenever its time or room changes.

### Creating and publishing events (organizer)
- An organizer creates an event by choosing a free room, the number of seats and equipment, when reservation opens and closes, when the event starts, and how long it lasts.
- The organizer can mark equipment as required for the event. A user who has none of their own can book one. When none are left, users must bring their own.
- A new event books its room and time as soon as it is created, even before it is published. The organizer's profile shows their events that are not published yet.
- The organizer publishes the event after creating it.

### Changing and cancelling events (organizer)
- An organizer can edit and cancel their own events.
- An admin can edit, cancel and delete any event.
- Fewer seats: if the organizer lowers an event's seats, the latest registrations are removed.
- Less equipment: if the organizer lowers an event's equipment, the latest equipment bookings are removed. Those users keep their seats.
- New time: allowed only if the room is free at the new time.
- New room: allowed only if the new room is free at that time. The event starts with the new room's default seats and equipment, which the organizer can then change. Registrations and equipment bookings move to the new room, and the old room is freed. If the new room's defaults have fewer seats, the latest registrations are removed along with their equipment. If they only have less equipment, the latest users lose their equipment but keep their seats.

### Signing up (user)
- A user signs in, sees upcoming lab events, and signs up for one with free seats, booking equipment if needed.
- A user can cancel their reservation.
- A user can save events. Saved events are a list, not a queue: when a seat frees up, everyone who saved the event is notified, and the first to sign up gets it.

### Notifications
- Notifications appear in a bell on the page and update when a page loads.
- A user is notified of every change to their reservations and every update to their events: cancellation, deletion, time change and other changes. This applies whether the organizer or an admin makes the change.
- A user is notified when reservation opens for an event they saved.
- Users who asked to be notified get a notification when equipment for an event frees up.
- An organizer gets a notification for every sign-up to their events.

### Main page
- The main page shows an announcement for every newly published event, newest first. Each announcement stays until its event starts, and the list updates on page load.

## Non-goals

- no payment system: it is university booking system during lab events.
- no take home: the equipment is available in the room only during the event.
- no recurring events: every event is created separately.
- no mobile app needed: web UI that works well on a phone
- no emails, no sms: the user check the site
- no browser notifications: no notifications needed outside of the page. No notification pop-ups outside of the page.
- no advertising services needed: do not add ad banners
- not selling equipment: it will be used only for sharing the university equipment during lab events if needed

## Constraints

- the passwords are stored as a salted PBKDF2-HMAC-SHA256 hash in database with 600000 iterations. Tests may use fewer iterations to stay fast; the running app always uses 600000.
- python backend with fastapi
- postgreSQL as a database
- plain HTML, CSS and Javascript in the UI. CSS framework and CDN libraries are okay, like AlpineJS. No build step.
- the UI is in English only.
- all times are in the Europe/Sofia time zone: the app is used only at the Technical University.

## The model feature
<!-- Which model, which modality, and what it does for a user.
     Name three things or the check fails: the input it receives, the output it produces,
     and what happens when the model is slow, rate-limited or wrong. -->
- Model: Google Gemini 2.5 Flash (`gemini-2.5-flash`) through the Gemini API, text in and JSON out. The model name comes from `MODEL_NAME` and the key from `GEMINI_API_KEY`.

### Event search (users)
- Input: the text a user types into the search box, for example "laptop lab on Thursday afternoon", plus today's date in Europe/Sofia and the list of room names. Nothing about the user is sent: no name, no email, no reservations.
- Output: search filters as JSON: date range, time of day, room, whether equipment is needed, and keywords. The app checks every filter (a real date, a room that exists) and drops the ones that fail, then runs the normal database query over published upcoming events. Every result comes from the database. The screen shows the filters the model understood, labelled "Suggested filters", and the user can change them.
- When it fails: the call times out after 10 seconds. On a timeout, a 429 rate limit, a provider error, a missing key, or output that isn't valid JSON, the app falls back to keyword search over event titles and descriptions and shows "Smart search isn't available right now, showing keyword results". The rest of the page keeps working.
## Auth
<!-- Local sign-in plus at least one provider. Say how an account signing in both ways stays one account. -->
- Local: a visitor registers with an email and a password of at least 8 characters, and gets the user role. The password is stored as a salted PBKDF2-HMAC-SHA256 hash (see Constraints). After sign-in the server sets a signed session cookie (`SESSION_SECRET`) that is HttpOnly, Secure and SameSite=Lax. Signing out clears it. A wrong email or password gets the same message, so nobody can tell which emails have accounts. There is no self-service password reset, because the app sends no emails. The sign-in page says "Forgot your password? Ask an admin to reset it", and an admin can set a new password for any local account from the admin page.
- Session checks: every request re-checks the account in the database, so blocking, deleting or a role change takes effect on the next page load. After a block, the next page load shows the block message. After a delete, the person is signed out.
- Provider: Sign in with Google (OAuth 2.0 / OpenID Connect, authorization code flow). The exchange happens on the server, and `GOOGLE_CLIENT_SECRET` never reaches the browser. The account stores Google's user id (`sub`). The first Google sign-in with an unknown email creates a new account with the user role.
- Linking: one person, one account, and the email is the only way to match an account the first time. A Google sign-in is matched by email only if Google reports the email as verified. If a local account already has that email, the person must enter that account's password once. After that, the Google id is saved on the account, and both ways sign in to the same account, with the same role and reservations. Registering locally with an email that already belongs to a Google account is refused with "This email already has an account. Sign in with Google". Blocking applies to the account, so a blocked person is blocked both ways.

## MCP tools
<!-- At least three tools your own MCP server exposes over this project's data.
     Each tool calls the same service functions the HTTP API calls, so the same rules apply.
     A description shorter than 20 characters is not a description. -->
Every tool is read-only: none of them signs up, cancels or changes anything. Every tool acts as the account that `MCP_TOKEN` belongs to, and calls the same service function as the matching HTTP route.

| Tool | What it does | Who may call it |
| --- | --- | --- |
| `list_upcoming_events` | Lists published events that have not started yet, with room, start time, duration, free seats and free equipment. Optional filters: date range, room, and whether equipment is needed. | Any signed-in account, including blocked ones |
| `get_event` | Returns one event by id: title, description, room, start time, duration, reservation window, free seats and free equipment. An unpublished event is returned only to its organizer or an admin. | Any signed-in account |
| `list_my_reservations` | Lists the calling account's own reservations, with event, room, start time and whether equipment is booked. | Any signed-in account |
| `find_free_rooms` | Lists rooms that are free for a given start time and duration, with their default seats and equipment, so an organizer can plan an event before creating it. | Organizer or admin |

## UI
<!-- Stack, and the three or more screens. The graded checklist lives in docs/UI.md. -->

- Stack: plain HTML, CSS and JavaScript, with Alpine.js loaded from a CDN at a pinned version, and no build step. FastAPI serves the pages as static files, and the JavaScript calls the FastAPI JSON routes with the session cookie. Those routes use the same services as the MCP tools. The CSS uses its own design tokens as custom properties: one spacing scale and one type scale. Pages are in English (`lang="en"`), show all times in Europe/Sofia, and work at 380, 768 and 1280 pixels wide.

- Every screen has a loading, an empty, an error and a success state, and a header with the notification bell, which updates on page load.

Screens:

1. Sign in and register: email and password, "Sign in with Google", and the one-time password prompt that links a Google sign-in to an existing local account.

2. Main page: announcements for newly published events (newest first), the list of upcoming events, and the search box. Smart search shows the filters it understood as "Suggested filters" and falls back to keyword results.

3. Event page: details, free seats and free equipment, plus the actions the viewer is allowed:
   - users: Sign up (with or without equipment), Save, "Notify me about equipment", Cancel reservation;
   - the event's organizer: Edit, Publish, Cancel;
   - admins: Edit, Cancel, Delete.
   A blocked user sees the event with no actions and the block message.

4. My reservations: the user's reservations and saved events, each with a Cancel or Remove action.

5. Notifications: the full list behind the bell, newest first. Each entry keeps the event's title and time, even after the event is deleted.

6. Organizer profile: the organizer's events, with the unpublished ones marked "Not published", and a "Create event" button.

7. Create and edit event: choose a free room, then times, the reservation window, and seats and equipment pre-filled from the room's defaults. Required equipment is marked here.

8. Admin page: rooms with their default seats and equipment; accounts with role changes, password reset, block and delete, including the warning when an organizer has active events; and all events, with edit, cancel and delete.

## Architecture
<!-- Exercise 3. One request traced through every layer, naming the file for each one,
     plus one place where your own code does not match this layering. -->

## Acceptance criteria
<!-- Every criterion carries an id. A test proves it by naming that id in its title, for example
     test('AC-3 a booking that overlaps another is refused with 409', ...).
     Say who acts, what they see, and what must be true in the database. -->
### Slice 1: sign-in and the upcoming events list
- [AC-1] A visitor registers with an email and a password, signs in, and sees the list of upcoming events. In `users`, the stored password is a salted PBKDF2-HMAC-SHA256 hash that records its salt and its iteration count, 600000, and is not the password itself.
- [AC-2] Two users register with the same password. Both can sign in and see the list of upcoming events, and their stored hashes in `users` are different.
- [AC-3] A user who signs in with a wrong password sees "Wrong email or password" and stays on the sign-in page. No session cookie is set.
- [AC-4] The database holds a published event that starts tomorrow, an unpublished event, and a published event whose start time is an hour ago. A signed-in user sees only the first one in the list, with its room, start time and free seats.
- [AC-5] A blocked user signs in, sees "Your account is blocked" and can browse the events list. The Sign up and Save buttons are not shown, a direct request to sign up or save is refused with 403, and no row appears in `registrations` or `saved_events`.

### Signing up and saving events (user)
- [AC-6] A user signs up for an event with free seats and sees "You are signed up". One row appears in `registrations`, and the event's free seats go down by one.
- [AC-7] A user who signs up for an event with no free seats sees "This event is full", and no new row appears in `registrations`.
- [AC-8] In `events`, one event's reservation opens tomorrow and another's closed yesterday. A user who tries to sign up for either sees "Reservation is not open", and no new row appears in `registrations`.
- [AC-9] A user signs up and books a laptop while laptops are left. They see "You are signed up with a laptop", and one row appears in `equipment_bookings`. When none are left, the user can still sign up, sees "No equipment left: please bring your own", and no row appears in `equipment_bookings`.
- [AC-10] A user cancels their reservation and sees "Your reservation is cancelled". Their rows for that event in `registrations` and `equipment_bookings` are gone, and the free seats go up by one.
- [AC-11] Two users have saved a full event. A third user cancels their reservation, which frees a seat, and both saving users get a notification. The first to sign up sees "You are signed up" and has a row in `registrations`. The second sees "This event is full" and has no row.

### Creating and changing events (organizer and admin)
- [AC-12] An organizer creates an event in Room 101 from 10:00 to 12:00 while another event holds Room 101 from 11:00 to 13:00. They see "This room is already booked at that time", and no new row appears in `events`.
- [AC-13] An organizer moves an event to a time when its room is already booked. They see "This room is already booked at that time", and the event's time in `events` is unchanged.
- [AC-14] An organizer moves an event to a room that is booked at that time. They see "This room is already booked at that time", and the event's room in `events` is unchanged.
- [AC-15] In a room with 20 default seats and 10 laptops, an organizer creates an event with 25 seats and 15 laptops. They see the new event with 25 seats and 15 laptops. The event in `events` has 25 and 15, and the room in `rooms` still has 20 and 10.
- [AC-16] An organizer sees no way to edit a room. A direct request from an organizer to change a room's default seats is refused with 403, and the room in `rooms` is unchanged.
- [AC-17] An event has 10 seats and 10 registrations. The organizer lowers it to 8 seats and sees the event with 8 seats. The two latest registrations are removed from `registrations`, and those two users see a notification in the bell.
- [AC-18] An event has 5 laptops, all booked. The organizer lowers it to 3 and sees the event with 3 laptops. The two latest rows in `equipment_bookings` are removed, those two users keep their rows in `registrations`, and they see a notification in the bell.
- [AC-19] An organizer moves an event with 15 registrations to a free room whose defaults are 12 seats. The organizer sees the event in the new room with the new room's default seats and equipment. The three latest registrations are removed from `registrations`, and those three users see a notification in the bell.
- [AC-20] An organizer creates an event and doesn't publish it. Their profile lists the event as not published, and its status in `events` is `draft`. Another organizer who tries to create an event in that room at that time sees "This room is already booked at that time".
- [AC-21] An organizer opens another organizer's event and sees no Edit or Cancel button. A direct request to change its start time or cancel it is refused with 403, and the event in `events` is unchanged. An admin changes the same event's start time, sees the new time on the event page, and `events` holds the new time.

### Accounts and roles (admin)
- [AC-22] The only admin tries to demote, block or delete their own account and sees "At least one admin must remain". Their row in `users` is unchanged.
- [AC-23] An admin blocks a user who is signed up for an event with a laptop. The admin sees the user marked as blocked, and the user sees a notification that their reservation was removed. That user's rows in `registrations` and `equipment_bookings` are gone, and the seat and the laptop are free again.
- [AC-24] An admin deletes an organizer who has an active event. The admin first sees a warning that the organizer has active events. After confirming, the organizer's row is gone from `users`, the event's status in `events` is `cancelled`, and everyone signed up for it gets a notification.
- [AC-25] An admin promotes a user to admin: the user's role in `users` is `admin`, and they can open the admin page. A user who is not an admin sees no link to the admin page, and opening its address directly shows "You don't have access to this page" with status 403.

### Notifications and the main page
- [AC-26] An admin changes the start time of an event a user is signed up for. The next time that user loads a page, the bell shows a notification about the new time, and one new row for that user appears in `notifications`.
- [AC-27] An admin deletes an event a user is signed up for. The user's notification still shows the event's title and time, although the event is gone from `events`.
- [AC-28] A user signs up for an event. Its organizer gets one new row in `notifications` and sees it in the bell.
- [AC-29] A user has saved an event, and its reservation opening time in `events` is set to a minute ago. On the user's next page load, the bell shows "Reservation is open" for that event, and one new row for that user appears in `notifications`. Loading another page adds no second row.
- [AC-30] On an event's page, one user clicks "Notify me about equipment" and another user doesn't. A third user cancels their laptop booking for that event. The first user sees a notification in the bell and has one new row in `notifications`. The second user has none.
- [AC-31] An organizer publishes event A, then event B. The main page shows B's announcement above A's. After A's start time in `events` is set to a minute ago, the main page no longer shows A's announcement.

## Traceability
<!-- Filled in from Exercise 3 onward: each AC id, and the test that names it. -->
| Criterion | Test |
| --- | --- |
| AC-1 |  |

## Spec vs result
<!-- After the agent builds the slice: which criteria passed, which it missed or reinterpreted, and what you changed in this spec because of it. -->

### Slice 1 (built by Gemini CLI on 2026-11-10, reviewed and fixed afterwards)

**Passed.** AC-1 to AC-5 all matched in the code Gemini wrote, and each has a test with its id in the name. Gemini reported 17 passing tests. After the fixes below, 36 tests pass locally against a separate test database, with 100% line and branch coverage of `src/services/`.

**Reinterpreted.**
- The Auth section says the session cookie is always `Secure`. Gemini set `Secure` only over HTTPS.
- My build prompt asked it to stop after each step and wait. It stopped after steps 1 and 2. After step 2, I sent a correction ("missing .env loading, use database name labbooking"), and it made the fix and went straight on to build step 3 without waiting.
- My approval prompt still contained its placeholder (`<your corrections, or "none">`). Gemini read it as "approved with no changes". That was my mistake, not the agent's.

**Missed.**
- `SESSION_SECRET` had a hard-coded fallback in a public repository, so a server without the variable would accept forged sessions.
- The database URL had a hard-coded default too. The first one was `labdb` over TCP, which needed a password; it was fixed after my correction.
- The sign-up and save endpoints existed but checked only blocking. Users could sign up for full events, drafts or events that had started. Signing up twice, or for an unknown event, returned a 500 error.
- The seed rows went into a migration (`002_seed_slice1.sql`), with the demo passwords in plain text in its comments. A migration also runs on the deployed database.
- Its plan said `organizer_id REFERENCES users(id)`, but the migration added `ON DELETE CASCADE`. Deleting an organizer would have deleted their events, while the Goals say the events are cancelled.
- The data-layer tests read and wrote the development database and depended on its seed rows.
- The `role` column had no constraint.
- Its `.env` write failed ("Path not in workspace"), but the step 3 report still said `.env` settings were respected. It also never asked before touching `.env`, which is on the "Always ask before" list.

**What I changed because of it.** The fixes went into the code and `AGENTS.md`, not into this spec:
- Code: no defaults for secrets, the sign-up and save rules, a constraints migration, a local-only seed script and a separate test database.
- `AGENTS.md`: the migrate and seed commands, the `/tmp` socket and the error convention.

`SPEC.md` itself is unchanged so far. No acceptance criterion says that secrets have no defaults, or that migrations hold schema only. That is how both slipped through, and they are candidates for new criteria.
