# Agent log

One entry per agent session, newest at the bottom. Be honest: what went wrong is the useful part.

<!-- Copy this block for each session:

## YYYY-MM-DD · <short title>
- Goal:
- Delegated:
- Checkpoints:
- Went wrong:
- Changed by hand:

-->

## 2026-10-14 · Exercise 1 MCP server
- Goal: work through Exercise 1, steps 1–10, in file`mcp-server/server.py`.
- Delegated: Claude Code recorded the step 8 transcript, pointed `.gemini/settings.json` and `.vscode/mcp.json` at `server.py`, created `package.json` with the `mcp` script, ran the description experiment and filled in the practice copy's logs.
- Checkpoints: the step's own test commands after every step; the real self-check (`node mcp-server/check.mjs -- npm run --silent mcp`) at 12/12;.
- Went wrong: Gemini 2.5 Flash is no longer available to new users, and Gemini 3.8 Flash kept answering 503 "high demand" and then hit the free daily quota after one successful run, so I paied to finish the experiment; a review found inputs that still crash the server (a `tools/call` without `params` or `name`, `"arguments": null`, a non-string `query`), and they are not fixed yet.
- Changed by hand: 

## 2026-10-14 · Gemini CLI explains the protocol
- Goal: understand each part of the protocol with the exercise's prompts: reading stdin line by line and logging to stderr, `initialize` and `notifications/initialized`, `tools/list` and its JSON Schema, the shape of a `tools/call` result, and tool errors versus protocol errors.
- Delegated: explanations only; every prompt told Gemini not to write the code.
- Checkpoints: Gemini wrote no files; the self-check still passes 12/12.
- Went wrong: I used the prompts as written, so they asked about Node.js (`readline`, `console.error`, `readFileSync`) although my server is in Python; in the last prompt I left the `<paste it here>` placeholder instead of my `handle` function, so Gemini searched the folder itself and read `check.mjs`, `messages.jsonl` and the README but never `server.py`, and explained the expected replies instead of reviewing my handler.
- Changed by hand: nothing, the session produced explanations and no code.

## 2026-10-14 · Gemini CLI: connecting the server and the description experiment
- Goal: step 9: check that Gemini loads both tools, ask "What does lecture 7 cover?" without naming a tool, record the usage, and compare a vaguer and a much more precise `find_lecture` description.
- Delegated: the tool choice; Gemini decided which tool to call and I allowed each call.
- Checkpoints: `/mcp` showed `my-project` with 2 tools; `/mcp desc` showed which description was really loaded; Gemini's local session logs showed which tool each run called.
- Went wrong: at first I edited the description and asked the same question four more times in the same session; `/mcp` does not restart the server, so Gemini still had the original description, and with the answer already in the conversation it once answered from memory, once read `lectures.json` and `course.json` directly, and once read the self-check files before calling the tool; none of that measured the description, so I redid both runs with `/quit` and a fresh session each time. I also quit the vague-description session without running `/stats`, so `USAGE.md` only has the first session.
- Changed by hand: the `find_lecture` description in `server.py` between runs; the precise description stayed in.

## 2026-10-14 · Claude Code: step 9 write-up and step 10
- Goal: understand what step 9 asks, tell which Gemini runs were valid, and finish the README, `USAGE.md` and this log.
- Delegated: reading Gemini's session logs to see which runs were fresh sessions and which tool each one called; the Gemini rows and price note in `USAGE.md`; "How to start it" and "The description experiment" in `mcp-server/README.md`; a code block around my transcript; this log.
- Checkpoints: I ran every Gemini session myself and pasted the output; the self-check passed 12/12 with both `python3 mcp-server/server.py` and `npm run --silent mcp`; no commit or push by the agent.
- Went wrong: Claude added at first wrote the two models' tokens as one summed row, which I had split into one row per model.
- Changed by hand: ran the step 8 session and pasted the transcript; changed the `mcp` script in `package.json` from `python` to `python3`.

## 2026-11-10 · Gemini CLI: plan and build Slice 1
- Goal: plan Slice 1 (AC-1 to AC-5) without writing any code, then build it in three steps: the database tables with a few seeded rows, then sign-in, then the list screen. Gemini was to stop after each step so I could check it.
- Delegated: Gemini CLI (gemini-3.8-flash) wrote the plan and then all of Slice 1: `requirements.txt`, `.python-version`, the two migrations, `src/` (data, services, routes and the static page) and the tests. It installed the packages with `pip install -r requirements.txt`, created the `labbooking` database, and ran both migrations by hand with `psql`.
- Checkpoints:
  - The plan was reviewed before any code was written. It had five tables (`users`, `rooms`, `events`, `registrations`, `saved_events`) and seven endpoints: register, login, logout, me, upcoming events, and sign-up and save, which only refuse blocked users. It had one page with a sign-in view and a list view, and the files for each layer, each mapped to the criteria it serves. I approved it without changes.
  - After each step Gemini reported what it had built and gave me commands to check it. It ran the coverage gate (`pytest --cov=src/services --cov-fail-under=100 && pytest --cov=src --cov-fail-under=80`) and `node checks/ex3.mjs`, and finished with 17 passing tests and 93.56% coverage.
