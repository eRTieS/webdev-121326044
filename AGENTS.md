# Instructions for the agent

Read this file at the start of every session. Keep it short and correct; update it when the project changes.

## Project
<!-- One or two sentences: what the app does and for whom. Link SPEC.md. -->
A lab booking web app for the Technical University: organizers publish lab events in rooms with a limited number of seats and equipment such as laptops, and users sign up for a seat and book equipment if they have none of their own. Admins manage rooms, accounts and all events.

See `SPEC.md` for goals, non-goals and acceptance criteria.

## Commands
<!-- How to install, run, test. Keep these exact and working. -->
Run everything from the repository root. Settings come from `.env` (copy `.env.example`); `DATABASE_URL` and `SESSION_SECRET` have no defaults, and the app refuses to start without them.

- Install: `python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt`
- Database, local machine (PostgreSQL 18 installed and running): once, `sudo -u postgres createuser --createdb "$USER" && createdb labbooking && createdb labbooking_test`. The server's socket is in `/tmp` but psycopg looks in `/var/run/postgresql`, so name it: `DATABASE_URL=postgresql:///labbooking?host=/tmp` and `TEST_DATABASE_URL=postgresql:///labbooking_test?host=/tmp`
- Database, codespace: `docker run -d --name labdb -p 5432:5432 -e POSTGRES_PASSWORD="$PGPASSWORD" postgres:18`, then set `DATABASE_URL` to point at it
- Migrate: `python -m src.data.migrate` (applies the files in `migrations/` that have not run yet)
- Demo data, local only: `python -m src.data.seed` (demo accounts at example.com, new random passwords printed once; never run it against the deployed database)
- Python: development happens locally on Python 3.14; CI and the codespace use 3.12, so do not use anything newer than 3.12 offers.
- Run: `uvicorn src.main:app --reload --port 8000`
- Test: `python -m pytest` (the data-layer tests run only when `TEST_DATABASE_URL` is set, and wipe that database first)
- Coverage: `python -m pytest --cov=src/services --cov-fail-under=100 && python -m pytest --cov=src --cov-fail-under=80`
- MCP server: `npm run mcp`

## Conventions
<!-- Folder layout, naming, where business rules live, how errors are returned to the client. -->
- `src/main.py`: creates the FastAPI app, mounts `src/static/` and includes the routes.
- `src/routes/`: HTTP route handlers. They read the request, call a service, and turn the result into a status code. No rules and no SQL here.
- `src/services/`: **all business rules live here**: seats, equipment, overlaps, roles, blocking, notifications, and the checks on the model's output. Services know nothing about HTTP or MCP, and get the data layer and the model client passed in, so tests can pass fakes.
- `src/data/`: data access. The only place that writes SQL. One exception, on purpose: `create_registration_if_seat_free` checks the seat count itself, because only a locked event row stops two people taking the last seat.
- Errors: a service raises a `ServiceError` subclass from `src/services/errors.py` with a message for the user. Routes map `BlockedUserError` to 403, `NotFoundError` to 404 and `ConflictError` to 409, and the client gets `{"detail": "<message>"}`.
- `src/clients/gemini.py`: the only file that names the model provider.
- `src/static/`: the HTML, CSS and JavaScript pages.
- `migrations/`: numbered SQL files with schema only, no data. `schema_migrations` records which have run; a migration that has run is never edited, only followed by a new one.
- `mcp-server/server.py`: the MCP server. Its tools import from `src/services/`, never from `src/data/`.
- `tests/`: pytest tests. A test that proves an acceptance criterion has its id in its name, for example `test_AC_7_full_event_is_refused`.

## Layers
<!-- Fill in the file or folder for each layer. -->
Requests arrive two ways and both end in the same place:

- HTTP route handler → service → data access → database
- MCP tool → **the same service** → data access → database

A route handler reads the request and turns a result into a status code. A service holds the
rules and knows nothing about HTTP or about MCP. Only the data layer writes SQL. An MCP tool
that talks to the database directly is a second, unguarded way into your data: never add one.

## The model feature
<!-- Provider, env var, and the call site. -->
- The provider is named in exactly one file: 
- The key comes from an environment variable and is never committed or logged.
- Every call has a timeout and a deterministic fallback, so the app still works when the provider is down or rate-limited.
- The model's output is re-checked against real data before anything is saved or shown.
- Tests never call the provider: they pass in a fake client.

## The MCP server
<!-- Where it lives and how it authenticates. -->
- Lives in `mcp-server/`, grew out of Exercise 1.
- Every tool calls a service function; none touches the data layer or the database directly.
- It carries a user, and enforces exactly the same authorization rules as the HTTP API.
- Adding a tool means adding a row to the table in `SPEC.md` too.

## Tests and coverage
- Every acceptance criterion in `SPEC.md` has an id like `AC-3`, and a test whose title contains that id.
- The coverage gate runs in CI: 100% of the service layer, 80% overall.
- A test is evidence. Changing a test so the code passes destroys the evidence.

## Always ask before
- deleting files or folders
- editing a migration that has already run
- installing or removing dependencies
- pushing, tagging or changing CI
- anything that touches secrets or `.env`
- changing an authentication or authorization rule
- adding, renaming or removing an MCP tool
- changing a coverage threshold
- sending user data to a third-party model

## Never
- commit secrets, passwords, API keys or an OAuth client secret
- weaken or delete a test to make it pass
- lower a coverage threshold or switch off a CI job to make the build green
- add an MCP tool that reaches past the service layer
- log a prompt that contains somebody's personal data