- Went wrong:
  - My approval prompt still contained its placeholder, `<your corrections, or "none">`. I sent it twice, because I cancelled the first run at its `sudo -n docker ps` command after about ten minutes of Docker probing.
  - The build differed from the approved plan:
    - The plan had no seed migration. The build added `002_seed_slice1.sql`, with the demo passwords in plain text in its comments.
    - The plan had `psycopg2-binary` and a connection pool. The build uses psycopg 3 with one connection per call.
    - The plan had `organizer_id` without a cascade. The build added `ON DELETE CASCADE`.
  - It hard-coded fallbacks for `SESSION_SECRET`, in a public repository, and for the database URL. The first database default was `labdb` over TCP, which needed a password.
  - After step 2, I sent a correction ("missing .env loading. Use database name labbooking"). It made the fix and went straight on to build step 3 without stopping.
  - Its `.env` write failed ("Path not in workspace"), but its step 3 report still said `.env` settings were respected. It never asked before touching `.env`. The chat also shows no question before `pip install`; the CLI may have shown its own approval prompt.
  - The data-layer tests ran against my development database and depended on its seed rows. The 17 passing tests therefore don't prove that the SQL works on a clean database.
- Changed by hand: during the session, only my correction after step 2 and cancelling the `sudo` command. The review and the fixes afterwards happened in a separate Claude Code session (see "Spec vs result" in `SPEC.md`).

## 2026-11-11 · Booking conflict rule
Goal: service function refusing overlapping bookings, plus its test
Autonomy: alone within the step, I read the diff before commit
Checkpoints used: plan review, tests green before commit
Went wrong: first version compared dates as text
Changed by hand: renamed the error to BookingConflict

## 2026-11-20 · Users and roles line in the spec
- Goal: headline, users and main scenario from the spec, plus one roles line in `SPEC.md` and `AGENTS.md`
- Autonomy: alone for reading and answering, edits only in files I approve, I read the diff before commit
- Checkpoints used: exact text shown before editing, `node checks/ex2.mjs` green after the edit
- Went wrong: called users "students, mostly" as if the spec said so; edited `SPEC.html` without approval
- Changed by hand: nothing yet

## 2026-11-23 · Slice 2 plan
- Goal: a plan of at most one page for Slice 2 (AC-6 to AC-18), no code
- Autonomy: plan only, no file written until I approve; then one step at a time, asking before the migration, I read the diff before commit
- Checkpoints used: plan review against `SPEC.md` and the code before any code, a second review of the revised plan, `git status` clean of new files until I approved
- Went wrong: the first plan moved the laptop rule into the data layer without saying so, kept the route's hard-coded message, would have failed AC-15, and added things I did not ask for (403 on cancel, `is_read`, an empty state for reservations)
- Changed by hand: nothing in the code yet
- Final plan:

```markdown
# Slice 2 plan: signing up and saving events

## Files
- AGENTS.md: the second data-layer exception (laptops counted under the event lock)
- migrations/003_slice2_tables.sql (new)
- src/data/events.py: seat and laptop locking in sign-up, cancel with a was-full result, saved-event removal, savers' notification rows
- src/services/events.py: sign-up messages, cancel, saver notifications
- src/routes/events.py: book_equipment on sign-up, the service's message, DELETE /{event_id}/register
- src/static/index.html: "Request laptop" checkbox, Cancel, Save, banners
- tests/test_data_layer.py and tests/test_events_service.py (plain names), tests/test_slice2_events_api.py (new, AC tests)

## Migration (ask before running it)
- equipment_bookings: id, user_id → users ON DELETE CASCADE, event_id → events ON DELETE CASCADE,
  created_at, UNIQUE (user_id, event_id)
- notifications: id, user_id → users ON DELETE CASCADE, event_id → events ON DELETE SET NULL,
  message TEXT NOT NULL (includes the event's title and time), created_at

## Endpoints (all: 401 not signed in, 422 bad event_id or book_equipment)
| Method | Path | Returns |
|---|---|---|
| POST | /api/events/{event_id}/register?book_equipment= | 200 "You are signed up" / "You are signed up with a laptop" / "No equipment left: please bring your own"; 403 "Your account is blocked"; 404 "Event not found" (unknown or draft); 409 "You are already signed up", "This event is full", "Reservation is not open" |
| DELETE | /api/events/{event_id}/register | 200 "Your reservation is cancelled"; 404 "You have no reservation for this event" (unknown event or no reservation) |
| POST | /api/events/{event_id}/save | 200 "Event saved" (also the second time); 403 "Your account is blocked"; 404 "Event not found" (unknown or draft); 409 "You are already signed up for this event" |

## Service rules (src/services/events.py)
- sign_up(user, event_id, book_equipment=False): refuse blocked → published event → reservation open
  (inside the window, start in the future) → create_registration_if_seat_free(user_id, event_id, book_equipment),
  which returns created / created_with_equipment / created_without_equipment / duplicate / full / missing.
  The service maps the code to an error or returns {**registration, "message": ...}.
  A successful sign-up also removes the user's saved_events row for that event.
- cancel_reservation(user, event_id): no blocked and no published check. No reservation →
  NotFoundError("You have no reservation for this event"). If the data layer reports the event was full,
  everyone who saved it gets "{title} at {time}: a seat has opened up", with the time in Europe/Sofia.
- save_event: unchanged; refuses blocked users, drafts and users who are signed up.

## Authorization
- 401 from get_current_user, before any service runs.
- 403 only from BlockedUserError, in sign_up and save_event.
- Cancel acts only on the caller's own registration (user["id"]).

## UI states
- Not signed up: Sign up, "Request laptop", Save. Signed up: Cancel, no Save. Blocked: no actions, the block message.
- Loading: buttons disabled while a request runs. Error: the server's detail. Success: the server's message.
  Empty: the Slice 1 "No upcoming lab events found".

## Tests
- tests/test_slice2_events_api.py:
  test_AC_6_user_signs_up_with_free_seats, test_AC_7_user_signs_up_full_event_refused_with_409,
  test_AC_8_user_signs_up_outside_window_refused_with_409, test_AC_9_user_signs_up_with_equipment_or_falls_back,
  test_AC_10_user_cancels_reservation_and_frees_seat_and_equipment,
  test_AC_11_cancel_notifies_savers_and_first_to_sign_up_wins, test_AC_12_duplicate_signup_refused_with_409,
  test_AC_13_signup_unknown_or_draft_refused_with_404, test_AC_14_signup_past_start_time_refused_with_409,
  test_AC_15_cancel_missing_or_unknown_refused_with_404, test_AC_16_save_draft_or_unknown_refused_with_404,
  test_AC_17_save_event_twice_is_idempotent, test_AC_18_save_event_already_signed_up_refused_with_409
- Plain-named service tests with fakes, and data-layer tests that run only with TEST_DATABASE_URL,
  including one that signing up removes the saved row.

## Steps (each tested and committed on its own; stop after each)
1. Migration and the AGENTS.md exception. Ask before running the migration.
2. Data layer and data-layer tests.
3. Service layer and service tests.
4. Routes and tests/test_slice2_events_api.py.
5. UI, then the full test suite and the coverage gates.
```

- Changed in review:
  - laptop count stays in the data function but returns only a result code, named in `AGENTS.md`: the first plan moved a rule into the data layer without saying so
  - the message comes from the service, not the route's hard-coded "You are signed up": sign-up now has three messages
  - cancel has no blocked or published check, and both a missing reservation and an unknown event get 404 "You have no reservation for this event": AC-15, and the spec refuses only sign-up and save for blocked users
  - the data layer only reports that the event was full, the service decides who is notified: the rule stays in the service
  - no `is_read`, the message holds the event's title and time: the spec has no read state, and AC-34 needs the title and time after the event is deleted
  - 200 instead of "200/201", and 422 listed: my prompt asked for every status code
  - AC-18 only gets its API test: its rule and service test already existed
  - AC tests in `tests/test_slice2_events_api.py`, plain names elsewhere: as in Slice 1
  - no empty state for reservations: there is no endpoint behind it in this slice
  - ask before the migration, data-layer tests only with `TEST_DATABASE_URL`: "Always ask before", and the Slice 1 tests ran against my development database
  - notification time in Europe/Sofia: the spec's time-zone rule, and only the browser converted times
  - blocked users see no actions, Cancel included: the spec's event page says "no actions"
  - signing up removes the saved row: the new goal in `SPEC.md`, so savers aren't told about seats in an event they're already in
